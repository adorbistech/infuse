"""Unit and integration tests for Lovable Agent Adapter (Block 27)."""

import unittest
from datetime import datetime

from infuse.agents.errors import AgentExecutionError
from infuse.agents.lovable.adapter import LovableAdapter
from infuse.agents.lovable.errors import (
    LovableAdapterError,
    LovableAuthenticationError,
    LovableMalformedOutputError,
    LovableNetworkError,
    LovableTimeoutError,
)
from infuse.agents.lovable.models import (
    LovableAdapterConfig,
    LovableExecutionOutput,
    redact_lovable_secrets,
)
from infuse.agents.lovable.transport import (
    LovableHttpTransport,
    LovableReferenceTransport,
)
from infuse.agents.interfaces import IUniversalAgentAdapter
from infuse.agents.models import (
    AgentErrorRecord,
    AgentExecutionSession,
    AgentIdentity,
    AgentStepRequest,
    AgentStepResponse,
)
from infuse.contracts.capabilities import AgentCapability
from infuse.contracts.control import (
    ControlCapability,
    ControlOperation,
    ControlResult,
    ControlStatus,
)
from infuse.contracts.events import EventSource, EventType, ExecutionEvent
from infuse.contracts.governor import GovernorAction
from infuse.events.bus import InMemoryEventBus


class TestLovableAdapter(unittest.TestCase):
    """Test suite for Lovable Adapter (Block 27)."""

    def setUp(self) -> None:
        self.transport = LovableReferenceTransport()
        self.bus = InMemoryEventBus()
        self.config = LovableAdapterConfig(
            api_endpoint="https://api.lovable.dev/v1",
            api_key="lovable-test-key-12345",
            project_id="proj_block27_test",
            timeout_seconds=30.0,
        )
        self.adapter = LovableAdapter(
            agent_id="test_lovable",
            agent_name="lovable",
            config=self.config,
            transport=self.transport,
            event_bus=self.bus,
        )

    def test_01_implements_universal_agent_interface(self) -> None:
        self.assertIsInstance(self.adapter, IUniversalAgentAdapter)

    def test_02_identity_properties(self) -> None:
        ident = self.adapter.identity
        self.assertEqual(ident.agent_id, "test_lovable")
        self.assertEqual(ident.agent_name, "lovable")
        self.assertEqual(ident.runtime_type, "cloud_api")

    def test_03_capability_declaration(self) -> None:
        cap = self.adapter.get_agent_capability()
        self.assertIsInstance(cap, AgentCapability)
        self.assertTrue(cap.control_capabilities.supports_cancel)
        self.assertTrue(cap.control_capabilities.supports_terminate)
        self.assertFalse(cap.control_capabilities.supports_throttle)
        self.assertFalse(cap.control_capabilities.supports_next_step_switch)
        self.assertIn(GovernorAction.CONTINUE, cap.control_capabilities.supported_actions)
        self.assertIn(GovernorAction.STOP, cap.control_capabilities.supported_actions)

    def test_04_supports_action_predicate(self) -> None:
        self.assertTrue(self.adapter.supports_action(GovernorAction.CONTINUE))
        self.assertTrue(self.adapter.supports_action(GovernorAction.STOP))
        self.assertFalse(self.adapter.supports_action(GovernorAction.THROTTLE))
        self.assertFalse(self.adapter.supports_action(GovernorAction.SWITCH))
        self.assertFalse(self.adapter.supports_action(None))

    def test_05_attach_and_detach_execution(self) -> None:
        session = self.adapter.attach_execution("exec_lv1", metadata={"project_name": "landing_page"})
        self.assertIsInstance(session, AgentExecutionSession)
        self.assertEqual(session.execution_id, "exec_lv1")
        self.assertTrue(session.is_active)

        retrieved = self.adapter.get_session("exec_lv1")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.metadata.get("project_name"), "landing_page")

        self.adapter.detach_execution("exec_lv1")
        detached = self.adapter.get_session("exec_lv1")
        self.assertIsNotNone(detached)
        self.assertFalse(detached.is_active)

    def test_06_attach_empty_id_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            self.adapter.attach_execution("")

    def test_07_execute_step_success(self) -> None:
        req = AgentStepRequest(
            execution_id="exec_lv2",
            step_index=0,
            prompt="Create a responsive navbar with search",
        )
        resp = self.adapter.execute_step(req)
        self.assertIsInstance(resp, AgentStepResponse)
        self.assertEqual(resp.execution_id, "exec_lv2")
        self.assertEqual(resp.step_index, 0)
        self.assertIn("Lovable created UI components", resp.content)
        self.assertEqual(len(self.transport.invocations), 1)

    def test_08_execute_step_preserves_project_id_boundary(self) -> None:
        req = AgentStepRequest(
            execution_id="exec_lv3",
            step_index=1,
            prompt="Add dark mode toggle",
            parameters={"project_id": "custom_proj_999"},
        )
        resp = self.adapter.execute_step(req)
        inv = self.transport.invocations[0]
        self.assertEqual(inv["project_id"], "custom_proj_999")
        self.assertEqual(resp.metadata.get("project_id"), "custom_proj_999")
        # Ensure INFUSE execution ID is preserved and not replaced by project ID
        self.assertEqual(resp.execution_id, "exec_lv3")

    def test_09_execute_step_timeout_handling(self) -> None:
        self.transport.should_timeout = True
        req = AgentStepRequest(execution_id="exec_lv4", step_index=0, prompt="Large project build")
        with self.assertRaises(AgentExecutionError) as ctx:
            self.adapter.execute_step(req)
        self.assertIn("timed out", str(ctx.exception))

    def test_10_execute_step_auth_failure(self) -> None:
        self.transport.should_raise_auth = True
        req = AgentStepRequest(execution_id="exec_lv5", step_index=0, prompt="Protected project")
        with self.assertRaises(AgentExecutionError) as ctx:
            self.adapter.execute_step(req)
        self.assertIn("authentication failed", str(ctx.exception))

    def test_11_execute_step_network_failure(self) -> None:
        self.transport.should_fail = True
        req = AgentStepRequest(execution_id="exec_lv6", step_index=0, prompt="API build")
        with self.assertRaises(AgentExecutionError) as ctx:
            self.adapter.execute_step(req)
        self.assertIn("returned 500 error", str(ctx.exception))

    def test_12_execute_control_stop_cancel(self) -> None:
        self.adapter.attach_execution("exec_ctrl_lv1")
        op = ControlOperation(
            operation_id="op_lv1",
            execution_id="exec_ctrl_lv1",
            action=GovernorAction.STOP,
        )
        res = self.adapter.execute_control(op)
        self.assertEqual(res.status, ControlStatus.COMPLETED)
        self.assertIn("exec_ctrl_lv1", self.transport.cancelled_executions)

    def test_13_execute_control_stop_terminate(self) -> None:
        self.adapter.attach_execution("exec_ctrl_lv2")
        op = ControlOperation(
            operation_id="op_lv2",
            execution_id="exec_ctrl_lv2",
            action=GovernorAction.STOP,
            params={"hard": True},
        )
        res = self.adapter.execute_control(op)
        self.assertEqual(res.status, ControlStatus.COMPLETED)
        self.assertIn("exec_ctrl_lv2", self.transport.terminated_sessions)

    def test_14_execute_control_unsupported_action(self) -> None:
        op = ControlOperation(
            operation_id="op_lv3",
            execution_id="exec_ctrl_lv3",
            action=GovernorAction.THROTTLE,
        )
        res = self.adapter.execute_control(op)
        self.assertEqual(res.status, ControlStatus.UNSUPPORTED)
        self.assertIn("does not support", res.message)

    def test_15_execute_control_continue_action(self) -> None:
        op = ControlOperation(
            operation_id="op_lv4",
            execution_id="exec_ctrl_lv4",
            action=GovernorAction.CONTINUE,
        )
        res = self.adapter.execute_control(op)
        self.assertEqual(res.status, ControlStatus.COMPLETED)

    def test_16_event_bus_publishes_step_completion(self) -> None:
        published_events: list = []
        self.bus.subscribe(lambda e: published_events.append(e))

        req = AgentStepRequest(execution_id="exec_ev_lv1", step_index=0, prompt="Generate view")
        self.adapter.execute_step(req)

        self.assertGreater(len(published_events), 0)
        step_ev = published_events[0]
        self.assertEqual(step_ev.type, EventType.EXECUTION_COMPLETED)
        self.assertEqual(step_ev.source, EventSource.AGENT)
        self.assertEqual(step_ev.execution_id, "exec_ev_lv1")

    def test_17_tool_observability_normalization(self) -> None:
        published_events: list = []
        self.bus.subscribe(lambda e: published_events.append(e))

        self.transport.custom_output = LovableExecutionOutput(
            response_data={
                "result": "Rendered components",
                "tools": [
                    {"name": "tailwind_compiler", "args": {"theme": "dark"}, "duration_ms": 12.0, "status": "success"}
                ],
            },
            status_code=200,
            duration_ms=15.0,
        )
        req = AgentStepRequest(execution_id="exec_tools_lv1", step_index=0, prompt="Compile style")
        self.adapter.execute_step(req)

        tool_events = [e for e in published_events if e.type in (EventType.TOOL_CALLED, EventType.TOOL_COMPLETED)]
        self.assertEqual(len(tool_events), 2)
        self.assertEqual(tool_events[0].type, EventType.TOOL_CALLED)
        self.assertEqual(tool_events[0].payload["tool_name"], "tailwind_compiler")
        self.assertEqual(tool_events[1].type, EventType.TOOL_COMPLETED)
        self.assertEqual(tool_events[1].payload["tool_name"], "tailwind_compiler")

    def test_18_web_observability_normalization(self) -> None:
        published_events: list = []
        self.bus.subscribe(lambda e: published_events.append(e))

        self.transport.custom_output = LovableExecutionOutput(
            response_data={
                "result": "Imported icons package",
                "web_requests": [
                    {"url": "https://lucide.dev/api", "method": "GET", "status_code": 200, "duration_ms": 28.0}
                ],
            },
            status_code=200,
            duration_ms=30.0,
        )
        req = AgentStepRequest(execution_id="exec_web_lv1", step_index=0, prompt="Fetch icons")
        self.adapter.execute_step(req)

        web_events = [e for e in published_events if e.type in (EventType.WEB_REQUEST, EventType.WEB_RESPONSE)]
        self.assertEqual(len(web_events), 2)
        self.assertEqual(web_events[0].type, EventType.WEB_REQUEST)
        self.assertEqual(web_events[0].payload["url"], "https://lucide.dev/api")
        self.assertEqual(web_events[1].type, EventType.WEB_RESPONSE)
        self.assertEqual(web_events[1].payload["status_code"], 200)

    def test_19_secret_redaction_utility(self) -> None:
        raw_msg = "Failed auth: api_key: lovable_sec_token_88888888 and Bearer lovable-tok-999999"
        redacted = redact_lovable_secrets(raw_msg)
        self.assertNotIn("lovable_sec_token_88888888", redacted)
        self.assertNotIn("lovable-tok-999999", redacted)
        self.assertIn("[REDACTED]", redacted)

    def test_20_normalize_error_record(self) -> None:
        err = LovableAuthenticationError("Invalid API key api_key: sec_pass_1234")
        record = self.adapter.normalize_error(err, execution_id="exec_err_lv1")
        self.assertIsInstance(record, AgentErrorRecord)
        self.assertEqual(record.error_code, "LovableAuthenticationError")
        self.assertNotIn("sec_pass_1234", record.message)
        self.assertEqual(record.details.get("execution_id"), "exec_err_lv1")

    def test_21_session_isolation_across_multiple_executions(self) -> None:
        self.adapter.attach_execution("exec_LV_A")
        self.adapter.attach_execution("exec_LV_B")

        req_A = AgentStepRequest(execution_id="exec_LV_A", step_index=0, prompt="Build A")
        req_B = AgentStepRequest(execution_id="exec_LV_B", step_index=0, prompt="Build B")

        resp_A = self.adapter.execute_step(req_A)
        resp_B = self.adapter.execute_step(req_B)

        self.assertEqual(resp_A.execution_id, "exec_LV_A")
        self.assertEqual(resp_B.execution_id, "exec_LV_B")

        sess_A = self.adapter.get_session("exec_LV_A")
        sess_B = self.adapter.get_session("exec_LV_B")
        self.assertEqual(sess_A.step_count, 1)
        self.assertEqual(sess_B.step_count, 1)

    def test_22_http_transport_missing_key_availability(self) -> None:
        transport = LovableHttpTransport(api_key=None)
        self.assertFalse(transport.is_available())

    def test_23_null_request_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            self.adapter.execute_step(None)

    def test_24_empty_execution_id_in_step_raises_value_error(self) -> None:
        req = AgentStepRequest(execution_id="", step_index=0, prompt="Hello")
        with self.assertRaises(ValueError):
            self.adapter.execute_step(req)

    def test_25_null_operation_in_control_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            self.adapter.execute_control(None)


if __name__ == "__main__":
    unittest.main()
