"""Comprehensive Unit, Integration, and Boundary Test Suite for Block 24 Claude Code Adapter."""

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
from infuse.agents.claude.adapter import ClaudeCodeAdapter
from infuse.agents.claude.errors import (
    ClaudeAdapterError,
    ClaudeCLINotFoundError,
    ClaudeProcessError,
    ClaudeTimeoutError,
)
from infuse.agents.claude.models import (
    ClaudeAdapterConfig,
    ClaudeExecutionOutput,
    redact_secrets,
)
from infuse.agents.claude.transport import (
    ClaudeReferenceTransport,
    ClaudeSubprocessTransport,
)
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


class TestClaudeCodeAdapter(unittest.TestCase):
    """Test suite verifying Claude Code adapter contracts, transport, controls, security, and isolation."""

    def setUp(self) -> None:
        self.transport = ClaudeReferenceTransport()
        self.adapter = ClaudeCodeAdapter(transport=self.transport)

    # 1. Identity
    def test_01_claude_identity(self) -> None:
        """Verify Claude Code adapter identity matches universal specification."""
        ident = self.adapter.identity
        self.assertEqual(ident.agent_name, "claudecode")
        self.assertEqual(ident.version, "1.0.0")
        self.assertEqual(ident.runtime_type, "cli")

    def test_02_identity_serialization(self) -> None:
        """Verify AgentIdentity serialization and deserialization."""
        ident = self.adapter.identity
        data = ident.model_dump()
        self.assertEqual(data["agent_name"], "claudecode")
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
        req = AgentStepRequest(execution_id="claude_exec_preserve_01", step_index=0, prompt="Fix bug")
        resp = self.adapter.execute_step(req)

        self.assertEqual(resp.execution_id, "claude_exec_preserve_01")
        session = self.adapter.get_session("claude_exec_preserve_01")
        self.assertIsNotNone(session)
        self.assertEqual(session.execution_id, "claude_exec_preserve_01")

    # 2. Universal Contract
    def test_05_interface_compliance(self) -> None:
        """Verify ClaudeCodeAdapter cleanly implements IUniversalAgentAdapter."""
        self.assertIsInstance(self.adapter, IUniversalAgentAdapter)
        self.assertEqual(self.adapter.executor_id, self.adapter.identity.agent_id)

    def test_06_step_request_normalization(self) -> None:
        """Verify AgentStepRequest is properly parsed and passed to transport arguments."""
        req = AgentStepRequest(
            execution_id="claude_exec_02",
            step_index=1,
            prompt="Refactor authentication layer",
            parameters={"model": "claude-3-7-sonnet"},
        )
        self.adapter.execute_step(req)

        self.assertEqual(len(self.transport.invocations), 1)
        inv = self.transport.invocations[0]
        self.assertEqual(inv["execution_id"], "claude_exec_02")
        self.assertIn("-p", inv["args"])
        self.assertIn("Refactor authentication layer", inv["args"])
        self.assertIn("--output-format", inv["args"])

    def test_07_step_response_structure(self) -> None:
        """Verify AgentStepResponse contains required contract fields."""
        req = AgentStepRequest(execution_id="claude_exec_03", step_index=0, prompt="Test prompt")
        resp = self.adapter.execute_step(req)

        self.assertEqual(resp.execution_id, "claude_exec_03")
        self.assertEqual(resp.step_index, 0)
        self.assertIsNotNone(resp.content)
        self.assertEqual(resp.finish_reason, "stop")
        self.assertIn("agent_id", resp.metadata)
        self.assertIn("duration_ms", resp.metadata)

    def test_08_session_creation(self) -> None:
        """Verify explicit session attachment returns an active AgentExecutionSession."""
        session = self.adapter.attach_execution("claude_sess_01", metadata={"branch": "feature/x"})
        self.assertTrue(session.is_active)
        self.assertEqual(session.execution_id, "claude_sess_01")
        self.assertEqual(session.metadata.get("branch"), "feature/x")

    def test_09_session_lookup(self) -> None:
        """Verify get_session returns the active session or None."""
        self.adapter.attach_execution("claude_sess_02")
        sess = self.adapter.get_session("claude_sess_02")
        self.assertIsNotNone(sess)
        self.assertTrue(sess.is_active)

        none_sess = self.adapter.get_session("non_existent_sess")
        self.assertIsNone(none_sess)

    def test_10_session_isolation(self) -> None:
        """Verify Execution A and Execution B sessions do not share state."""
        self.adapter.attach_execution("exec_A")
        self.adapter.attach_execution("exec_B")

        self.adapter.execute_step(AgentStepRequest(execution_id="exec_A", step_index=0))
        self.adapter.execute_step(AgentStepRequest(execution_id="exec_A", step_index=1))
        self.adapter.execute_step(AgentStepRequest(execution_id="exec_B", step_index=0))

        sess_a = self.adapter.get_session("exec_A")
        sess_b = self.adapter.get_session("exec_B")

        self.assertEqual(sess_a.step_count, 2)
        self.assertEqual(sess_b.step_count, 1)

    # 3. Execution
    def test_11_successful_execution(self) -> None:
        """Verify reference transport execution produces a valid response."""
        req = AgentStepRequest(execution_id="exec_succ_01", step_index=0, prompt="Hello Claude")
        resp = self.adapter.execute_step(req)
        self.assertIn("Claude Code response", resp.content)

    def test_12_empty_response_handling(self) -> None:
        """Verify empty transport stdout does not cause an uncaught crash."""
        self.transport.custom_output = ClaudeExecutionOutput(
            stdout="",
            stderr="",
            return_code=0,
            duration_ms=5.0,
        )
        req = AgentStepRequest(execution_id="exec_empty_01", step_index=0)
        resp = self.adapter.execute_step(req)
        self.assertEqual(resp.content, "")

    def test_13_structured_response_parsing(self) -> None:
        """Verify JSON output from Claude is parsed into raw_output and content."""
        self.transport.custom_output = ClaudeExecutionOutput(
            stdout=json.dumps({"result": "Structured solution", "cost_usd": 0.01}),
            stderr="",
            return_code=0,
            parsed_json={"result": "Structured solution", "cost_usd": 0.01},
            duration_ms=10.0,
        )
        req = AgentStepRequest(execution_id="exec_struct_01", step_index=0)
        resp = self.adapter.execute_step(req)
        self.assertEqual(resp.content, "Structured solution")
        self.assertEqual(resp.raw_output.get("cost_usd"), 0.01)

    def test_14_malformed_response_fallback(self) -> None:
        """Verify non-JSON stdout falls back safely to plain string content."""
        self.transport.custom_output = ClaudeExecutionOutput(
            stdout="Raw plain text response from CLI",
            stderr="",
            return_code=0,
            parsed_json=None,
            duration_ms=8.0,
        )
        req = AgentStepRequest(execution_id="exec_raw_01", step_index=0)
        resp = self.adapter.execute_step(req)
        self.assertEqual(resp.content, "Raw plain text response from CLI")

    def test_15_process_failure_handling(self) -> None:
        """Verify transport non-zero process failure raises AgentExecutionError."""
        self.transport.should_fail = True
        req = AgentStepRequest(execution_id="exec_fail_01", step_index=0)
        with self.assertRaises(AgentExecutionError):
            self.adapter.execute_step(req)

    def test_16_startup_failure_not_found(self) -> None:
        """Verify executable not found error maps to AgentExecutionError."""
        self.transport.should_raise_not_found = True
        req = AgentStepRequest(execution_id="exec_not_found_01", step_index=0)
        with self.assertRaises(AgentExecutionError):
            self.adapter.execute_step(req)

    def test_17_runtime_timeout(self) -> None:
        """Verify CLI process timeout maps to AgentExecutionError."""
        self.transport.should_timeout = True
        req = AgentStepRequest(execution_id="exec_timeout_01", step_index=0)
        with self.assertRaises(AgentExecutionError):
            self.adapter.execute_step(req)

    def test_18_duration_ms_telemetry(self) -> None:
        """Verify execution duration is captured in response metadata."""
        self.transport.custom_output = ClaudeExecutionOutput(
            stdout="OK",
            return_code=0,
            duration_ms=42.5,
        )
        req = AgentStepRequest(execution_id="exec_dur_01", step_index=0)
        resp = self.adapter.execute_step(req)
        self.assertEqual(resp.metadata.get("duration_ms"), 42.5)

    def test_19_auto_attach_on_step(self) -> None:
        """Verify step execution auto-attaches a session if unattached."""
        req = AgentStepRequest(execution_id="exec_auto_01", step_index=0)
        self.adapter.execute_step(req)
        sess = self.adapter.get_session("exec_auto_01")
        self.assertIsNotNone(sess)
        self.assertTrue(sess.is_active)

    def test_20_step_counter_monotonic(self) -> None:
        """Verify step counter monotonically increases across steps."""
        self.adapter.attach_execution("exec_mono_01")
        for i in range(3):
            self.adapter.execute_step(AgentStepRequest(execution_id="exec_mono_01", step_index=i))
        sess = self.adapter.get_session("exec_mono_01")
        self.assertEqual(sess.step_count, 3)

    # 4. Control
    def test_21_capability_declaration(self) -> None:
        """Verify Claude Code declares exact verified capabilities."""
        self.assertTrue(self.adapter.supports_cancel())
        self.assertTrue(self.adapter.supports_terminate())
        self.assertFalse(self.adapter.supports_throttle())
        self.assertFalse(self.adapter.supports_next_step_switch())

    def test_22_cancel_control_success(self) -> None:
        """Verify graceful STOP cancel invokes transport.cancel_execution."""
        op = ControlOperation(
            operation_id="op_cancel_1",
            execution_id="exec_ctrl_01",
            action=GovernorAction.STOP,
            params={"graceful": True},
        )
        res = self.adapter.execute_control(op)

        self.assertEqual(res.status, ControlStatus.COMPLETED)
        self.assertIn("exec_ctrl_01", self.transport.cancelled_executions)

    def test_23_terminate_control_success(self) -> None:
        """Verify hard STOP terminate invokes transport.terminate_session."""
        op = ControlOperation(
            operation_id="op_term_1",
            execution_id="exec_ctrl_02",
            action=GovernorAction.STOP,
            params={"hard": True},
        )
        res = self.adapter.execute_control(op)

        self.assertEqual(res.status, ControlStatus.COMPLETED)
        self.assertIn("exec_ctrl_02", self.transport.terminated_sessions)

    def test_24_throttle_unsupported(self) -> None:
        """Verify THROTTLE control action returns UNSUPPORTED safely."""
        op = ControlOperation(
            operation_id="op_throt_1",
            execution_id="exec_ctrl_03",
            action=GovernorAction.THROTTLE,
            params={"delay_ms": 1000},
        )
        res = self.adapter.execute_control(op)

        self.assertEqual(res.status, ControlStatus.UNSUPPORTED)
        self.assertFalse(res.metadata.get("is_supported"))

    def test_25_switch_unsupported(self) -> None:
        """Verify SWITCH control action returns UNSUPPORTED safely."""
        op = ControlOperation(
            operation_id="op_sw_1",
            execution_id="exec_ctrl_04",
            action=GovernorAction.SWITCH,
        )
        res = self.adapter.execute_control(op)

        self.assertEqual(res.status, ControlStatus.UNSUPPORTED)
        self.assertFalse(res.metadata.get("is_supported"))

    def test_26_unsupported_custom_action(self) -> None:
        """Verify unmapped action returns UNSUPPORTED."""
        op = ControlOperation(
            operation_id="op_esc_1",
            execution_id="exec_ctrl_05",
            action=GovernorAction.ESCALATE,
        )
        res = self.adapter.execute_control(op)
        self.assertEqual(res.status, ControlStatus.UNSUPPORTED)

    def test_27_continue_always_supported(self) -> None:
        """Verify CONTINUE action is always supported."""
        self.assertTrue(self.adapter.supports_action(GovernorAction.CONTINUE))

    def test_28_control_failure_handling(self) -> None:
        """Verify transport failure during control operation returns FAILED."""
        # Inject an exception on cancel
        self.transport.cancel_execution = lambda exec_id: (_ for _ in ()).throw(RuntimeError("Process kill failed"))
        op = ControlOperation(
            operation_id="op_fail_1",
            execution_id="exec_ctrl_06",
            action=GovernorAction.STOP,
        )
        res = self.adapter.execute_control(op)
        self.assertEqual(res.status, ControlStatus.FAILED)

    def test_29_no_false_success_on_unsupported(self) -> None:
        """Verify unsupported operations never return COMPLETED or ACCEPTED."""
        op = ControlOperation(
            operation_id="op_fake_1",
            execution_id="exec_ctrl_07",
            action=GovernorAction.THROTTLE,
        )
        res = self.adapter.execute_control(op)
        self.assertNotEqual(res.status, ControlStatus.COMPLETED)
        self.assertNotEqual(res.status, ControlStatus.ACCEPTED)

    def test_30_control_history_in_session(self) -> None:
        """Verify session records received control operations."""
        self.adapter.attach_execution("exec_hist_01")
        op = ControlOperation(
            operation_id="op_h_1",
            execution_id="exec_hist_01",
            action=GovernorAction.STOP,
        )
        self.adapter.execute_control(op)
        sess = self.adapter.get_session("exec_hist_01")
        self.assertEqual(len(sess.control_history), 1)

    # 5. Block 22 Control Boundary Integration
    def test_31_register_with_control_boundary(self) -> None:
        """Verify Claude Code adapter registers with Block 22 ExecutionControlBoundary."""
        boundary = ExecutionControlBoundary()
        boundary.register_executor("exec_bound_01", self.adapter)

        cap = boundary.get_capability("exec_bound_01")
        self.assertIsNotNone(cap)
        self.assertTrue(cap.supports_cancel)
        self.assertTrue(cap.supports_terminate)
        self.assertFalse(cap.supports_throttle)

    def test_32_control_boundary_dispatches_stop(self) -> None:
        """Verify Control Boundary dispatching STOP succeeds against Claude adapter."""
        boundary = ExecutionControlBoundary()
        boundary.register_executor("exec_bound_02", self.adapter)

        result = boundary.dispatch_control("exec_bound_02", GovernorAction.STOP, params={"graceful": True})
        self.assertEqual(result.status, ControlStatus.COMPLETED)
        self.assertIn("exec_bound_02", self.transport.cancelled_executions)

    def test_33_control_boundary_dispatches_throttle_returns_unsupported(self) -> None:
        """Verify Control Boundary dispatching THROTTLE returns UNSUPPORTED."""
        boundary = ExecutionControlBoundary()
        boundary.register_executor("exec_bound_03", self.adapter)

        result = boundary.dispatch_control("exec_bound_03", GovernorAction.THROTTLE)
        self.assertEqual(result.status, ControlStatus.UNSUPPORTED)

    def test_34_control_boundary_dispatches_switch_returns_unsupported(self) -> None:
        """Verify Control Boundary dispatching SWITCH returns UNSUPPORTED."""
        boundary = ExecutionControlBoundary()
        boundary.register_executor("exec_bound_04", self.adapter)

        result = boundary.dispatch_control("exec_bound_04", GovernorAction.SWITCH)
        self.assertEqual(result.status, ControlStatus.UNSUPPORTED)

    # 6. Events
    def test_35_execution_completed_event_emitted(self) -> None:
        """Verify Step Execution emits ExecutionCompleted event on EventBus."""
        bus = InMemoryEventBus()
        adapter_with_bus = ClaudeCodeAdapter(transport=self.transport, event_bus=bus)

        events: List[ExecutionEvent] = []
        bus.subscribe(lambda ev: events.append(ev))

        adapter_with_bus.execute_step(AgentStepRequest(execution_id="exec_ev_01", step_index=0))

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].type, EventType.EXECUTION_COMPLETED)

    def test_36_event_envelope_fields(self) -> None:
        """Verify event envelope has required canonical fields."""
        bus = InMemoryEventBus()
        adapter_with_bus = ClaudeCodeAdapter(transport=self.transport, event_bus=bus)

        events: List[ExecutionEvent] = []
        bus.subscribe(lambda ev: events.append(ev))

        adapter_with_bus.execute_step(AgentStepRequest(execution_id="exec_ev_02", step_index=0))

        ev = events[0]
        self.assertTrue(ev.event_id.startswith("step_ev_claude_"))
        self.assertEqual(ev.sequence, 1)
        self.assertEqual(ev.source, EventSource.AGENT)

    def test_37_event_execution_id_matches(self) -> None:
        """Verify event envelope execution_id matches request execution_id."""
        bus = InMemoryEventBus()
        adapter_with_bus = ClaudeCodeAdapter(transport=self.transport, event_bus=bus)

        events: List[ExecutionEvent] = []
        bus.subscribe(lambda ev: events.append(ev))

        adapter_with_bus.execute_step(AgentStepRequest(execution_id="exec_ev_03", step_index=2))
        self.assertEqual(events[0].execution_id, "exec_ev_03")

    def test_38_event_source_is_agent(self) -> None:
        """Verify event source is set to AGENT."""
        bus = InMemoryEventBus()
        adapter_with_bus = ClaudeCodeAdapter(transport=self.transport, event_bus=bus)

        events: List[ExecutionEvent] = []
        bus.subscribe(lambda ev: events.append(ev))

        adapter_with_bus.execute_step(AgentStepRequest(execution_id="exec_ev_04", step_index=0))
        self.assertEqual(events[0].source, EventSource.AGENT)

    def test_39_event_isolation_across_runs(self) -> None:
        """Verify events emitted for execution A and execution B do not intermix."""
        bus = InMemoryEventBus()
        adapter_with_bus = ClaudeCodeAdapter(transport=self.transport, event_bus=bus)

        events: List[ExecutionEvent] = []
        bus.subscribe(lambda ev: events.append(ev))

        adapter_with_bus.execute_step(AgentStepRequest(execution_id="exec_ev_A", step_index=0))
        adapter_with_bus.execute_step(AgentStepRequest(execution_id="exec_ev_B", step_index=0))

        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].execution_id, "exec_ev_A")
        self.assertEqual(events[1].execution_id, "exec_ev_B")

    def test_40_event_bus_subscriber_failure_safety(self) -> None:
        """Verify step execution succeeds even if an event subscriber fails."""
        bus = InMemoryEventBus()
        adapter_with_bus = ClaudeCodeAdapter(transport=self.transport, event_bus=bus)

        def faulty_sub(ev: ExecutionEvent) -> None:
            raise RuntimeError("Event subscriber error")

        bus.subscribe(faulty_sub)

        resp = adapter_with_bus.execute_step(AgentStepRequest(execution_id="exec_ev_safe", step_index=0))
        self.assertEqual(resp.execution_id, "exec_ev_safe")

    # 7. Security & Redaction
    def test_41_no_shell_true_used(self) -> None:
        """Verify SubprocessTransport never invokes shell=True."""
        transport = ClaudeSubprocessTransport()
        src = inspect.getsource(ClaudeSubprocessTransport.execute)
        self.assertIn("shell=False", src)
        self.assertNotIn("shell=True", src)

    def test_42_secret_redaction_in_errors(self) -> None:
        """Verify sensitive API keys are redacted in normalized error records."""
        raw_error = "Authentication failed with key: sk-ant-api03-abcdef123456789012345678"
        norm = self.adapter.normalize_error(raw_error)
        self.assertNotIn("sk-ant-api03-abcdef123456789012345678", norm.message)
        self.assertIn("[REDACTED]", norm.message)

    def test_43_secret_redaction_utility(self) -> None:
        """Verify redact_secrets removes tokens, bearer keys, and api-keys."""
        text = "Authorization: Bearer token_secret_1234567890 password=supersecretpass"
        redacted = redact_secrets(text)
        self.assertNotIn("token_secret_1234567890", redacted)
        self.assertNotIn("supersecretpass", redacted)

    def test_44_argument_injection_safety(self) -> None:
        """Verify semicolons, pipes, and backticks in prompt are passed as literal arguments."""
        injection_prompt = "test; rm -rf / | echo `whoami`"
        req = AgentStepRequest(execution_id="exec_sec_01", step_index=0, prompt=injection_prompt)
        self.adapter.execute_step(req)

        self.assertEqual(len(self.transport.invocations), 1)
        args = self.transport.invocations[0]["args"]
        # Prompt must be a direct element in the args array
        self.assertIn(injection_prompt, args)

    def test_45_empty_execution_id_rejected(self) -> None:
        """Verify empty or whitespace execution_id is rejected with ValueError."""
        with self.assertRaises(ValueError):
            self.adapter.attach_execution("   ")

        with self.assertRaises(ValueError):
            self.adapter.execute_step(AgentStepRequest(execution_id="", step_index=0))

    def test_46_cross_session_isolation(self) -> None:
        """Verify control operations on session A do not touch session B."""
        self.adapter.attach_execution("sess_A")
        self.adapter.attach_execution("sess_B")

        self.adapter.execute_control(ControlOperation(
            operation_id="op_iso_1",
            execution_id="sess_A",
            action=GovernorAction.STOP,
        ))

        sess_a = self.adapter.get_session("sess_A")
        sess_b = self.adapter.get_session("sess_B")

        self.assertEqual(len(sess_a.control_history), 1)
        self.assertEqual(len(sess_b.control_history), 0)

    # 8. Architecture Boundaries
    def test_47_no_policy_evaluation_in_claude_adapter(self) -> None:
        """Verify claude adapter contains zero policy evaluation logic."""
        import infuse.agents.claude
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.agents.claude")]
        for mod in modules:
            src = inspect.getsource(mod)
            self.assertNotIn("GovernancePolicy", src)
            self.assertNotIn("evaluate_policy", src)

    def test_48_no_governor_decisions_in_claude_adapter(self) -> None:
        """Verify claude adapter contains zero Governor decisions logic."""
        import infuse.agents.claude
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.agents.claude")]
        for mod in modules:
            src = inspect.getsource(mod)
            self.assertNotIn("derive_state", src)
            self.assertNotIn("select_action", src)

    def test_49_no_provider_routing_in_claude_adapter(self) -> None:
        """Verify claude adapter contains zero provider or model routing logic."""
        import infuse.agents.claude
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.agents.claude")]
        for mod in modules:
            src = inspect.getsource(mod)
            self.assertNotIn("route_request", src)
            self.assertNotIn("select_provider", src)

    def test_50_no_provider_pricing_in_claude_adapter(self) -> None:
        """Verify claude adapter contains zero pricing calculation logic."""
        import infuse.agents.claude
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.agents.claude")]
        for mod in modules:
            src = inspect.getsource(mod)
            self.assertNotIn("calculate_cost", src)
            self.assertNotIn("EconomicsEngine", src)

    def test_51_no_direct_observer_invocations(self) -> None:
        """Verify claude adapter does not invoke observers directly."""
        import infuse.agents.claude
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.agents.claude")]
        for mod in modules:
            src = inspect.getsource(mod)
            self.assertNotIn("TokenObserver", src)
            self.assertNotIn("ToolActivityObserver", src)
            self.assertNotIn("WebActivityObserver", src)
            self.assertNotIn("HealthEngine", src)

    def test_52_no_parallel_concrete_agent_dependencies(self) -> None:
        """Verify claude adapter does not depend on other concrete agent adapters."""
        import infuse.agents.claude
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.agents.claude")]
        for mod in modules:
            src = inspect.getsource(mod)
            self.assertNotIn("opencode", src)
            self.assertNotIn("codex", src)
            self.assertNotIn("hermes", src)
            self.assertNotIn("openclaw", src)
            self.assertNotIn("lovable", src)

    def test_53_zero_database_or_network_socket_imports(self) -> None:
        """Verify claude adapter contains zero database or network socket imports."""
        import infuse.agents.claude
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.agents.claude")]
        forbidden = ["sqlite3", "psycopg2", "sqlalchemy", "redis", "requests", "urllib", "httpx", "aiohttp", "socket"]
        for mod in modules:
            src = inspect.getsource(mod)
            for f in forbidden:
                self.assertNotIn(f"import {f}", src)
                self.assertNotIn(f"from {f}", src)

    # 9. Concurrency & Thread Safety
    def test_54_thread_safe_concurrent_steps(self) -> None:
        """Verify thread-safe concurrent step executions across multiple threads."""
        threads = []
        for i in range(16):
            req = AgentStepRequest(execution_id=f"th_claude_step_{i}", step_index=0)
            t = threading.Thread(target=self.adapter.execute_step, args=(req,))
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        for i in range(16):
            sess = self.adapter.get_session(f"th_claude_step_{i}")
            self.assertIsNotNone(sess)
            self.assertEqual(sess.step_count, 1)

    def test_55_thread_safe_concurrent_controls(self) -> None:
        """Verify thread-safe concurrent control operations across multiple threads."""
        threads = []
        for i in range(16):
            op = ControlOperation(
                operation_id=f"th_claude_op_{i}",
                execution_id=f"th_claude_ctrl_{i}",
                action=GovernorAction.STOP,
            )
            t = threading.Thread(target=self.adapter.execute_control, args=(op,))
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(self.adapter.received_controls), 16)

    # 10. Live Integration Verification
    def test_56_live_cli_discovery(self) -> None:
        """Verify ClaudeSubprocessTransport correctly detects local CLI availability."""
        sub_transport = ClaudeSubprocessTransport()
        # Verify is_available returns a boolean without throwing
        avail = sub_transport.is_available()
        self.assertIsInstance(avail, bool)


if __name__ == "__main__":
    unittest.main()
