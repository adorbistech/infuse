"""Unit and integration tests for the INFUSE SDK (Block 28)."""

import json
import unittest
from datetime import datetime
from typing import Any, Dict

from infuse.contracts.control import (
    ControlCapability,
    ControlOperation,
    ControlResult,
    ControlStatus,
)
from infuse.contracts.events import EventSource, EventType, ExecutionEvent
from infuse.contracts.execution import (
    ExecutionContext,
    ExecutionRequirements,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    ExecutionTelemetry,
    NormalizedResponse,
    OperationRequest,
    TaskContext,
)
from infuse.contracts.frontend import ExecutionSummaryViewModel
from infuse.contracts.governor import GovernorAction, GovernorDecision
from infuse.contracts.policy import BudgetControls, GovernancePolicy
from infuse.contracts.state import ExecutionState
from infuse.control.boundary import ExecutionControlBoundary
from infuse.sdk import (
    AuthenticationError,
    ClientConfig,
    ConflictError,
    ControlClient,
    EventClient,
    ExecutionClient,
    ExecutionListResponse,
    GovernorClient,
    InfuseClient,
    InfuseSdkError,
    MalformedResponseError,
    NotFoundError,
    PolicyClient,
    PolicyListResponse,
    ReferenceTransport,
    ServerError,
    StateInfo,
    TimeoutError,
    TransportError,
    ValidationError,
    redact_sdk_secrets,
)


class TestInfuseSdk(unittest.TestCase):
    """Test suite for Block 28 SDK layer."""

    def setUp(self) -> None:
        self.transport = ReferenceTransport()
        self.boundary = ExecutionControlBoundary()
        self.config = ClientConfig(base_url="http://localhost:8000", api_key="test-api-key")
        self.client = InfuseClient(
            config=self.config,
            transport=self.transport,
            control_boundary=self.boundary,
        )

    # ── 1. Client Initialization & Configuration ──────────────────────

    def test_01_client_initialization_defaults(self) -> None:
        c = InfuseClient()
        self.assertEqual(c.config.base_url, "http://localhost:8000")
        self.assertIsInstance(c.executions, ExecutionClient)
        self.assertIsInstance(c.policies, PolicyClient)
        self.assertIsInstance(c.events, EventClient)
        self.assertIsInstance(c.governor, GovernorClient)
        self.assertIsInstance(c.control, ControlClient)

    def test_02_transport_and_config_injection(self) -> None:
        custom_config = ClientConfig(
            base_url="https://api.infuse.example.com",
            api_key="secret-token-12345",
            timeout_seconds=45.0,
        )
        c = InfuseClient(config=custom_config, transport=self.transport)
        self.assertEqual(c.config.base_url, "https://api.infuse.example.com")
        self.assertEqual(c.config.api_key, "secret-token-12345")
        self.assertIs(c.transport, self.transport)

    # ── 2. Execution Operations ────────────────────────────────────────

    def test_03_execute_submission_typed_request(self) -> None:
        mock_result = ExecutionResult(
            execution_id="exec_sdk_1",
            request_id="req_sdk_1",
            status=ExecutionStatus.COMPLETED,
            response=NormalizedResponse(content="Execution finished successfully."),
            execution=ExecutionTelemetry(
                input_tokens=100,
                output_tokens=50,
                total_tokens=150,
                cost_usd=0.003,
                state=ExecutionState.NORMAL,
            ),
            decision=GovernorDecision(action=GovernorAction.CONTINUE),
        )
        self.transport.register_route(
            method="POST",
            path="/v1/execute",
            status_code=200,
            data=mock_result.model_dump(mode="json"),
        )

        req = ExecutionRequest(
            request_id="req_sdk_1",
            task=TaskContext(task_id="task_1", description="SDK execution test"),
            request=OperationRequest(messages=[{"role": "user", "content": "Hello INFUSE"}]),
        )
        res = self.client.execute(req)

        self.assertIsInstance(res, ExecutionResult)
        self.assertEqual(res.execution_id, "exec_sdk_1")
        self.assertEqual(res.status, ExecutionStatus.COMPLETED)
        self.assertEqual(res.response.content, "Execution finished successfully.")
        self.assertEqual(res.execution.total_tokens, 150)
        self.assertEqual(len(self.transport.invocations), 1)
        self.assertEqual(self.transport.invocations[0]["method"], "POST")
        self.assertEqual(self.transport.invocations[0]["path"], "/v1/execute")

    def test_04_execute_submission_dict_request(self) -> None:
        mock_result = ExecutionResult(
            execution_id="exec_sdk_2",
            request_id="req_sdk_2",
            status=ExecutionStatus.COMPLETED,
        )
        self.transport.register_route(
            method="POST",
            path="/v1/execute",
            status_code=200,
            data=mock_result.model_dump(mode="json"),
        )

        dict_req = {
            "request_id": "req_sdk_2",
            "task": {"task_id": "task_2", "description": "Dict payload test"},
            "request": {"messages": [{"role": "user", "content": "Test"}]},
        }
        res = self.client.execute(dict_req)
        self.assertEqual(res.execution_id, "exec_sdk_2")

    def test_05_get_execution_retrieval(self) -> None:
        mock_summary = ExecutionSummaryViewModel(
            execution_id="exec_sdk_3",
            agent_name="codex",
            task_description="Build feature",
            status="RUNNING",
            provider="openai",
            model="gpt-4o",
            runtime_seconds=12,
        )
        self.transport.register_route(
            method="GET",
            path="/v1/executions/exec_sdk_3",
            status_code=200,
            data=mock_summary.model_dump(mode="json"),
        )

        summary = self.client.get_execution("exec_sdk_3")
        self.assertIsInstance(summary, ExecutionSummaryViewModel)
        self.assertEqual(summary.execution_id, "exec_sdk_3")
        self.assertEqual(summary.agent_name, "codex")
        self.assertEqual(summary.provider, "openai")

    def test_06_get_execution_state(self) -> None:
        mock_summary = ExecutionSummaryViewModel(
            execution_id="exec_sdk_4",
            agent_name="claude",
            task_description="Refactor codebase",
            status="NORMAL",
            provider="anthropic",
            model="claude-3-5-sonnet",
        )
        self.transport.register_route(
            method="GET",
            path="/v1/executions/exec_sdk_4",
            status_code=200,
            data=mock_summary.model_dump(mode="json"),
        )

        state_info = self.client.get_state("exec_sdk_4")
        self.assertIsInstance(state_info, StateInfo)
        self.assertEqual(state_info.execution_id, "exec_sdk_4")
        self.assertEqual(state_info.state, ExecutionState.NORMAL)

    def test_07_list_executions_with_pagination_and_filters(self) -> None:
        mock_items = [
            ExecutionSummaryViewModel(
                execution_id=f"exec_sdk_list_{i}",
                agent_name="hermes",
                task_description=f"Task {i}",
                status="COMPLETED",
                provider="nous",
                model="hermes-3",
            ).model_dump(mode="json")
            for i in range(3)
        ]
        self.transport.register_route(
            method="GET",
            path="/v1/executions",
            status_code=200,
            data={"items": mock_items, "total": 3, "limit": 10, "offset": 0},
        )

        res = self.client.list_executions(query="Task", state="COMPLETED", limit=10, offset=0)
        self.assertIsInstance(res, ExecutionListResponse)
        self.assertEqual(len(res.items), 3)
        self.assertEqual(res.total, 3)
        self.assertEqual(res.items[0].execution_id, "exec_sdk_list_0")
        params = self.transport.invocations[0]["params"]
        self.assertEqual(params.get("query"), "Task")
        self.assertEqual(params.get("state"), "COMPLETED")

    # ── 3. Policy Operations ──────────────────────────────────────────

    def test_08_get_active_policy(self) -> None:
        mock_policy = GovernancePolicy(
            policy_id="pol_default",
            name="Standard Guardrails",
            budget=BudgetControls(max_cost_per_task=5.0),
        )
        self.transport.register_route(
            method="GET",
            path="/v1/policies",
            status_code=200,
            data={"policies": [mock_policy.model_dump(mode="json")], "active_policy": mock_policy.model_dump(mode="json")},
        )

        policy = self.client.get_active_policy()
        self.assertIsNotNone(policy)
        self.assertEqual(policy.policy_id, "pol_default")
        self.assertEqual(policy.budget.max_cost_per_task, 5.0)

    def test_09_list_policies(self) -> None:
        mock_p1 = GovernancePolicy(policy_id="pol_1", name="Policy 1")
        mock_p2 = GovernancePolicy(policy_id="pol_2", name="Policy 2")
        self.transport.register_route(
            method="GET",
            path="/v1/policies",
            status_code=200,
            data={"policies": [mock_p1.model_dump(mode="json"), mock_p2.model_dump(mode="json")], "active_policy": mock_p1.model_dump(mode="json")},
        )

        res = self.client.policies.list()
        self.assertIsInstance(res, PolicyListResponse)
        self.assertEqual(len(res.policies), 2)
        self.assertEqual(res.active_policy.policy_id, "pol_1")

    def test_10_update_policy(self) -> None:
        updated_policy = GovernancePolicy(
            policy_id="pol_strict",
            name="Strict Financial Controls",
            budget=BudgetControls(max_cost_per_task=1.0),
        )
        self.transport.register_route(
            method="PUT",
            path="/v1/policies/pol_strict",
            status_code=200,
            data=updated_policy.model_dump(mode="json"),
        )

        res = self.client.update_policy("pol_strict", updated_policy)
        self.assertEqual(res.policy_id, "pol_strict")
        self.assertEqual(res.budget.max_cost_per_task, 1.0)
        self.assertEqual(self.transport.invocations[0]["method"], "PUT")
        self.assertEqual(self.transport.invocations[0]["path"], "/v1/policies/pol_strict")

    # ── 4. Event Operations ────────────────────────────────────────────

    def test_11_publish_execution_event_envelope(self) -> None:
        self.transport.register_route(
            method="POST",
            path="/v1/executions/exec_ev_1/events",
            status_code=201,
            data={"status": "INGESTED", "event_id": "ev_001", "execution_id": "exec_ev_1", "schema_version": "1.0.0"},
        )

        ev = ExecutionEvent(
            event_id="ev_001",
            execution_id="exec_ev_1",
            type=EventType.EXECUTION_COMPLETED,
            source=EventSource.AGENT,
            sequence=1,
            payload={"step_index": 1, "status": "ok"},
        )
        resp = self.client.publish_event("exec_ev_1", ev)

        self.assertEqual(resp.status, "INGESTED")
        self.assertEqual(resp.event_id, "ev_001")
        self.assertEqual(resp.execution_id, "exec_ev_1")

    def test_12_publish_event_from_dict(self) -> None:
        self.transport.register_route(
            method="POST",
            path="/v1/executions/exec_ev_2/events",
            status_code=201,
            data={"status": "INGESTED", "event_id": "ev_002", "execution_id": "exec_ev_2"},
        )

        dict_ev = {
            "event_id": "ev_002",
            "execution_id": "exec_ev_2",
            "type": EventType.TOOL_CALLED.value,
            "source": EventSource.AGENT.value,
            "sequence": 2,
            "payload": {"tool_name": "bash"},
        }
        resp = self.client.publish_event("exec_ev_2", dict_ev)
        self.assertEqual(resp.event_id, "ev_002")

    # ── 5. Governor Visibility ────────────────────────────────────────

    def test_13_get_governor_decision(self) -> None:
        mock_summary = ExecutionSummaryViewModel(
            execution_id="exec_gov_1",
            agent_name="opencode",
            task_description="Execute batch",
            status="NORMAL",
            provider="openai",
            model="gpt-4o",
            routing_mode="CONTINUE",
        )
        self.transport.register_route(
            method="GET",
            path="/v1/executions/exec_gov_1",
            status_code=200,
            data=mock_summary.model_dump(mode="json"),
        )

        gov_info = self.client.get_governor_decision("exec_gov_1")
        self.assertEqual(gov_info.execution_id, "exec_gov_1")
        self.assertEqual(gov_info.action, GovernorAction.CONTINUE)

    # ── 6. Control Operations & Boundary ──────────────────────────────

    def test_14_control_dispatch_cancel(self) -> None:
        self.boundary.register_capability(
            "exec_ctrl_1",
            ControlCapability(supports_cancel=True, supported_actions=[GovernorAction.STOP, GovernorAction.CONTINUE]),
        )

        res = self.client.cancel("exec_ctrl_1")
        self.assertIsInstance(res, ControlResult)
        self.assertEqual(res.status, ControlStatus.ACCEPTED)
        self.assertEqual(res.action, GovernorAction.STOP)

    def test_15_control_dispatch_terminate(self) -> None:
        self.boundary.register_capability(
            "exec_ctrl_2",
            ControlCapability(supports_terminate=True, supported_actions=[GovernorAction.STOP, GovernorAction.CONTINUE]),
        )

        res = self.client.terminate("exec_ctrl_2")
        self.assertEqual(res.status, ControlStatus.ACCEPTED)
        self.assertEqual(res.action, GovernorAction.STOP)

    def test_16_control_dispatch_unsupported_action(self) -> None:
        self.boundary.register_capability(
            "exec_ctrl_3",
            ControlCapability(supports_throttle=False),
        )

        res = self.client.control.throttle("exec_ctrl_3", delay_ms=500)
        self.assertEqual(res.status, ControlStatus.UNSUPPORTED)
        self.assertIn("not supported", res.message)

    def test_17_control_capability_inspection(self) -> None:
        cap = ControlCapability(supports_cancel=True, supports_terminate=True, supports_throttle=False)
        self.boundary.register_capability("exec_ctrl_4", cap)

        retrieved_cap = self.client.get_control_capability("exec_ctrl_4")
        self.assertIsNotNone(retrieved_cap)
        self.assertTrue(retrieved_cap.supports_cancel)
        self.assertFalse(retrieved_cap.supports_throttle)

    # ── 7. Error Taxonomy & Edge Cases ────────────────────────────────

    def test_18_not_found_error_propagation(self) -> None:
        self.transport.register_route(
            method="GET",
            path="/v1/executions/nonexistent_id",
            status_code=404,
            data={"message": "Execution 'nonexistent_id' was not found."},
        )
        with self.assertRaises(NotFoundError) as ctx:
            self.client.get_execution("nonexistent_id")
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("not found", str(ctx.exception))

    def test_19_validation_error_propagation(self) -> None:
        self.transport.register_route(
            method="POST",
            path="/v1/execute",
            status_code=422,
            data={"message": "Invalid request parameters."},
        )
        req = ExecutionRequest(
            request_id="req_invalid",
            task=TaskContext(task_id="t_inv", description="Test"),
            request=OperationRequest(messages=[]),
        )
        with self.assertRaises(ValidationError) as ctx:
            self.client.execute(req)
        self.assertEqual(ctx.exception.status_code, 422)

    def test_20_authentication_error_propagation(self) -> None:
        self.transport.register_route(
            method="GET",
            path="/v1/policies",
            status_code=401,
            data={"message": "Missing or invalid API token."},
        )
        with self.assertRaises(AuthenticationError) as ctx:
            self.client.policies.list()
        self.assertEqual(ctx.exception.status_code, 401)

    def test_21_conflict_error_propagation(self) -> None:
        self.transport.register_route(
            method="PUT",
            path="/v1/policies/pol_conflict",
            status_code=409,
            data={"message": "Version conflict."},
        )
        policy = GovernancePolicy(policy_id="pol_conflict", name="Conflict")
        with self.assertRaises(ConflictError) as ctx:
            self.client.update_policy("pol_conflict", policy)
        self.assertEqual(ctx.exception.status_code, 409)

    def test_22_server_error_propagation(self) -> None:
        self.transport.register_route(
            method="POST",
            path="/v1/execute",
            status_code=500,
            data={"message": "Internal execution fault."},
        )
        req = ExecutionRequest(
            request_id="req_err",
            task=TaskContext(task_id="t_err", description="Test"),
            request=OperationRequest(messages=[]),
        )
        with self.assertRaises(ServerError) as ctx:
            self.client.execute(req)
        self.assertEqual(ctx.exception.status_code, 500)

    def test_23_timeout_error_propagation(self) -> None:
        self.transport.should_raise = TimeoutError("Request timed out after 30s")
        with self.assertRaises(TimeoutError):
            self.client.get_execution("exec_timeout")

    def test_24_transport_error_propagation(self) -> None:
        self.transport.should_raise = TransportError("Connection refused")
        with self.assertRaises(TransportError):
            self.client.get_execution("exec_conn_err")

    # ── 8. Secret Redaction & Security ────────────────────────────────

    def test_25_secret_redaction_in_errors(self) -> None:
        raw_msg = "Failed with api_key: secret_key_999999 and Bearer sk-ant-secret-12345678"
        redacted = redact_sdk_secrets(raw_msg)
        self.assertNotIn("secret_key_999999", redacted)
        self.assertNotIn("sk-ant-secret-12345678", redacted)
        self.assertIn("[REDACTED]", redacted)

        err = InfuseSdkError(raw_msg)
        self.assertNotIn("secret_key_999999", str(err))

    # ── 9. Identity & Canonical Integrity ─────────────────────────────

    def test_26_execution_identity_preservation(self) -> None:
        mock_result = ExecutionResult(
            execution_id="authoritative_exec_id_999",
            request_id="req_caller_777",
            status=ExecutionStatus.COMPLETED,
        )
        self.transport.register_route(
            method="POST",
            path="/v1/execute",
            status_code=200,
            data=mock_result.model_dump(mode="json"),
        )
        req = ExecutionRequest(
            request_id="req_caller_777",
            task=TaskContext(task_id="t_id", description="ID check"),
            request=OperationRequest(messages=[]),
        )
        res = self.client.execute(req)
        self.assertEqual(res.execution_id, "authoritative_exec_id_999")
        self.assertEqual(res.request_id, "req_caller_777")

    def test_27_control_operation_identity_preservation(self) -> None:
        self.boundary.register_capability("exec_op_id", ControlCapability(supports_cancel=True))
        res = self.client.control.dispatch(
            execution_id="exec_op_id",
            action=GovernorAction.STOP,
            operation_id="custom_op_id_123",
        )
        self.assertEqual(res.operation_id, "custom_op_id_123")
        self.assertEqual(res.execution_id, "exec_op_id")

    # ── 10. Architectural Negative Tests ──────────────────────────────

    def test_28_sdk_does_not_evaluate_governor_decisions(self) -> None:
        self.assertFalse(hasattr(self.client.governor, "evaluate"))
        self.assertFalse(hasattr(self.client.governor, "decide"))
        self.assertFalse(hasattr(self.client.governor, "calculate_action"))

    def test_29_sdk_does_not_evaluate_policies(self) -> None:
        self.assertFalse(hasattr(self.client.policies, "evaluate"))
        self.assertFalse(hasattr(self.client.policies, "check_budget"))

    def test_30_sdk_does_not_bypass_control_boundary(self) -> None:
        res = self.client.control.dispatch("unregistered_exec", GovernorAction.STOP)
        self.assertEqual(res.status, ControlStatus.UNSUPPORTED)

    def test_31_sdk_does_not_calculate_pricing(self) -> None:
        import infuse.sdk as sdk
        self.assertFalse(hasattr(sdk, "calculate_cost"))
        self.assertFalse(hasattr(sdk, "token_price"))

    def test_32_sdk_zero_provider_adapter_imports(self) -> None:
        import sys
        sdk_modules = [m for m in sys.modules if m.startswith("infuse.sdk")]
        for m in sdk_modules:
            mod = sys.modules[m]
            self.assertFalse(hasattr(mod, "OpenAIProviderAdapter"))
            self.assertFalse(hasattr(mod, "AnthropicProviderAdapter"))

    def test_33_sdk_zero_agent_adapter_imports(self) -> None:
        import sys
        sdk_modules = [m for m in sys.modules if m.startswith("infuse.sdk")]
        for m in sdk_modules:
            mod = sys.modules[m]
            self.assertFalse(hasattr(mod, "ClaudeCodeAdapter"))
            self.assertFalse(hasattr(mod, "CodexAdapter"))
            self.assertFalse(hasattr(mod, "HermesAdapter"))

    def test_34_empty_execution_id_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            self.client.get_execution("")
        with self.assertRaises(ValueError):
            self.client.cancel("")
        with self.assertRaises(ValueError):
            self.client.publish_event("", {})

    def test_35_invalid_pagination_parameters_raise_value_error(self) -> None:
        with self.assertRaises(ValueError):
            self.client.list_executions(limit=0)
        with self.assertRaises(ValueError):
            self.client.list_executions(limit=300)
        with self.assertRaises(ValueError):
            self.client.list_executions(offset=-1)

    def test_36_empty_policy_id_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            self.client.update_policy("", {"name": "Bad"})

    def test_37_invalid_execute_request_type_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            self.client.execute(None)

    def test_38_client_config_from_env(self) -> None:
        import os
        from unittest.mock import patch
        with patch.dict(os.environ, {"INFUSE_BASE_URL": "http://env-host:9000", "INFUSE_API_KEY": "env-key-999"}):
            cfg = ClientConfig.from_env()
            self.assertEqual(cfg.base_url, "http://env-host:9000")
            self.assertEqual(cfg.api_key, "env-key-999")

    def test_39_public_api_exports_all_symbols(self) -> None:
        from infuse.sdk import __all__ as sdk_exports
        self.assertIn("InfuseClient", sdk_exports)
        self.assertIn("ClientConfig", sdk_exports)
        self.assertIn("ExecutionRequest", sdk_exports)
        self.assertIn("ExecutionResult", sdk_exports)
        self.assertIn("GovernancePolicy", sdk_exports)
        self.assertIn("ExecutionEvent", sdk_exports)
        self.assertIn("ControlOperation", sdk_exports)
        self.assertIn("ControlResult", sdk_exports)

    def test_40_reference_transport_clear_functionality(self) -> None:
        self.transport.register_route("GET", "/test", 200, {"ok": True})
        self.transport.send_request("GET", "/test")
        self.assertEqual(len(self.transport.invocations), 1)

        self.transport.clear()
        self.assertEqual(len(self.transport.invocations), 0)
        with self.assertRaises(NotFoundError):
            self.transport.send_request("GET", "/test")


if __name__ == "__main__":
    unittest.main()
