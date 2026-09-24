"""Comprehensive Unit, Integration, and Boundary Test Suite for Block 26 Codex Adapter."""

import inspect
import json
import sys
import threading
import unittest
from typing import Any, Dict, List, Optional

from infuse.contracts.capabilities import AgentCapability
from infuse.contracts.control import (
    ControlCapability,
    ControlOperation,
    ControlResult,
    ControlStatus,
)
from infuse.contracts.events import EventSource, EventType, ExecutionEvent
from infuse.contracts.governor import GovernorAction
from infuse.control.boundary import ExecutionControlBoundary
from infuse.events.bus import InMemoryEventBus
from infuse.agents.errors import (
    AgentAdapterError,
    AgentControlError,
    AgentExecutionError,
)
from infuse.agents.interfaces import IUniversalAgentAdapter
from infuse.agents.models import (
    AgentErrorRecord,
    AgentExecutionSession,
    AgentIdentity,
    AgentStepRequest,
    AgentStepResponse,
)
from infuse.agents.codex.adapter import CodexAdapter
from infuse.agents.codex.errors import (
    CodexAdapterError,
    CodexCLINotFoundError,
    CodexProcessError,
    CodexTimeoutError,
)
from infuse.agents.codex.models import (
    CodexAdapterConfig,
    CodexExecutionOutput,
    redact_codex_secrets,
)
from infuse.agents.codex.transport import (
    CodexReferenceTransport,
    CodexSubprocessTransport,
)


class TestCodexAdapter(unittest.TestCase):
    """Test suite verifying Codex adapter contracts, transport, controls, tool/web events, security, and isolation."""

    def setUp(self) -> None:
        self.transport = CodexReferenceTransport()
        self.adapter = CodexAdapter(transport=self.transport)

    # 1. Identity
    def test_01_codex_identity(self) -> None:
        """Verify Codex adapter identity matches universal specification."""
        ident = self.adapter.identity
        self.assertEqual(ident.agent_name, "codex")
        self.assertEqual(ident.version, "1.0.0")
        self.assertEqual(ident.runtime_type, "cli")

    def test_02_identity_serialization(self) -> None:
        """Verify AgentIdentity serialization and deserialization."""
        ident = self.adapter.identity
        data = ident.model_dump()
        self.assertEqual(data["agent_name"], "codex")
        restored = AgentIdentity.model_validate(data)
        self.assertEqual(restored.agent_id, self.adapter.identity.agent_id)

    def test_03_identity_consistency(self) -> None:
        """Verify identity property returns an immutable deep copy."""
        ident1 = self.adapter.identity
        ident2 = self.adapter.identity
        self.assertEqual(ident1.agent_id, ident2.agent_id)
        self.assertIsNot(ident1, ident2)

    def test_04_execution_identity_preservation(self) -> None:
        """Verify canonical execution ID is strictly preserved across requests and responses."""
        req = AgentStepRequest(execution_id="codex_exec_preserve_01", step_index=0, prompt="Run task")
        resp = self.adapter.execute_step(req)

        self.assertEqual(resp.execution_id, "codex_exec_preserve_01")
        session = self.adapter.get_session("codex_exec_preserve_01")
        self.assertIsNotNone(session)
        self.assertEqual(session.execution_id, "codex_exec_preserve_01")

    # 2. Universal Contract
    def test_05_interface_compliance(self) -> None:
        """Verify CodexAdapter cleanly implements IUniversalAgentAdapter."""
        self.assertIsInstance(self.adapter, IUniversalAgentAdapter)
        self.assertEqual(self.adapter.executor_id, self.adapter.identity.agent_id)

    def test_06_step_request_normalization(self) -> None:
        """Verify AgentStepRequest is properly parsed and passed to transport arguments."""
        req = AgentStepRequest(
            execution_id="codex_exec_02",
            step_index=1,
            prompt="Refactor database models",
            parameters={"model": "o3-mini"},
        )
        self.adapter.execute_step(req)

        self.assertEqual(len(self.transport.invocations), 1)
        inv = self.transport.invocations[0]
        self.assertEqual(inv["execution_id"], "codex_exec_02")
        self.assertIn("exec", inv["args"])
        self.assertIn("--json", inv["args"])
        self.assertIn("Refactor database models", inv["args"])

    def test_07_step_response_structure(self) -> None:
        """Verify AgentStepResponse contains required contract fields."""
        req = AgentStepRequest(execution_id="codex_exec_03", step_index=0, prompt="Test prompt")
        resp = self.adapter.execute_step(req)

        self.assertEqual(resp.execution_id, "codex_exec_03")
        self.assertEqual(resp.step_index, 0)
        self.assertIsNotNone(resp.content)
        self.assertEqual(resp.finish_reason, "stop")
        self.assertIn("agent_id", resp.metadata)
        self.assertIn("duration_ms", resp.metadata)

    def test_08_session_creation(self) -> None:
        """Verify explicit session attachment returns an active AgentExecutionSession."""
        session = self.adapter.attach_execution("codex_sess_01", metadata={"branch": "main"})
        self.assertTrue(session.is_active)
        self.assertEqual(session.execution_id, "codex_sess_01")
        self.assertEqual(session.metadata.get("branch"), "main")

    def test_09_session_lookup(self) -> None:
        """Verify get_session returns the active session or None."""
        self.adapter.attach_execution("codex_sess_02")
        sess = self.adapter.get_session("codex_sess_02")
        self.assertIsNotNone(sess)
        self.assertTrue(sess.is_active)

        none_sess = self.adapter.get_session("non_existent_sess")
        self.assertIsNone(none_sess)

    def test_10_session_isolation(self) -> None:
        """Verify Execution A and Execution B sessions do not share state."""
        self.adapter.attach_execution("exec_codex_A")
        self.adapter.attach_execution("exec_codex_B")

        self.adapter.execute_step(AgentStepRequest(execution_id="exec_codex_A", step_index=0))
        self.adapter.execute_step(AgentStepRequest(execution_id="exec_codex_A", step_index=1))
        self.adapter.execute_step(AgentStepRequest(execution_id="exec_codex_B", step_index=0))

        sess_a = self.adapter.get_session("exec_codex_A")
        sess_b = self.adapter.get_session("exec_codex_B")

        self.assertEqual(sess_a.step_count, 2)
        self.assertEqual(sess_b.step_count, 1)

    # 3. Execution
    def test_11_successful_execution(self) -> None:
        """Verify reference transport execution produces a valid response."""
        req = AgentStepRequest(execution_id="exec_codex_succ_01", step_index=0, prompt="Hello Codex")
        resp = self.adapter.execute_step(req)
        self.assertIn("Codex response", resp.content)

    def test_12_empty_response_handling(self) -> None:
        """Verify empty transport stdout does not cause an uncaught crash."""
        self.transport.custom_output = CodexExecutionOutput(
            stdout="",
            stderr="",
            return_code=0,
            duration_ms=4.0,
        )
        req = AgentStepRequest(execution_id="exec_codex_empty_01", step_index=0)
        resp = self.adapter.execute_step(req)
        self.assertEqual(resp.content, "")

    def test_13_structured_response_parsing(self) -> None:
        """Verify JSON output from Codex is parsed into raw_output and content."""
        self.transport.custom_output = CodexExecutionOutput(
            stdout=json.dumps({"result": "Refactored code cleanly", "files_modified": 3}),
            stderr="",
            return_code=0,
            parsed_json={"result": "Refactored code cleanly", "files_modified": 3},
            duration_ms=12.0,
        )
        req = AgentStepRequest(execution_id="exec_codex_struct_01", step_index=0)
        resp = self.adapter.execute_step(req)
        self.assertEqual(resp.content, "Refactored code cleanly")
        self.assertEqual(resp.raw_output.get("files_modified"), 3)

    def test_14_jsonl_events_parsing(self) -> None:
        """Verify JSONL stream events from Codex are parsed into events_jsonl."""
        self.transport.custom_output = CodexExecutionOutput(
            stdout='{"type":"status","msg":"running"}\n{"type":"result","result":"Success message"}',
            stderr="",
            return_code=0,
            parsed_json={"type": "result", "result": "Success message"},
            events_jsonl=[
                {"type": "status", "msg": "running"},
                {"type": "result", "result": "Success message"},
            ],
            duration_ms=18.0,
        )
        req = AgentStepRequest(execution_id="exec_codex_jsonl_01", step_index=0)
        resp = self.adapter.execute_step(req)
        self.assertEqual(resp.content, "Success message")
        self.assertEqual(resp.metadata.get("events_count"), 2)

    def test_15_malformed_response_fallback(self) -> None:
        """Verify non-JSON stdout falls back safely to plain string content."""
        self.transport.custom_output = CodexExecutionOutput(
            stdout="Raw output text from Codex CLI execution",
            stderr="",
            return_code=0,
            parsed_json=None,
            duration_ms=6.0,
        )
        req = AgentStepRequest(execution_id="exec_codex_raw_01", step_index=0)
        resp = self.adapter.execute_step(req)
        self.assertEqual(resp.content, "Raw output text from Codex CLI execution")

    def test_16_process_failure_handling(self) -> None:
        """Verify transport non-zero process failure raises AgentExecutionError."""
        self.transport.should_fail = True
        req = AgentStepRequest(execution_id="exec_codex_fail_01", step_index=0)
        with self.assertRaises(AgentExecutionError):
            self.adapter.execute_step(req)

    def test_17_startup_failure_not_found(self) -> None:
        """Verify executable not found error maps to AgentExecutionError."""
        self.transport.should_raise_not_found = True
        req = AgentStepRequest(execution_id="exec_codex_not_found_01", step_index=0)
        with self.assertRaises(AgentExecutionError):
            self.adapter.execute_step(req)

    def test_18_runtime_timeout(self) -> None:
        """Verify CLI process timeout maps to AgentExecutionError."""
        self.transport.should_timeout = True
        req = AgentStepRequest(execution_id="exec_codex_timeout_01", step_index=0)
        with self.assertRaises(AgentExecutionError):
            self.adapter.execute_step(req)

    def test_19_duration_ms_telemetry(self) -> None:
        """Verify execution duration is captured in response metadata."""
        self.transport.custom_output = CodexExecutionOutput(
            stdout="DONE",
            return_code=0,
            duration_ms=42.5,
        )
        req = AgentStepRequest(execution_id="exec_codex_dur_01", step_index=0)
        resp = self.adapter.execute_step(req)
        self.assertEqual(resp.metadata.get("duration_ms"), 42.5)

    def test_20_auto_attach_on_step(self) -> None:
        """Verify step execution auto-attaches a session if unattached."""
        req = AgentStepRequest(execution_id="exec_codex_auto_01", step_index=0)
        self.adapter.execute_step(req)
        sess = self.adapter.get_session("exec_codex_auto_01")
        self.assertIsNotNone(sess)
        self.assertTrue(sess.is_active)

    def test_21_step_counter_monotonic(self) -> None:
        """Verify step counter monotonically increases across steps."""
        self.adapter.attach_execution("exec_codex_mono_01")
        for i in range(3):
            self.adapter.execute_step(AgentStepRequest(execution_id="exec_codex_mono_01", step_index=i))
        sess = self.adapter.get_session("exec_codex_mono_01")
        self.assertEqual(sess.step_count, 3)

    # 4. Control
    def test_22_capability_declaration(self) -> None:
        """Verify Codex declares exact verified capabilities."""
        self.assertTrue(self.adapter.supports_cancel())
        self.assertTrue(self.adapter.supports_terminate())
        self.assertFalse(self.adapter.supports_throttle())
        self.assertFalse(self.adapter.supports_next_step_switch())

    def test_23_cancel_control_success(self) -> None:
        """Verify graceful STOP cancel invokes transport.cancel_execution."""
        op = ControlOperation(
            operation_id="op_cancel_codex_1",
            execution_id="exec_codex_ctrl_01",
            action=GovernorAction.STOP,
            params={"graceful": True},
        )
        res = self.adapter.execute_control(op)

        self.assertEqual(res.status, ControlStatus.COMPLETED)
        self.assertIn("exec_codex_ctrl_01", self.transport.cancelled_executions)

    def test_24_terminate_control_success(self) -> None:
        """Verify hard STOP terminate invokes transport.terminate_session."""
        op = ControlOperation(
            operation_id="op_term_codex_1",
            execution_id="exec_codex_ctrl_02",
            action=GovernorAction.STOP,
            params={"hard": True},
        )
        res = self.adapter.execute_control(op)

        self.assertEqual(res.status, ControlStatus.COMPLETED)
        self.assertIn("exec_codex_ctrl_02", self.transport.terminated_sessions)

    def test_25_throttle_unsupported(self) -> None:
        """Verify THROTTLE control action returns UNSUPPORTED safely."""
        op = ControlOperation(
            operation_id="op_throt_codex_1",
            execution_id="exec_codex_ctrl_03",
            action=GovernorAction.THROTTLE,
            params={"delay_ms": 500},
        )
        res = self.adapter.execute_control(op)

        self.assertEqual(res.status, ControlStatus.UNSUPPORTED)
        self.assertFalse(res.metadata.get("is_supported"))

    def test_26_switch_unsupported(self) -> None:
        """Verify SWITCH control action returns UNSUPPORTED safely."""
        op = ControlOperation(
            operation_id="op_sw_codex_1",
            execution_id="exec_codex_ctrl_04",
            action=GovernorAction.SWITCH,
        )
        res = self.adapter.execute_control(op)

        self.assertEqual(res.status, ControlStatus.UNSUPPORTED)
        self.assertFalse(res.metadata.get("is_supported"))

    def test_27_unsupported_custom_action(self) -> None:
        """Verify unmapped action returns UNSUPPORTED."""
        op = ControlOperation(
            operation_id="op_esc_codex_1",
            execution_id="exec_codex_ctrl_05",
            action=GovernorAction.ESCALATE,
        )
        res = self.adapter.execute_control(op)
        self.assertEqual(res.status, ControlStatus.UNSUPPORTED)

    def test_28_continue_always_supported(self) -> None:
        """Verify CONTINUE action is always supported."""
        self.assertTrue(self.adapter.supports_action(GovernorAction.CONTINUE))

    def test_29_control_failure_handling(self) -> None:
        """Verify transport failure during control operation returns FAILED."""
        self.transport.cancel_execution = lambda exec_id: (_ for _ in ()).throw(RuntimeError("Process kill failed"))
        op = ControlOperation(
            operation_id="op_fail_codex_1",
            execution_id="exec_codex_ctrl_06",
            action=GovernorAction.STOP,
        )
        res = self.adapter.execute_control(op)
        self.assertEqual(res.status, ControlStatus.FAILED)

    def test_30_no_false_success_on_unsupported(self) -> None:
        """Verify unsupported operations never return COMPLETED or ACCEPTED."""
        op = ControlOperation(
            operation_id="op_fake_codex_1",
            execution_id="exec_codex_ctrl_07",
            action=GovernorAction.THROTTLE,
        )
        res = self.adapter.execute_control(op)
        self.assertNotEqual(res.status, ControlStatus.COMPLETED)
        self.assertNotEqual(res.status, ControlStatus.ACCEPTED)

    def test_31_control_history_in_session(self) -> None:
        """Verify session records received control operations."""
        self.adapter.attach_execution("exec_codex_hist_01")
        op = ControlOperation(
            operation_id="op_h_codex_1",
            execution_id="exec_codex_hist_01",
            action=GovernorAction.STOP,
        )
        self.adapter.execute_control(op)
        sess = self.adapter.get_session("exec_codex_hist_01")
        self.assertEqual(len(sess.control_history), 1)

    # 5. Block 22 Control Boundary Integration
    def test_32_register_with_control_boundary(self) -> None:
        """Verify Codex adapter registers with Block 22 ExecutionControlBoundary."""
        boundary = ExecutionControlBoundary()
        boundary.register_executor("exec_codex_bound_01", self.adapter)

        cap = boundary.get_capability("exec_codex_bound_01")
        self.assertIsNotNone(cap)
        self.assertTrue(cap.supports_cancel)
        self.assertTrue(cap.supports_terminate)
        self.assertFalse(cap.supports_throttle)

    def test_33_control_boundary_dispatches_stop(self) -> None:
        """Verify Control Boundary dispatching STOP succeeds against Codex adapter."""
        boundary = ExecutionControlBoundary()
        boundary.register_executor("exec_codex_bound_02", self.adapter)

        result = boundary.dispatch_control("exec_codex_bound_02", GovernorAction.STOP, params={"graceful": True})
        self.assertEqual(result.status, ControlStatus.COMPLETED)
        self.assertIn("exec_codex_bound_02", self.transport.cancelled_executions)

    def test_34_control_boundary_dispatches_throttle_returns_unsupported(self) -> None:
        """Verify Control Boundary dispatching THROTTLE returns UNSUPPORTED."""
        boundary = ExecutionControlBoundary()
        boundary.register_executor("exec_codex_bound_03", self.adapter)

        result = boundary.dispatch_control("exec_codex_bound_03", GovernorAction.THROTTLE)
        self.assertEqual(result.status, ControlStatus.UNSUPPORTED)

    def test_35_control_boundary_dispatches_switch_returns_unsupported(self) -> None:
        """Verify Control Boundary dispatching SWITCH returns UNSUPPORTED."""
        boundary = ExecutionControlBoundary()
        boundary.register_executor("exec_codex_bound_04", self.adapter)

        result = boundary.dispatch_control("exec_codex_bound_04", GovernorAction.SWITCH)
        self.assertEqual(result.status, ControlStatus.UNSUPPORTED)

    # 6. Events (Step, Tool, Web)
    def test_36_execution_completed_event_emitted(self) -> None:
        """Verify Step Execution emits ExecutionCompleted event on EventBus."""
        bus = InMemoryEventBus()
        adapter_with_bus = CodexAdapter(transport=self.transport, event_bus=bus)

        events: List[ExecutionEvent] = []
        bus.subscribe(lambda ev: events.append(ev))

        adapter_with_bus.execute_step(AgentStepRequest(execution_id="exec_codex_ev_01", step_index=0))

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].type, EventType.EXECUTION_COMPLETED)

    def test_37_event_envelope_fields(self) -> None:
        """Verify event envelope has required canonical fields."""
        bus = InMemoryEventBus()
        adapter_with_bus = CodexAdapter(transport=self.transport, event_bus=bus)

        events: List[ExecutionEvent] = []
        bus.subscribe(lambda ev: events.append(ev))

        adapter_with_bus.execute_step(AgentStepRequest(execution_id="exec_codex_ev_02", step_index=0))

        ev = events[0]
        self.assertTrue(ev.event_id.startswith("step_ev_codex_"))
        self.assertEqual(ev.sequence, 1)
        self.assertEqual(ev.source, EventSource.AGENT)

    def test_38_event_execution_id_matches(self) -> None:
        """Verify event envelope execution_id matches request execution_id."""
        bus = InMemoryEventBus()
        adapter_with_bus = CodexAdapter(transport=self.transport, event_bus=bus)

        events: List[ExecutionEvent] = []
        bus.subscribe(lambda ev: events.append(ev))

        adapter_with_bus.execute_step(AgentStepRequest(execution_id="exec_codex_ev_03", step_index=2))
        self.assertEqual(events[0].execution_id, "exec_codex_ev_03")

    def test_39_event_source_is_agent(self) -> None:
        """Verify event source is set to AGENT."""
        bus = InMemoryEventBus()
        adapter_with_bus = CodexAdapter(transport=self.transport, event_bus=bus)

        events: List[ExecutionEvent] = []
        bus.subscribe(lambda ev: events.append(ev))

        adapter_with_bus.execute_step(AgentStepRequest(execution_id="exec_codex_ev_04", step_index=0))
        self.assertEqual(events[0].source, EventSource.AGENT)

    def test_40_event_isolation_across_runs(self) -> None:
        """Verify events emitted for execution A and execution B do not intermix."""
        bus = InMemoryEventBus()
        adapter_with_bus = CodexAdapter(transport=self.transport, event_bus=bus)

        events: List[ExecutionEvent] = []
        bus.subscribe(lambda ev: events.append(ev))

        adapter_with_bus.execute_step(AgentStepRequest(execution_id="exec_codex_ev_A", step_index=0))
        adapter_with_bus.execute_step(AgentStepRequest(execution_id="exec_codex_ev_B", step_index=0))

        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].execution_id, "exec_codex_ev_A")
        self.assertEqual(events[1].execution_id, "exec_codex_ev_B")

    def test_41_tool_called_and_completed_events_emitted(self) -> None:
        """Verify observable tool activities in payload are emitted as TOOL_CALLED and TOOL_COMPLETED events."""
        bus = InMemoryEventBus()
        adapter_with_bus = CodexAdapter(transport=self.transport, event_bus=bus)

        self.transport.custom_output = CodexExecutionOutput(
            stdout=json.dumps({
                "result": "File edited",
                "tools": [
                    {"name": "file_patcher", "args": {"file": "schema.py"}, "duration_ms": 50.0, "status": "success"},
                ],
            }),
            parsed_json={
                "result": "File edited",
                "tools": [
                    {"name": "file_patcher", "args": {"file": "schema.py"}, "duration_ms": 50.0, "status": "success"},
                ],
            },
        )

        events: List[ExecutionEvent] = []
        bus.subscribe(lambda ev: events.append(ev))

        adapter_with_bus.execute_step(AgentStepRequest(execution_id="exec_codex_tool_01", step_index=0))

        types = [e.type for e in events]
        self.assertIn(EventType.EXECUTION_COMPLETED, types)
        self.assertIn(EventType.TOOL_CALLED, types)
        self.assertIn(EventType.TOOL_COMPLETED, types)

    def test_42_web_request_and_response_events_emitted(self) -> None:
        """Verify observable web activities in payload are emitted as WEB_REQUEST and WEB_RESPONSE events."""
        bus = InMemoryEventBus()
        adapter_with_bus = CodexAdapter(transport=self.transport, event_bus=bus)

        self.transport.custom_output = CodexExecutionOutput(
            stdout=json.dumps({
                "result": "Searched documentation",
                "web_requests": [
                    {"url": "https://docs.openai.com/codex", "method": "GET", "status_code": 200, "duration_ms": 130.0},
                ],
            }),
            parsed_json={
                "result": "Searched documentation",
                "web_requests": [
                    {"url": "https://docs.openai.com/codex", "method": "GET", "status_code": 200, "duration_ms": 130.0},
                ],
            },
        )

        events: List[ExecutionEvent] = []
        bus.subscribe(lambda ev: events.append(ev))

        adapter_with_bus.execute_step(AgentStepRequest(execution_id="exec_codex_web_01", step_index=0))

        types = [e.type for e in events]
        self.assertIn(EventType.EXECUTION_COMPLETED, types)
        self.assertIn(EventType.WEB_REQUEST, types)
        self.assertIn(EventType.WEB_RESPONSE, types)

    def test_43_event_bus_subscriber_failure_safety(self) -> None:
        """Verify step execution succeeds even if an event subscriber fails."""
        bus = InMemoryEventBus()
        adapter_with_bus = CodexAdapter(transport=self.transport, event_bus=bus)

        def faulty_sub(ev: ExecutionEvent) -> None:
            raise RuntimeError("Event subscriber error")

        bus.subscribe(faulty_sub)

        resp = adapter_with_bus.execute_step(AgentStepRequest(execution_id="exec_codex_ev_safe", step_index=0))
        self.assertEqual(resp.execution_id, "exec_codex_ev_safe")

    # 7. Security & Redaction
    def test_44_no_shell_true_used(self) -> None:
        """Verify SubprocessTransport never invokes shell=True."""
        transport = CodexSubprocessTransport()
        src = inspect.getsource(CodexSubprocessTransport.execute)
        self.assertIn("shell=False", src)
        self.assertNotIn("shell=True", src)

    def test_45_secret_redaction_in_errors(self) -> None:
        """Verify sensitive API keys are redacted in normalized error records."""
        raw_error = "Codex token invalid: codex-secret-token-abcdef12345678"
        norm = self.adapter.normalize_error(raw_error)
        self.assertNotIn("codex-secret-token-abcdef12345678", norm.message)
        self.assertIn("[REDACTED]", norm.message)

    def test_46_secret_redaction_utility(self) -> None:
        """Verify redact_codex_secrets removes tokens, bearer keys, and api-keys."""
        text = "Authorization: Bearer my_codex_token_secret password: supersecretpass"
        redacted = redact_codex_secrets(text)
        self.assertNotIn("my_codex_token_secret", redacted)
        self.assertNotIn("supersecretpass", redacted)

    def test_47_argument_injection_safety(self) -> None:
        """Verify semicolons, pipes, and backticks in prompt are passed as literal arguments."""
        injection_prompt = "codex_task; rm -rf / | echo `whoami`"
        req = AgentStepRequest(execution_id="exec_codex_sec_01", step_index=0, prompt=injection_prompt)
        self.adapter.execute_step(req)

        self.assertEqual(len(self.transport.invocations), 1)
        args = self.transport.invocations[0]["args"]
        self.assertIn(injection_prompt, args)

    def test_48_empty_execution_id_rejected(self) -> None:
        """Verify empty or whitespace execution_id is rejected with ValueError."""
        with self.assertRaises(ValueError):
            self.adapter.attach_execution("   ")

        with self.assertRaises(ValueError):
            self.adapter.execute_step(AgentStepRequest(execution_id="", step_index=0))

    def test_49_cross_session_isolation(self) -> None:
        """Verify control operations on session A do not touch session B."""
        self.adapter.attach_execution("sess_codex_A")
        self.adapter.attach_execution("sess_codex_B")

        self.adapter.execute_control(ControlOperation(
            operation_id="op_codex_iso_1",
            execution_id="sess_codex_A",
            action=GovernorAction.STOP,
        ))

        sess_a = self.adapter.get_session("sess_codex_A")
        sess_b = self.adapter.get_session("sess_codex_B")

        self.assertEqual(len(sess_a.control_history), 1)
        self.assertEqual(len(sess_b.control_history), 0)

    # 8. Architecture Boundaries
    def test_50_no_policy_evaluation_in_codex_adapter(self) -> None:
        """Verify codex adapter contains zero policy evaluation logic."""
        import infuse.agents.codex
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.agents.codex")]
        for mod in modules:
            src = inspect.getsource(mod)
            self.assertNotIn("GovernancePolicy", src)
            self.assertNotIn("evaluate_policy", src)

    def test_51_no_governor_decisions_in_codex_adapter(self) -> None:
        """Verify codex adapter contains zero Governor decisions logic."""
        import infuse.agents.codex
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.agents.codex")]
        for mod in modules:
            src = inspect.getsource(mod)
            self.assertNotIn("derive_state", src)
            self.assertNotIn("select_action", src)

    def test_52_no_provider_routing_in_codex_adapter(self) -> None:
        """Verify codex adapter contains zero provider or model routing logic."""
        import infuse.agents.codex
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.agents.codex")]
        for mod in modules:
            src = inspect.getsource(mod)
            self.assertNotIn("route_request", src)
            self.assertNotIn("select_provider", src)

    def test_53_no_provider_pricing_in_codex_adapter(self) -> None:
        """Verify codex adapter contains zero pricing calculation logic."""
        import infuse.agents.codex
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.agents.codex")]
        for mod in modules:
            src = inspect.getsource(mod)
            self.assertNotIn("calculate_cost", src)
            self.assertNotIn("EconomicsEngine", src)

    def test_54_no_direct_observer_invocations(self) -> None:
        """Verify codex adapter does not invoke observers directly."""
        import infuse.agents.codex
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.agents.codex")]
        for mod in modules:
            src = inspect.getsource(mod)
            self.assertNotIn("TokenObserver", src)
            self.assertNotIn("ToolActivityObserver", src)
            self.assertNotIn("WebActivityObserver", src)
            self.assertNotIn("HealthEngine", src)

    def test_55_no_concrete_agent_cross_dependencies(self) -> None:
        """Verify codex adapter does not depend on claude or opencode concrete agent adapters."""
        import infuse.agents.codex
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.agents.codex")]
        for mod in modules:
            src = inspect.getsource(mod)
            self.assertNotIn("ClaudeCodeAdapter", src)
            self.assertNotIn("OpenCodeAdapter", src)

    def test_56_zero_database_or_network_socket_imports(self) -> None:
        """Verify codex adapter contains zero database or network socket imports."""
        import infuse.agents.codex
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.agents.codex")]
        forbidden = ["sqlite3", "psycopg2", "sqlalchemy", "redis", "requests", "urllib", "httpx", "aiohttp", "socket"]
        for mod in modules:
            src = inspect.getsource(mod)
            for f in forbidden:
                self.assertNotIn(f"import {f}", src)
                self.assertNotIn(f"from {f}", src)

    # 9. Concurrency & Thread Safety & Live Discovery
    def test_57_thread_safe_concurrent_steps(self) -> None:
        """Verify thread-safe concurrent step executions across multiple threads."""
        threads = []
        for i in range(16):
            req = AgentStepRequest(execution_id=f"th_codex_step_{i}", step_index=0)
            t = threading.Thread(target=self.adapter.execute_step, args=(req,))
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        for i in range(16):
            sess = self.adapter.get_session(f"th_codex_step_{i}")
            self.assertIsNotNone(sess)
            self.assertEqual(sess.step_count, 1)

    def test_58_thread_safe_concurrent_controls(self) -> None:
        """Verify thread-safe concurrent control operations across multiple threads."""
        threads = []
        for i in range(16):
            op = ControlOperation(
                operation_id=f"th_codex_op_{i}",
                execution_id=f"th_codex_ctrl_{i}",
                action=GovernorAction.STOP,
            )
            t = threading.Thread(target=self.adapter.execute_control, args=(op,))
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(self.adapter.received_controls), 16)

    def test_59_live_cli_discovery(self) -> None:
        """Verify CodexSubprocessTransport correctly handles CLI discovery."""
        sub_transport = CodexSubprocessTransport()
        avail = sub_transport.is_available()
        self.assertTrue(avail)


if __name__ == "__main__":
    unittest.main()
