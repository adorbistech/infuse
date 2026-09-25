"""INFUSE MCP Server Comprehensive Test Suite (Block 30).

Tests MCP server initialization, tool discovery, resource registration,
SDK delegation, tool calls, error mapping, secret redaction, stdio/logging separation,
and architectural negative invariants.
"""

import asyncio
import io
import json
import logging
import sys
import unittest
from unittest.mock import MagicMock, patch

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
from infuse.contracts.policy import GovernancePolicy
from infuse.contracts.state import ExecutionState
from infuse.control.boundary import ExecutionControlBoundary
from infuse.control.interfaces import IControlExecutor
from infuse.mcp.config import McpServerConfig
from infuse.mcp.errors import format_mcp_error, map_error_to_code
from infuse.mcp.main import create_parser, run_server, setup_logging
from infuse.mcp.server import create_mcp_server
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


class MockMcpControlExecutor(IControlExecutor):
    """Mock executor for testing control operations in MCP tests."""

    def __init__(self, supported: bool = True, fail: bool = False):
        self.supported = supported
        self.fail = fail
        self.last_dispatched = None

    @property
    def executor_id(self) -> str:
        return "mock_mcp_executor"

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
            ]
            if self.supported
            else [GovernorAction.CONTINUE],
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


class TestMcpServer(unittest.TestCase):
    """Comprehensive test suite for the INFUSE MCP Server layer."""

    def setUp(self):
        self.transport = ReferenceTransport()
        self.boundary = ExecutionControlBoundary()
        self.mock_executor = MockMcpControlExecutor(supported=True)
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
                "response": {"content": "Hello from MCP execution", "role": "assistant"},
                "execution": {
                    "provider": "mock",
                    "model": "test-model",
                    "input_tokens": 12,
                    "output_tokens": 24,
                    "total_tokens": 36,
                    "cost_usd": 0.0002,
                    "latency_ms": 145.0,
                    "state": "NORMAL",
                },
                "decision": {
                    "action": "CONTINUE",
                    "reason_codes": [],
                },
            },
        )

        # 2. Executions summary & state
        summary_data = {
            "execution_id": "exec_123",
            "agent_name": "TestAgent",
            "task_description": "Sample MCP task",
            "status": "COMPLETED",
            "provider": "mock",
            "model": "test-model",
            "tokens_total": 36,
            "cost_usd": 0.0002,
            "latency_ms": 145.0,
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
            "name": "Default MCP Policy",
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
                "name": "Custom MCP Policy",
                "version": "1.0.0",
                "is_active": True,
                "budget_controls": {"max_budget_usd": 50.0},
            },
        )

        self.client = InfuseClient(transport=self.transport, control_boundary=self.boundary)
        self.mcp = create_mcp_server(client=self.client)

    def _call_tool_sync(self, name, arguments=None, server=None):
        srv = server or self.mcp
        result = asyncio.run(srv.call_tool(name, arguments or {}))
        if isinstance(result, tuple) and len(result) >= 1:
            content_list = result[0]
            if isinstance(content_list, list) and len(content_list) > 0:
                return json.loads(content_list[0].text)
            elif isinstance(result[1], dict) and "result" in result[1]:
                return result[1]["result"]
        elif isinstance(result, list) and len(result) > 0:
            return json.loads(result[0].text)
        return result

    # 1. Server initialization
    def test_01_server_initialization(self):
        self.assertIsNotNone(self.mcp)
        self.assertEqual(self.mcp.name, "infuse")
        self.assertIs(self.mcp.client, self.client)

    # 2. MCP protocol initialization
    def test_02_protocol_initialization(self):
        cfg = McpServerConfig(name="test-server", version="0.1.0")
        server = create_mcp_server(client=self.client, config=cfg)
        self.assertEqual(server.name, "test-server")

    # 3. Tool discovery
    def test_03_tool_discovery(self):
        tools = asyncio.run(self.mcp.list_tools())
        tool_names = [t.name for t in tools]
        expected_tools = [
            "infuse_execute",
            "infuse_get_execution",
            "infuse_get_execution_state",
            "infuse_get_execution_result",
            "infuse_list_executions",
            "infuse_list_events",
            "infuse_publish_event",
            "infuse_get_policy",
            "infuse_list_policies",
            "infuse_update_policy",
            "infuse_get_governor_decision",
            "infuse_control",
        ]
        for exp in expected_tools:
            self.assertIn(exp, tool_names)
        self.assertEqual(len(tools), 12)

    # 4. Resource discovery
    def test_04_resource_discovery(self):
        templates = asyncio.run(self.mcp.list_resource_templates())
        template_uris = [t.uriTemplate for t in templates]
        self.assertIn("infuse://executions/{execution_id}", template_uris)
        self.assertIn("infuse://executions/{execution_id}/state", template_uris)
        self.assertIn("infuse://executions/{execution_id}/result", template_uris)
        self.assertIn("infuse://governor/{execution_id}", template_uris)

        resources = asyncio.run(self.mcp.list_resources())
        resource_uris = [str(r.uri) for r in resources]
        self.assertIn("infuse://policies/active", resource_uris)

    # 5. Tool input schemas
    def test_05_tool_input_schemas(self):
        tools = asyncio.run(self.mcp.list_tools())
        execute_tool = next(t for t in tools if t.name == "infuse_execute")
        self.assertIsNotNone(execute_tool.inputSchema)
        self.assertIn("task_description", execute_tool.inputSchema.get("properties", {}))

    # 6. Execute tool
    def test_06_execute_tool(self):
        data = self._call_tool_sync(
            "infuse_execute",
            {"task_description": "Analyze repository", "prompt": "scan files", "provider": "mock", "model": "test-model"},
        )
        self.assertEqual(data["execution_id"], "exec_123")
        self.assertEqual(data["status"], "COMPLETED")
        self.assertEqual(data["response"]["content"], "Hello from MCP execution")

    # 7. Get execution tool
    def test_07_get_execution_tool(self):
        data = self._call_tool_sync("infuse_get_execution", {"execution_id": "exec_123"})
        self.assertEqual(data["execution_id"], "exec_123")
        self.assertEqual(data["status"], "COMPLETED")

    # 8. Get execution state tool
    def test_08_get_execution_state_tool(self):
        data = self._call_tool_sync("infuse_get_execution_state", {"execution_id": "exec_123"})
        self.assertEqual(data["execution_id"], "exec_123")
        self.assertEqual(data["state"], "NORMAL")
        self.assertEqual(data["boundary_threshold_percent"], 80.0)

    # 9. Get execution result tool
    def test_09_get_execution_result_tool(self):
        data = self._call_tool_sync("infuse_get_execution_result", {"execution_id": "exec_123"})
        self.assertEqual(data["execution_id"], "exec_123")

    # 10. List executions tool
    def test_10_list_executions_tool(self):
        data = self._call_tool_sync("infuse_list_executions", {"limit": 10, "offset": 0})
        self.assertIn("items", data)
        self.assertEqual(data["total"], 1)

    # 11. List events tool
    def test_11_list_events_tool(self):
        data = self._call_tool_sync("infuse_list_events", {"execution_id": "exec_123"})
        self.assertEqual(data["execution_id"], "exec_123")

    # 12. Publish event tool
    def test_12_publish_event_tool(self):
        data = self._call_tool_sync(
            "infuse_publish_event",
            {"execution_id": "exec_123", "event_type": "TOKEN_OBSERVED", "payload": {"tokens": 50}},
        )
        self.assertEqual(data["status"], "INGESTED")
        self.assertEqual(data["event_id"], "evt_123")

    # 13. Policy list tool
    def test_13_policy_list_tool(self):
        data = self._call_tool_sync("infuse_list_policies")
        self.assertIn("policies", data)
        self.assertEqual(len(data["policies"]), 1)

    # 14. Policy get tool (active)
    def test_14_policy_get_tool_active(self):
        data = self._call_tool_sync("infuse_get_policy")
        self.assertEqual(data["policy_id"], "pol_default")

    # 15. Policy get tool (by id)
    def test_15_policy_get_tool_by_id(self):
        data = self._call_tool_sync("infuse_get_policy", {"policy_id": "pol_default"})
        self.assertEqual(data["policy_id"], "pol_default")

    # 16. Policy update tool
    def test_16_policy_update_tool(self):
        data = self._call_tool_sync(
            "infuse_update_policy",
            {"policy_id": "pol_custom", "policy_data": {"name": "Custom MCP Policy", "version": "1.0.0"}},
        )
        self.assertEqual(data["policy_id"], "pol_custom")

    # 17. Governor decision tool
    def test_17_governor_decision_tool(self):
        data = self._call_tool_sync("infuse_get_governor_decision", {"execution_id": "exec_123"})
        self.assertEqual(data["execution_id"], "exec_123")
        self.assertEqual(data["action"], "CONTINUE")

    # 18. Control tool (STOP)
    def test_18_control_tool_stop(self):
        data = self._call_tool_sync(
            "infuse_control",
            {"execution_id": "exec_123", "action": "STOP", "params": {"hard": False}},
        )
        self.assertEqual(data["status"], "COMPLETED")
        self.assertEqual(data["action"], "STOP")

    # 19. Control tool (THROTTLE)
    def test_19_control_tool_throttle(self):
        data = self._call_tool_sync(
            "infuse_control",
            {"execution_id": "exec_123", "action": "THROTTLE", "params": {"delay_ms": 2000}},
        )
        self.assertEqual(data["status"], "COMPLETED")
        self.assertEqual(data["action"], "THROTTLE")

    # 20. Control tool (SWITCH)
    def test_20_control_tool_switch(self):
        data = self._call_tool_sync(
            "infuse_control",
            {"execution_id": "exec_123", "action": "SWITCH", "params": {"target_model": "gpt-4o"}},
        )
        self.assertEqual(data["status"], "COMPLETED")
        self.assertEqual(data["action"], "SWITCH")

    # 21. Unsupported control tool
    def test_21_unsupported_control_tool(self):
        unsupported_executor = MockMcpControlExecutor(supported=False)
        self.boundary.register_executor("exec_unsupported", unsupported_executor)
        data = self._call_tool_sync(
            "infuse_control",
            {"execution_id": "exec_unsupported", "action": "STOP"},
        )
        self.assertEqual(data["status"], "UNSUPPORTED")

    # 22. Control failure tool
    def test_22_control_failure_tool(self):
        failing_executor = MockMcpControlExecutor(supported=True, fail=True)
        self.boundary.register_executor("exec_failing", failing_executor)
        data = self._call_tool_sync(
            "infuse_control",
            {"execution_id": "exec_failing", "action": "STOP"},
        )
        self.assertEqual(data["status"], "FAILED")

    # 23. Validation failure error mapping
    def test_23_validation_failure(self):
        mock_client = MagicMock()
        mock_client.executions.execute.side_effect = ValidationError("Invalid field format", details={"field": "task"})
        server = create_mcp_server(client=mock_client)
        data = self._call_tool_sync("infuse_execute", {"task_description": "invalid"}, server=server)
        self.assertTrue(data["error"])
        self.assertEqual(data["code"], "VALIDATION_ERROR")
        self.assertIn("Invalid field format", data["message"])

    # 24. Authentication failure error mapping
    def test_24_authentication_failure(self):
        mock_client = MagicMock()
        mock_client.executions.get.side_effect = AuthenticationError("Invalid Bearer Token: sk-secret-12345", status_code=401)
        server = create_mcp_server(client=mock_client)
        data = self._call_tool_sync("infuse_get_execution", {"execution_id": "exec_auth"}, server=server)
        self.assertTrue(data["error"])
        self.assertEqual(data["code"], "AUTHENTICATION_ERROR")
        self.assertNotIn("sk-secret-12345", data["message"])
        self.assertIn("[REDACTED]", data["message"])

    # 25. Not found error mapping
    def test_25_not_found(self):
        mock_client = MagicMock()
        mock_client.executions.get.side_effect = NotFoundError("Execution 'exec_missing' not found", status_code=404)
        server = create_mcp_server(client=mock_client)
        data = self._call_tool_sync("infuse_get_execution", {"execution_id": "exec_missing"}, server=server)
        self.assertTrue(data["error"])
        self.assertEqual(data["code"], "NOT_FOUND")
        self.assertEqual(data["status_code"], 404)

    # 26. Transport failure error mapping
    def test_26_transport_failure(self):
        mock_client = MagicMock()
        mock_client.executions.list.side_effect = TransportError("Failed to connect to core API")
        server = create_mcp_server(client=mock_client)
        data = self._call_tool_sync("infuse_list_executions", {}, server=server)
        self.assertTrue(data["error"])
        self.assertEqual(data["code"], "TRANSPORT_ERROR")

    # 27. Timeout error mapping
    def test_27_timeout_failure(self):
        mock_client = MagicMock()
        mock_client.executions.list.side_effect = TimeoutError("Request timed out after 30s")
        server = create_mcp_server(client=mock_client)
        data = self._call_tool_sync("infuse_list_executions", {}, server=server)
        self.assertTrue(data["error"])
        self.assertEqual(data["code"], "TIMEOUT_ERROR")

    # 28. Malformed SDK response error mapping
    def test_28_malformed_sdk_response(self):
        mock_client = MagicMock()
        mock_client.executions.get.side_effect = MalformedResponseError("Unparsable JSON payload")
        server = create_mcp_server(client=mock_client)
        data = self._call_tool_sync("infuse_get_execution", {"execution_id": "exec_malformed"}, server=server)
        self.assertTrue(data["error"])
        self.assertEqual(data["code"], "MALFORMED_RESPONSE")

    # 29. Conflict error mapping
    def test_29_conflict_failure(self):
        mock_client = MagicMock()
        mock_client.policies.update.side_effect = ConflictError("Policy revision conflict")
        server = create_mcp_server(client=mock_client)
        data = self._call_tool_sync("infuse_update_policy", {"policy_id": "pol_1", "policy_data": {}}, server=server)
        self.assertTrue(data["error"])
        self.assertEqual(data["code"], "CONFLICT_ERROR")

    # 30. Server error mapping
    def test_30_server_failure(self):
        mock_client = MagicMock()
        mock_client.executions.get.side_effect = ServerError("Internal Core Error 500", status_code=500)
        server = create_mcp_server(client=mock_client)
        data = self._call_tool_sync("infuse_get_execution", {"execution_id": "exec_err"}, server=server)
        self.assertTrue(data["error"])
        self.assertEqual(data["code"], "SERVER_ERROR")

    # 31. JSON serialization of responses
    def test_31_json_serialization(self):
        data = self._call_tool_sync("infuse_get_execution", {"execution_id": "exec_123"})
        self.assertEqual(data["execution_id"], "exec_123")

    # 32. Canonical event preservation
    def test_32_canonical_event_preservation(self):
        data = self._call_tool_sync(
            "infuse_publish_event",
            {"execution_id": "exec_123", "event_type": "TOKEN_OBSERVED", "source": "AGENT", "sequence": 5},
        )
        self.assertEqual(data["execution_id"], "exec_123")
        self.assertEqual(data["status"], "INGESTED")

    # 33. Execution identity preservation
    def test_33_execution_identity_preservation(self):
        data = self._call_tool_sync("infuse_get_execution", {"execution_id": "exec_123"})
        self.assertEqual(data["execution_id"], "exec_123")

    # 34. Decision identity preservation
    def test_34_decision_identity_preservation(self):
        data = self._call_tool_sync("infuse_get_governor_decision", {"execution_id": "exec_123"})
        self.assertEqual(data["execution_id"], "exec_123")
        self.assertEqual(data["action"], "CONTINUE")

    # 35. Control operation identity preservation
    def test_35_control_operation_identity_preservation(self):
        data = self._call_tool_sync(
            "infuse_control",
            {"execution_id": "exec_123", "action": "STOP", "operation_id": "op_explicit_999"},
        )
        self.assertEqual(data["operation_id"], "op_explicit_999")
        self.assertEqual(data["execution_id"], "exec_123")

    # 36. Secret redaction in messages
    def test_36_secret_redaction_message(self):
        exc = AuthenticationError("Bearer token sk-live-secret-987654321 was rejected")
        formatted = format_mcp_error(exc)
        self.assertNotIn("sk-live-secret-987654321", formatted["message"])
        self.assertIn("[REDACTED]", formatted["message"])

    # 37. Secret redaction in details
    def test_37_secret_redaction_details(self):
        exc = ValidationError("Validation error", details={"api_key": "sk-secret-11111", "token": "ghp_22222"})
        formatted = format_mcp_error(exc)
        self.assertNotIn("sk-secret-11111", str(formatted["details"]))
        self.assertNotIn("ghp_22222", str(formatted["details"]))

    # 38. Stderr / logging separation setup
    def test_38_logging_stderr_separation(self):
        err_stream = io.StringIO()
        logging.basicConfig(level=logging.INFO, stream=err_stream, force=True)
        setup_logging("DEBUG")
        logger = logging.getLogger("infuse.mcp.test")
        logger.info("Test diagnostic log message")
        handlers = logging.getLogger().handlers
        self.assertTrue(any(h.stream is sys.stderr for h in handlers if hasattr(h, "stream")))

    # 39. Config loader from environment
    def test_39_config_from_env(self):
        with patch.dict(
            "os.environ",
            {
                "INFUSE_BASE_URL": "http://env-host:8080",
                "INFUSE_API_KEY": "sk-env-key",
                "INFUSE_TIMEOUT_SECONDS": "45.0",
                "INFUSE_MCP_TRANSPORT": "streamable_http",
            },
        ):
            cfg = McpServerConfig.from_env()
            self.assertEqual(cfg.base_url, "http://env-host:8080")
            self.assertEqual(cfg.api_key, "sk-env-key")
            self.assertEqual(cfg.timeout_seconds, 45.0)
            self.assertEqual(cfg.transport, "streamable_http")

    # 40. Concurrent tool calls
    def test_40_concurrent_tool_calls(self):
        async def run_concurrent():
            t1 = self.mcp.call_tool("infuse_get_execution", {"execution_id": "exec_123"})
            t2 = self.mcp.call_tool("infuse_get_execution_state", {"execution_id": "exec_123"})
            t3 = self.mcp.call_tool("infuse_get_governor_decision", {"execution_id": "exec_123"})
            return await asyncio.gather(t1, t2, t3)

        results = asyncio.run(run_concurrent())
        self.assertEqual(len(results), 3)
        res1 = json.loads(results[0][0][0].text) if isinstance(results[0], tuple) else json.loads(results[0][0].text)
        res2 = json.loads(results[1][0][0].text) if isinstance(results[1], tuple) else json.loads(results[1][0].text)
        res3 = json.loads(results[2][0][0].text) if isinstance(results[2], tuple) else json.loads(results[2][0].text)
        self.assertEqual(res1["execution_id"], "exec_123")
        self.assertEqual(res2["state"], "NORMAL")
        self.assertEqual(res3["action"], "CONTINUE")

    # 41. Provider agnosticism (No hardcoded provider)
    def test_41_provider_agnosticism(self):
        import importlib
        mod = importlib.import_module("infuse.mcp.tools")
        with open(mod.__file__, "r") as f:
            src = f.read()
        self.assertNotIn("openai.OpenAI", src)
        self.assertNotIn("anthropic.Anthropic", src)
        self.assertNotIn("google.generativeai", src)

    # 42. Agent agnosticism (No hardcoded agent)
    def test_42_agent_agnosticism(self):
        import importlib
        mod = importlib.import_module("infuse.mcp.tools")
        with open(mod.__file__, "r") as f:
            src = f.read()
        self.assertNotIn("ClaudeCodeAdapter", src)
        self.assertNotIn("CodexAdapter", src)
        self.assertNotIn("OpenCodeAdapter", src)

    # 43. Runtime agnosticism
    def test_43_runtime_agnosticism(self):
        import importlib
        mod = importlib.import_module("infuse.mcp.server")
        with open(mod.__file__, "r") as f:
            src = f.read()
        self.assertNotIn("subprocess.Popen", src)
        self.assertNotIn("os.system", src)

    # 44. Negative architectural test: No direct subprocess invocation
    def test_44_no_direct_subprocess(self):
        import importlib
        mod = importlib.import_module("infuse.mcp.main")
        with open(mod.__file__, "r") as f:
            src = f.read()
        self.assertNotIn("subprocess", src)

    # 45. Negative architectural test: No direct provider adapter imports
    def test_45_no_direct_provider_imports(self):
        import importlib
        for sub in ["server", "tools", "resources", "errors", "config", "main"]:
            m = importlib.import_module(f"infuse.mcp.{sub}")
            with open(m.__file__, "r") as f:
                content = f.read()
            self.assertNotIn("OpenAIProviderAdapter", content)
            self.assertNotIn("AnthropicProviderAdapter", content)
            self.assertNotIn("GeminiProviderAdapter", content)
            self.assertNotIn("DeepSeekProviderAdapter", content)

    # 46. Negative architectural test: No direct agent adapter imports
    def test_46_no_direct_agent_imports(self):
        import importlib
        for sub in ["server", "tools", "resources", "errors", "config", "main"]:
            m = importlib.import_module(f"infuse.mcp.{sub}")
            with open(m.__file__, "r") as f:
                content = f.read()
            self.assertNotIn("ClaudeCodeAdapter", content)
            self.assertNotIn("CodexAdapter", content)
            self.assertNotIn("OpenCodeAdapter", content)
            self.assertNotIn("HermesAdapter", content)

    # 47. Negative architectural test: No duplicate governor logic
    def test_47_no_duplicate_governor_logic(self):
        import importlib
        mod = importlib.import_module("infuse.mcp.tools")
        with open(mod.__file__, "r") as f:
            src = f.read()
        self.assertNotIn("calculate_cost", src)
        self.assertNotIn("evaluate_policy", src)
        self.assertNotIn("calculate_velocity", src)

    # 48. Negative architectural test: No duplicate policy evaluation
    def test_48_no_duplicate_policy_evaluation(self):
        import importlib
        mod = importlib.import_module("infuse.mcp.tools")
        with open(mod.__file__, "r") as f:
            src = f.read()
        self.assertNotIn("check_budget_limits", src)
        self.assertNotIn("check_token_limits", src)

    # 49. Negative architectural test: No local execution database
    def test_49_no_local_execution_db(self):
        import importlib
        for sub in ["server", "tools", "resources", "errors", "config", "main"]:
            m = importlib.import_module(f"infuse.mcp.{sub}")
            with open(m.__file__, "r") as f:
                content = f.read()
            self.assertNotIn("sqlite3", content)
            self.assertNotIn("SQLAlchemy", content)
            self.assertNotIn("tinydb", content)

    # 50. SDK delegation boundary
    def test_50_sdk_delegation_boundary(self):
        mock_client = MagicMock()
        mock_client.executions.get.return_value = ExecutionSummaryViewModel(
            execution_id="exec_boundary_test",
            status="COMPLETED",
            agent_name="TestAgent",
            task_description="Test Task",
            provider="mock",
            model="test",
            cost_usd=0.01,
            latency_ms=100.0,
        )
        server = create_mcp_server(client=mock_client)
        data = self._call_tool_sync("infuse_get_execution", {"execution_id": "exec_boundary_test"}, server=server)
        self.assertEqual(data["execution_id"], "exec_boundary_test")
        mock_client.executions.get.assert_called_once_with("exec_boundary_test")

    # 51. CLI / parser test
    def test_51_cli_parser(self):
        parser = create_parser()
        args = parser.parse_args(["--endpoint", "http://remote:8000", "--timeout", "50", "--transport", "streamable_http"])
        self.assertEqual(args.base_url, "http://remote:8000")
        self.assertEqual(args.timeout, 50.0)
        self.assertEqual(args.transport, "streamable_http")

    # 52. Version flag in CLI
    def test_52_cli_version_flag(self):
        out_buf = io.StringIO()
        with patch("sys.stdout", out_buf):
            code = run_server(["--version"])
        self.assertEqual(code, 0)
        self.assertIn(__version__, out_buf.getvalue())

    # 53. Resource read: execution summary
    def test_53_resource_read_execution(self):
        res = asyncio.run(self.mcp.read_resource("infuse://executions/exec_123"))
        self.assertTrue(len(res) > 0)
        data = json.loads(res[0].content)
        self.assertEqual(data["execution_id"], "exec_123")

    # 54. Resource read: execution state
    def test_54_resource_read_state(self):
        res = asyncio.run(self.mcp.read_resource("infuse://executions/exec_123/state"))
        self.assertTrue(len(res) > 0)
        data = json.loads(res[0].content)
        self.assertEqual(data["execution_id"], "exec_123")
        self.assertEqual(data["state"], "NORMAL")

    # 55. Resource read: active policy
    def test_55_resource_read_active_policy(self):
        res = asyncio.run(self.mcp.read_resource("infuse://policies/active"))
        self.assertTrue(len(res) > 0)
        data = json.loads(res[0].content)
        self.assertEqual(data["policy_id"], "pol_default")

    # 56. Resource read: governor decision
    def test_56_resource_read_governor(self):
        res = asyncio.run(self.mcp.read_resource("infuse://governor/exec_123"))
        self.assertTrue(len(res) > 0)
        data = json.loads(res[0].content)
        self.assertEqual(data["execution_id"], "exec_123")
        self.assertEqual(data["action"], "CONTINUE")


if __name__ == "__main__":
    unittest.main()
