"""INFUSE CLI Comprehensive Test Suite (Block 29).

Tests all CLI commands, formatters, exit codes, output discipline,
error mappings, and architectural boundary invariants.
"""

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import MagicMock, patch

from infuse.cli.exit_codes import (
    EXIT_AUTHENTICATION_ERROR,
    EXIT_CONFLICT,
    EXIT_CONTROL_ERROR,
    EXIT_GENERIC_ERROR,
    EXIT_MALFORMED_RESPONSE,
    EXIT_NOT_FOUND,
    EXIT_SERVER_ERROR,
    EXIT_SUCCESS,
    EXIT_TIMEOUT,
    EXIT_TRANSPORT_ERROR,
    EXIT_UNSUPPORTED,
    EXIT_USAGE_ERROR,
    EXIT_VALIDATION_ERROR,
    map_error_to_exit_code,
)
from infuse.cli.main import create_parser, main, run_cli
from infuse.contracts.control import (
    ControlCapability,
    ControlResult,
    ControlStatus,
)
from infuse.contracts.events import ExecutionEvent
from infuse.contracts.execution import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    NormalizedResponse,
)
from infuse.contracts.frontend import ExecutionSummaryViewModel
from infuse.contracts.governor import GovernorAction
from infuse.contracts.policy import BudgetControls, GovernancePolicy
from infuse.contracts.state import ExecutionState
from infuse.control.boundary import ExecutionControlBoundary
from infuse.control.interfaces import IControlExecutor
from infuse.sdk.client import InfuseClient
from infuse.sdk.config import ClientConfig
from infuse.sdk.errors import (
    AuthenticationError,
    ConflictError,
    ControlExecutionError,
    MalformedResponseError,
    NotFoundError,
    ServerError,
    TimeoutError,
    TransportError,
    UnsupportedControlError,
    ValidationError,
)
from infuse.sdk.models import (
    EventIngestResponse,
    ExecutionListResponse,
    GovernorInfo,
    PolicyListResponse,
    StateInfo,
)
from infuse.sdk.transport import ReferenceTransport
from infuse.version import __version__


class MockControlExecutor(IControlExecutor):
    """Mock executor for testing control operations."""

    def __init__(self, supported: bool = True, fail: bool = False):
        self.supported = supported
        self.fail = fail
        self.last_dispatched = None

    @property
    def executor_id(self) -> str:
        return "mock_cli_executor"

    def get_capability(self) -> ControlCapability:
        return ControlCapability(
            supports_cancel=self.supported,
            supports_terminate=self.supported,
            supports_throttle=self.supported,
            supports_next_step_switch=self.supported,
            supported_actions=[
                GovernorAction.CONTINUE,
                GovernorAction.STOP,
                GovernorAction.THROTTLE,
                GovernorAction.SWITCH,
            ] if self.supported else [GovernorAction.CONTINUE],
        )

    def execute_control(self, operation) -> ControlResult:
        self.last_dispatched = operation
        if not self.supported:
            return ControlResult(
                operation_id=operation.operation_id,
                execution_id=operation.execution_id,
                action=operation.action,
                status=ControlStatus.UNSUPPORTED,
                message="Action not supported",
            )
        if self.fail:
            return ControlResult(
                operation_id=operation.operation_id,
                execution_id=operation.execution_id,
                action=operation.action,
                status=ControlStatus.FAILED,
                message="Control failed in runtime",
            )
        return ControlResult(
            operation_id=operation.operation_id,
            execution_id=operation.execution_id,
            action=operation.action,
            status=ControlStatus.COMPLETED,
            message="Control applied successfully",
        )


class TestCli(unittest.TestCase):
    """Comprehensive test suite for the INFUSE CLI layer."""

    def setUp(self):
        self.transport = ReferenceTransport()
        self.boundary = ExecutionControlBoundary()
        self.mock_executor = MockControlExecutor(supported=True)
        self.boundary.register_executor("exec_123", self.mock_executor)

        # 1. Execute route
        self.transport.register_route(
            "POST",
            "/v1/execute",
            status_code=200,
            data={
                "execution_id": "exec_123",
                "request_id": "req_123",
                "status": "COMPLETED",
                "response": {"content": "Hello World", "role": "assistant"},
                "execution": {
                    "provider": "mock",
                    "model": "test-model",
                    "input_tokens": 10,
                    "output_tokens": 20,
                    "total_tokens": 30,
                    "cost_usd": 0.0001,
                    "latency_ms": 150.0,
                    "state": "NORMAL",
                },
                "decision": {
                    "action": "CONTINUE",
                    "reason_codes": [],
                },
            },
        )

        # 2. Executions list & get & state
        summary_data = {
            "execution_id": "exec_123",
            "agent_name": "TestAgent",
            "task_description": "Sample task",
            "status": "COMPLETED",
            "provider": "mock",
            "model": "test-model",
            "tokens_total": 30,
            "cost_usd": 0.0001,
            "latency_ms": 150.0,
            "is_live": False,
            "started_at": "2026-09-25T12:00:00Z",
        }
        self.transport.register_route(
            "GET",
            "/v1/executions",
            status_code=200,
            data={"items": [summary_data], "total": 1, "limit": 50, "offset": 0},
        )
        self.transport.register_route(
            "GET",
            "/v1/executions/exec_123",
            status_code=200,
            data=summary_data,
        )
        self.transport.register_route(
            "GET",
            "/v1/executions/exec_123/state",
            status_code=200,
            data={
                "execution_id": "exec_123",
                "state": "NORMAL",
                "boundary_threshold_percent": 100.0,
                "reason_codes": ["HEALTHY"],
                "evaluated_at": "2026-09-25T12:00:00Z",
            },
        )
        self.transport.register_route(
            "POST",
            "/v1/executions/exec_123/events",
            status_code=200,
            data={
                "status": "INGESTED",
                "event_id": "evt_123",
                "execution_id": "exec_123",
                "schema_version": "1.0.0",
            },
        )

        # 3. Policies
        policy_data = {
            "policy_id": "pol_default",
            "name": "Default Policy",
            "version": "1.0.0",
            "is_active": True,
            "budget_controls": {"max_budget_usd": 100.0},
        }
        self.transport.register_route(
            "GET",
            "/v1/policies",
            status_code=200,
            data={"policies": [policy_data], "active_policy": policy_data},
        )
        self.transport.register_route(
            "GET",
            "/v1/policies/active",
            status_code=200,
            data=policy_data,
        )
        self.transport.register_route(
            "PUT",
            "/v1/policies/pol_custom",
            status_code=200,
            data={
                "policy_id": "pol_custom",
                "name": "Custom CLI Policy",
                "version": "1.0.0",
                "is_active": True,
                "budget_controls": {"max_budget_usd": 50.0},
            },
        )

        self.client = InfuseClient(transport=self.transport, control_boundary=self.boundary)

    def _run_cli_capture(self, args, client=None):
        out_buf = io.StringIO()
        err_buf = io.StringIO()
        with redirect_stdout(out_buf), redirect_stderr(err_buf):
            code = run_cli(args=args, client=client or self.client)
        return code, out_buf.getvalue(), err_buf.getvalue()

    # 1. Root help
    def test_01_root_help(self):
        code, out, err = self._run_cli_capture(["--help"])
        self.assertEqual(code, EXIT_SUCCESS)
        self.assertIn("INFUSE", out)
        self.assertIn("Available commands", out)

    # 2. Command help
    def test_02_command_help(self):
        for cmd in ["execute", "execution", "executions", "state", "events", "policy", "governor", "control", "config"]:
            code, out, err = self._run_cli_capture([cmd, "--help"])
            self.assertEqual(code, EXIT_SUCCESS)
            self.assertIn(f"infuse {cmd}", out)

    # 3. Version command
    def test_03_version(self):
        code, out, err = self._run_cli_capture(["version"])
        self.assertEqual(code, EXIT_SUCCESS)
        self.assertIn(__version__, out)

        code_flag, out_flag, _ = self._run_cli_capture(["--version"])
        self.assertEqual(code_flag, EXIT_SUCCESS)
        self.assertIn(__version__, out_flag)

    # 4. Execute command
    def test_04_execute_command(self):
        code, out, err = self._run_cli_capture(["execute", "--task", "Test Task", "--provider", "mock", "--model", "test-model"])
        self.assertEqual(code, EXIT_SUCCESS)
        self.assertIn("Execution ID:", out)
        self.assertIn("COMPLETED", out)

    # 5. Execution retrieval
    def test_05_execution_retrieval(self):
        code, out, err = self._run_cli_capture(["execution", "get", "exec_123"])
        self.assertEqual(code, EXIT_SUCCESS)
        self.assertIn("Execution ID:", out)
        self.assertIn("exec_123", out)

    # 6. Execution state
    def test_06_execution_state(self):
        code, out, err = self._run_cli_capture(["execution", "state", "exec_123"])
        self.assertEqual(code, EXIT_SUCCESS)
        self.assertIn("Evaluated State:", out)

        # Direct state command
        code_dir, out_dir, _ = self._run_cli_capture(["state", "exec_123"])
        self.assertEqual(code_dir, EXIT_SUCCESS)
        self.assertIn("Evaluated State:", out_dir)

    # 7. Execution result
    def test_07_execution_result(self):
        code, out, err = self._run_cli_capture(["execution", "result", "exec_123"])
        self.assertEqual(code, EXIT_SUCCESS)
        self.assertIn("Execution ID:", out)

    # 8. Executions list
    def test_08_executions_list(self):
        code, out, err = self._run_cli_capture(["executions", "list", "--limit", "10"])
        self.assertEqual(code, EXIT_SUCCESS)
        self.assertIn("EXECUTION ID", out)

    # 9. Event inspection
    def test_09_events_inspection(self):
        code, out, err = self._run_cli_capture(["events", "list", "exec_123"])
        self.assertEqual(code, EXIT_SUCCESS)

    # 10. Event submission
    def test_10_events_submission(self):
        code, out, err = self._run_cli_capture([
            "events", "publish", "exec_123",
            "--type", "TOKEN_OBSERVED",
            "--payload", '{"tokens": 100}'
        ])
        self.assertEqual(code, EXIT_SUCCESS)
        self.assertIn("Event ID:", out)

    # 11. Policy list
    def test_11_policy_list(self):
        code, out, err = self._run_cli_capture(["policy", "list"])
        self.assertEqual(code, EXIT_SUCCESS)
        self.assertIn("POLICY ID", out)

    # 12. Policy get
    def test_12_policy_get(self):
        code, out, err = self._run_cli_capture(["policy", "get"])
        self.assertEqual(code, EXIT_SUCCESS)
        self.assertIn("Policy ID:", out)

    # 13. Policy mutation
    def test_13_policy_mutation(self):
        with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".json") as f:
            json.dump({
                "policy_id": "pol_custom",
                "name": "Custom CLI Policy",
                "version": "1.0.0",
                "is_active": True,
                "budget_controls": {"max_budget_usd": 50.0}
            }, f)
            f_path = f.name

        try:
            code, out, err = self._run_cli_capture(["policy", "update", "pol_custom", "--file", f_path])
            self.assertEqual(code, EXIT_SUCCESS)
            self.assertIn("Custom CLI Policy", out)
        finally:
            if os.path.exists(f_path):
                os.remove(f_path)

    # 14. Governor inspection
    def test_14_governor_inspection(self):
        code, out, err = self._run_cli_capture(["governor", "exec_123"])
        self.assertEqual(code, EXIT_SUCCESS)
        self.assertIn("Governor Action:", out)

    # 15. Control cancel
    def test_15_control_cancel(self):
        code, out, err = self._run_cli_capture(["control", "cancel", "exec_123", "--reason", "User cancel", "--yes"])
        self.assertEqual(code, EXIT_SUCCESS)
        self.assertIn("COMPLETED", out)

    # 16. Control terminate
    def test_16_control_terminate(self):
        code, out, err = self._run_cli_capture(["control", "terminate", "exec_123", "--yes"])
        self.assertEqual(code, EXIT_SUCCESS)
        self.assertIn("COMPLETED", out)

    # 17. Control throttle
    def test_17_control_throttle(self):
        code, out, err = self._run_cli_capture(["control", "throttle", "exec_123", "--delay-ms", "2000", "--yes"])
        self.assertEqual(code, EXIT_SUCCESS)
        self.assertIn("COMPLETED", out)

    # 18. Control switch
    def test_18_control_switch(self):
        code, out, err = self._run_cli_capture(["control", "switch", "exec_123", "--target-model", "gpt-4o", "--yes"])
        self.assertEqual(code, EXIT_SUCCESS)
        self.assertIn("COMPLETED", out)

    # 19. Unsupported control
    def test_19_unsupported_control(self):
        unsupported_executor = MockControlExecutor(supported=False)
        self.boundary.register_executor("exec_unsupported", unsupported_executor)
        code, out, err = self._run_cli_capture(["control", "cancel", "exec_unsupported", "--yes"])
        self.assertEqual(code, EXIT_UNSUPPORTED)
        self.assertIn("UNSUPPORTED", out)

    # 20. Control failure
    def test_20_control_failure(self):
        failing_executor = MockControlExecutor(supported=True, fail=True)
        self.boundary.register_executor("exec_failing", failing_executor)
        code, out, err = self._run_cli_capture(["control", "cancel", "exec_failing", "--yes"])
        self.assertEqual(code, EXIT_CONTROL_ERROR)
        self.assertIn("FAILED", out)

    # 21. JSON output
    def test_21_json_output(self):
        code, out, err = self._run_cli_capture(["version", "--json"])
        self.assertEqual(code, EXIT_SUCCESS)
        parsed = json.loads(out)
        self.assertEqual(parsed["version"], __version__)
        self.assertEqual(err, "")

    # 22. Human output
    def test_22_human_output(self):
        code, out, err = self._run_cli_capture(["config"])
        self.assertEqual(code, EXIT_SUCCESS)
        self.assertIn("INFUSE SDK / CLI Configuration:", out)

    # 23. JSON error formatting
    def test_23_json_error(self):
        mock_client = MagicMock()
        mock_client.executions.get.side_effect = NotFoundError("Execution not found")
        code, out, err = self._run_cli_capture(["execution", "get", "exec_missing", "--json"], client=mock_client)
        self.assertEqual(code, EXIT_NOT_FOUND)
        parsed_err = json.loads(err)
        self.assertIn("error", parsed_err)
        self.assertEqual(parsed_err["code"], "NotFoundError")

    # 24. Human error formatting
    def test_24_human_error(self):
        mock_client = MagicMock()
        mock_client.executions.get.side_effect = NotFoundError("Execution not found")
        code, out, err = self._run_cli_capture(["execution", "get", "exec_missing"], client=mock_client)
        self.assertEqual(code, EXIT_NOT_FOUND)
        self.assertIn("Error [NotFoundError]:", err)

    # 25. stdout discipline (JSON mode writes ONLY JSON to stdout)
    def test_25_stdout_discipline(self):
        code, out, err = self._run_cli_capture(["executions", "list", "--json"])
        self.assertEqual(code, EXIT_SUCCESS)
        data = json.loads(out)
        self.assertIn("items", data)
        self.assertEqual(err, "")

    # 26. stderr discipline (Errors go to stderr, not stdout)
    def test_26_stderr_discipline(self):
        code, out, err = self._run_cli_capture(["unknown_cmd"])
        self.assertEqual(code, EXIT_USAGE_ERROR)
        self.assertEqual(out, "")
        self.assertIn("unknown_cmd", err)

    # 27. Exit code success
    def test_27_exit_code_success(self):
        code, _, _ = self._run_cli_capture(["version"])
        self.assertEqual(code, EXIT_SUCCESS)

    # 28. Validation exit code
    def test_28_validation_exit_code(self):
        mock_client = MagicMock()
        mock_client.executions.execute.side_effect = ValidationError("Invalid schema")
        code, _, err = self._run_cli_capture(["execute", "--task", "test"], client=mock_client)
        self.assertEqual(code, EXIT_VALIDATION_ERROR)
        self.assertIn("ValidationError", err)

    # 29. Authentication exit code
    def test_29_authentication_exit_code(self):
        mock_client = MagicMock()
        mock_client.executions.list.side_effect = AuthenticationError("Unauthorized")
        code, _, err = self._run_cli_capture(["executions", "list"], client=mock_client)
        self.assertEqual(code, EXIT_AUTHENTICATION_ERROR)
        self.assertIn("AuthenticationError", err)

    # 30. Not found exit code
    def test_30_not_found_exit_code(self):
        mock_client = MagicMock()
        mock_client.executions.get.side_effect = NotFoundError("Resource not found")
        code, _, err = self._run_cli_capture(["execution", "get", "exec_none"], client=mock_client)
        self.assertEqual(code, EXIT_NOT_FOUND)

    # 31. Unsupported exit code
    def test_31_unsupported_exit_code(self):
        mock_client = MagicMock()
        mock_client.executions.get.side_effect = UnsupportedControlError("Unsupported")
        code, _, err = self._run_cli_capture(["execution", "get", "exec_none"], client=mock_client)
        self.assertEqual(code, EXIT_UNSUPPORTED)

    # 32. Transport exit code
    def test_32_transport_exit_code(self):
        mock_client = MagicMock()
        mock_client.executions.list.side_effect = TransportError("Connection refused")
        code, _, err = self._run_cli_capture(["executions", "list"], client=mock_client)
        self.assertEqual(code, EXIT_TRANSPORT_ERROR)

    # 33. Timeout exit code
    def test_33_timeout_exit_code(self):
        mock_client = MagicMock()
        mock_client.executions.list.side_effect = TimeoutError("Timed out")
        code, _, err = self._run_cli_capture(["executions", "list"], client=mock_client)
        self.assertEqual(code, EXIT_TIMEOUT)

    # 34. Secret redaction
    def test_34_secret_redaction(self):
        mock_client = MagicMock()
        mock_client.config = ClientConfig(api_key="sk-secret-key-123456789")
        code, out, _ = self._run_cli_capture(["config"], client=mock_client)
        self.assertEqual(code, EXIT_SUCCESS)
        self.assertNotIn("sk-secret-key-123456789", out)
        self.assertIn("[CONFIGURED]", out)

    # 35. Environment configuration
    def test_35_environment_configuration(self):
        with patch.dict(os.environ, {"INFUSE_BASE_URL": "http://custom-env:9000", "INFUSE_API_KEY": "sk-env-key-12345"}):
            cfg = ClientConfig.from_env()
            self.assertEqual(cfg.base_url, "http://custom-env:9000")
            self.assertEqual(cfg.api_key, "sk-env-key-12345")

    # 36. Config command inspection
    def test_36_config_command(self):
        code, out, _ = self._run_cli_capture(["config", "--json"])
        self.assertEqual(code, EXIT_SUCCESS)
        data = json.loads(out)
        self.assertIn("base_url", data)

    # 37. CLI argument precedence
    def test_37_cli_argument_precedence(self):
        parser = create_parser()
        args = parser.parse_args(["--endpoint", "http://flag-url:8000", "--timeout", "45", "version"])
        self.assertEqual(args.base_url, "http://flag-url:8000")
        self.assertEqual(args.timeout, 45.0)

    # 38. Pagination
    def test_38_pagination(self):
        code, out, _ = self._run_cli_capture(["executions", "list", "--limit", "5", "--offset", "10"])
        self.assertEqual(code, EXIT_SUCCESS)
        self.assertIn("Limit 5", out)
        self.assertIn("Offset 10", out)

    # 39. Empty results handling
    def test_39_empty_results(self):
        mock_client = MagicMock()
        mock_client.executions.list.return_value = ExecutionListResponse(items=[], total=0, limit=50, offset=0)
        code, out, _ = self._run_cli_capture(["executions", "list"], client=mock_client)
        self.assertEqual(code, EXIT_SUCCESS)
        self.assertIn("No executions found", out)

    # 40. Malformed SDK response error
    def test_40_malformed_sdk_response(self):
        mock_client = MagicMock()
        mock_client.executions.get.side_effect = MalformedResponseError("Invalid JSON received")
        code, _, err = self._run_cli_capture(["execution", "get", "exec_bad"], client=mock_client)
        self.assertEqual(code, EXIT_MALFORMED_RESPONSE)

    # 41. SDK transport failure
    def test_41_sdk_transport_failure(self):
        mock_client = MagicMock()
        mock_client.executions.execute.side_effect = TransportError("Failed to reach server")
        code, _, err = self._run_cli_capture(["execute", "--task", "fail"], client=mock_client)
        self.assertEqual(code, EXIT_TRANSPORT_ERROR)
        self.assertIn("TransportError", err)

    # 42. Architectural negative test: CLI does not instantiate agent adapters
    def test_42_no_direct_agent_invocation(self):
        import importlib
        mod = importlib.import_module("infuse.cli.main")
        with open(mod.__file__, "r") as f:
            content = f.read()
        self.assertNotIn("ClaudeCodeAdapter", content)
        self.assertNotIn("CodexAdapter", content)
        self.assertNotIn("OpenCodeAdapter", content)
        self.assertNotIn("HermesAdapter", content)
        self.assertNotIn("subprocess", content)

    # 43. Architectural negative test: CLI does not instantiate provider adapters
    def test_43_no_direct_provider_invocation(self):
        import importlib
        mod = importlib.import_module("infuse.cli.main")
        with open(mod.__file__, "r") as f:
            content = f.read()
        self.assertNotIn("OpenAIProviderAdapter", content)
        self.assertNotIn("AnthropicProviderAdapter", content)
        self.assertNotIn("GeminiProviderAdapter", content)
        self.assertNotIn("DeepSeekProviderAdapter", content)

    # 44. Architectural negative test: CLI does not calculate Governor thresholds or state transitions
    def test_44_no_duplicate_governor_logic(self):
        import infuse.cli.commands.governor as gov_cmd
        import infuse.cli.commands.execution as exec_cmd
        with open(gov_cmd.__file__, "r") as f:
            gov_src = f.read()
        with open(exec_cmd.__file__, "r") as f:
            exec_src = f.read()
        self.assertNotIn("calculate_cost", gov_src)
        self.assertNotIn("RUNAWAY", gov_src)
        self.assertNotIn("eval_policy", gov_src)
        self.assertNotIn("eval_policy", exec_src)

    # 45. Public CLI entry point
    def test_45_public_cli_entry_point(self):
        with patch.object(sys, "argv", ["infuse", "version"]):
            with patch("sys.exit") as mock_exit:
                main()
                mock_exit.assert_called_with(EXIT_SUCCESS)

    # 46. Conflict error exit code
    def test_46_conflict_error_exit_code(self):
        mock_client = MagicMock()
        mock_client.policies.update.side_effect = ConflictError("Policy already locked")
        code, _, err = self._run_cli_capture(["policy", "update", "pol_1", "--data", '{"name": "test"}'], client=mock_client)
        self.assertEqual(code, EXIT_CONFLICT)

    # 47. Server error exit code
    def test_47_server_error_exit_code(self):
        mock_client = MagicMock()
        mock_client.executions.get.side_effect = ServerError("Internal 500 error")
        code, _, err = self._run_cli_capture(["execution", "get", "exec_err"], client=mock_client)
        self.assertEqual(code, EXIT_SERVER_ERROR)

    # 48. Execute with JSON file
    def test_48_execute_with_file(self):
        with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".json") as f:
            json.dump({
                "request_id": "req_file_123",
                "task": {"task_id": "task_file_123", "description": "File based task"},
                "request": {"messages": [{"role": "user", "content": "hello"}]},
                "execution_context": {"agent_id": "TestAgent"}
            }, f)
            f_path = f.name

        try:
            code, out, _ = self._run_cli_capture(["execute", "--file", f_path])
            self.assertEqual(code, EXIT_SUCCESS)
            self.assertIn("Execution ID:", out)
        finally:
            if os.path.exists(f_path):
                os.remove(f_path)


if __name__ == "__main__":
    unittest.main()
