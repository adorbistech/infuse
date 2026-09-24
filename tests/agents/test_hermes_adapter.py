"""Unit and integration tests for Hermes Agent Adapter (Block 27)."""

import unittest
from datetime import datetime
from unittest.mock import MagicMock

from infuse.agents.errors import AgentControlError, AgentExecutionError
from infuse.agents.hermes.adapter import HermesAdapter
from infuse.agents.hermes.errors import (
    HermesAdapterError,
    HermesCLINotFoundError,
    HermesProcessError,
    HermesTimeoutError,
)
from infuse.agents.hermes.models import (
    HermesAdapterConfig,
    HermesExecutionOutput,
    redact_hermes_secrets,
)
from infuse.agents.hermes.transport import (
    HermesReferenceTransport,
    HermesSubprocessTransport,
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


class TestHermesAdapter(unittest.TestCase):
    """Test suite for Hermes Adapter (Block 27)."""

    def setUp(self) -> None:
        self.transport = HermesReferenceTransport()
        self.bus = InMemoryEventBus()
        self.config = HermesAdapterConfig(timeout_seconds=30.0)
        self.adapter = HermesAdapter(
            agent_id="test_hermes",
            agent_name="hermes",
            config=self.config,
            transport=self.transport,
            event_bus=self.bus,
        )

    def test_01_implements_universal_agent_interface(self) -> None:
        self.assertIsInstance(self.adapter, IUniversalAgentAdapter)

    def test_02_identity_properties(self) -> None:
        ident = self.adapter.identity
        self.assertEqual(ident.agent_id, "test_hermes")
        self.assertEqual(ident.agent_name, "hermes")
        self.assertEqual(ident.runtime_type, "cli")

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
        session = self.adapter.attach_execution("exec_h1", metadata={"task": "analysis"})
        self.assertIsInstance(session, AgentExecutionSession)
        self.assertEqual(session.execution_id, "exec_h1")
        self.assertTrue(session.is_active)

        retrieved = self.adapter.get_session("exec_h1")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.metadata.get("task"), "analysis")

        self.adapter.detach_execution("exec_h1")
        detached = self.adapter.get_session("exec_h1")
        self.assertIsNotNone(detached)
        self.assertFalse(detached.is_active)

    def test_06_attach_empty_id_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            self.adapter.attach_execution("")

    def test_07_execute_step_success(self) -> None:
        req = AgentStepRequest(
            execution_id="exec_h2",
            step_index=0,
            prompt="Analyze performance logs",
        )
        resp = self.adapter.execute_step(req)
        self.assertIsInstance(resp, AgentStepResponse)
        self.assertEqual(resp.execution_id, "exec_h2")
        self.assertEqual(resp.step_index, 0)
        self.assertIn("Hermes agent response", resp.content)
        self.assertEqual(len(self.transport.invocations), 1)

    def test_08_execute_step_passes_oneshot_args(self) -> None:
        req = AgentStepRequest(
            execution_id="exec_h3",
            step_index=1,
            prompt="Find bugs in module",
        )
        self.adapter.execute_step(req)
        inv = self.transport.invocations[0]
        args = inv["args"]
        self.assertIn("-z", args)
        self.assertIn("Find bugs in module", args)
        self.assertIn("--accept-hooks", args)

    def test_09_execute_step_with_model_override(self) -> None:
        custom_config = HermesAdapterConfig(default_model="anthropic/claude-sonnet-4.6")
        custom_adapter = HermesAdapter(config=custom_config, transport=self.transport)
        req = AgentStepRequest(execution_id="exec_h4", step_index=0, prompt="Refactor")
        custom_adapter.execute_step(req)
        args = self.transport.invocations[0]["args"]
        self.assertIn("-m", args)
        self.assertIn("anthropic/claude-sonnet-4.6", args)

    def test_10_execute_step_timeout_handling(self) -> None:
        self.transport.should_timeout = True
        req = AgentStepRequest(execution_id="exec_h5", step_index=0, prompt="Slow query")
        with self.assertRaises(AgentExecutionError) as ctx:
            self.adapter.execute_step(req)
        self.assertIn("timed out", str(ctx.exception))

    def test_11_execute_step_process_failure(self) -> None:
        self.transport.should_fail = True
        req = AgentStepRequest(execution_id="exec_h6", step_index=0, prompt="Faulty query")
        with self.assertRaises(AgentExecutionError) as ctx:
            self.adapter.execute_step(req)
        self.assertIn("exited with error", str(ctx.exception))

    def test_12_execute_control_stop_cancel(self) -> None:
        self.adapter.attach_execution("exec_ctrl_1")
        op = ControlOperation(
            operation_id="op_1",
            execution_id="exec_ctrl_1",
            action=GovernorAction.STOP,
        )
        res = self.adapter.execute_control(op)
        self.assertEqual(res.status, ControlStatus.COMPLETED)
        self.assertIn("exec_ctrl_1", self.transport.cancelled_executions)

    def test_13_execute_control_stop_terminate(self) -> None:
        self.adapter.attach_execution("exec_ctrl_2")
        op = ControlOperation(
            operation_id="op_2",
            execution_id="exec_ctrl_2",
            action=GovernorAction.STOP,
            params={"hard": True},
        )
        res = self.adapter.execute_control(op)
        self.assertEqual(res.status, ControlStatus.COMPLETED)
        self.assertIn("exec_ctrl_2", self.transport.terminated_sessions)

    def test_14_execute_control_unsupported_action(self) -> None:
        op = ControlOperation(
            operation_id="op_3",
            execution_id="exec_ctrl_3",
            action=GovernorAction.THROTTLE,
        )
        res = self.adapter.execute_control(op)
        self.assertEqual(res.status, ControlStatus.UNSUPPORTED)
        self.assertIn("does not support", res.message)

    def test_15_execute_control_continue_action(self) -> None:
        op = ControlOperation(
            operation_id="op_4",
            execution_id="exec_ctrl_4",
            action=GovernorAction.CONTINUE,
        )
        res = self.adapter.execute_control(op)
        self.assertEqual(res.status, ControlStatus.COMPLETED)

    def test_16_event_bus_publishes_step_completion(self) -> None:
        published_events: list = []
        self.bus.subscribe(lambda e: published_events.append(e))

        req = AgentStepRequest(execution_id="exec_ev_1", step_index=0, prompt="Run tests")
        self.adapter.execute_step(req)

        self.assertGreater(len(published_events), 0)
        step_ev = published_events[0]
        self.assertEqual(step_ev.type, EventType.EXECUTION_COMPLETED)
        self.assertEqual(step_ev.source, EventSource.AGENT)
        self.assertEqual(step_ev.execution_id, "exec_ev_1")

    def test_17_tool_observability_normalization(self) -> None:
        published_events: list = []
        self.bus.subscribe(lambda e: published_events.append(e))

        self.transport.custom_output = HermesExecutionOutput(
            stdout="",
            stderr="",
            return_code=0,
            parsed_json={
                "result": "Ran grep",
                "tools": [
                    {"name": "grep", "args": {"pattern": "TODO"}, "duration_ms": 15.0, "status": "success"}
                ],
            },
        )
        req = AgentStepRequest(execution_id="exec_tools_1", step_index=0, prompt="Search TODOs")
        self.adapter.execute_step(req)

        tool_events = [e for e in published_events if e.type in (EventType.TOOL_CALLED, EventType.TOOL_COMPLETED)]
        self.assertEqual(len(tool_events), 2)
        self.assertEqual(tool_events[0].type, EventType.TOOL_CALLED)
        self.assertEqual(tool_events[0].payload["tool_name"], "grep")
        self.assertEqual(tool_events[1].type, EventType.TOOL_COMPLETED)
        self.assertEqual(tool_events[1].payload["tool_name"], "grep")

    def test_18_web_observability_normalization(self) -> None:
        published_events: list = []
        self.bus.subscribe(lambda e: published_events.append(e))

        self.transport.custom_output = HermesExecutionOutput(
            stdout="",
            stderr="",
            return_code=0,
            parsed_json={
                "result": "Queried docs",
                "web_requests": [
                    {"url": "https://nousresearch.com/docs", "method": "GET", "status_code": 200, "duration_ms": 45.0}
                ],
            },
        )
        req = AgentStepRequest(execution_id="exec_web_1", step_index=0, prompt="Read docs")
        self.adapter.execute_step(req)

        web_events = [e for e in published_events if e.type in (EventType.WEB_REQUEST, EventType.WEB_RESPONSE)]
        self.assertEqual(len(web_events), 2)
        self.assertEqual(web_events[0].type, EventType.WEB_REQUEST)
        self.assertEqual(web_events[0].payload["url"], "https://nousresearch.com/docs")
        self.assertEqual(web_events[1].type, EventType.WEB_RESPONSE)
        self.assertEqual(web_events[1].payload["status_code"], 200)

    def test_19_secret_redaction_utility(self) -> None:
        raw_msg = "Error connecting with api_key: secret_key_12345678 and Bearer sk-ant-api03-abcdefghijkl"
        redacted = redact_hermes_secrets(raw_msg)
        self.assertNotIn("secret_key_12345678", redacted)
        self.assertNotIn("sk-ant-api03-abcdefghijkl", redacted)
        self.assertIn("[REDACTED]", redacted)

    def test_20_normalize_error_record(self) -> None:
        err = HermesProcessError("Fatal error with auth: super_secret_pass_123")
        record = self.adapter.normalize_error(err, execution_id="exec_err_1")
        self.assertIsInstance(record, AgentErrorRecord)
        self.assertEqual(record.error_code, "HermesProcessError")
        self.assertNotIn("super_secret_pass_123", record.message)
        self.assertEqual(record.details.get("execution_id"), "exec_err_1")

    def test_21_session_isolation_across_multiple_executions(self) -> None:
        self.adapter.attach_execution("exec_A")
        self.adapter.attach_execution("exec_B")

        req_A = AgentStepRequest(execution_id="exec_A", step_index=0, prompt="Task A")
        req_B = AgentStepRequest(execution_id="exec_B", step_index=0, prompt="Task B")

        resp_A = self.adapter.execute_step(req_A)
        resp_B = self.adapter.execute_step(req_B)

        self.assertEqual(resp_A.execution_id, "exec_A")
        self.assertEqual(resp_B.execution_id, "exec_B")

        sess_A = self.adapter.get_session("exec_A")
        sess_B = self.adapter.get_session("exec_B")
        self.assertEqual(sess_A.step_count, 1)
        self.assertEqual(sess_B.step_count, 1)

    def test_22_subprocess_transport_discovery_and_availability(self) -> None:
        transport = HermesSubprocessTransport(cli_path="/Volumes/Adorbis/bin/hermes")
        self.assertTrue(transport.is_available())

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

    def test_26_transport_not_found_handling(self) -> None:
        self.transport.should_raise_not_found = True
        req = AgentStepRequest(execution_id="exec_nf", step_index=0, prompt="Test")
        with self.assertRaises(AgentExecutionError):
            self.adapter.execute_step(req)


if __name__ == "__main__":
    unittest.main()
