"""Comprehensive Unit, Integration, and Boundary Test Suite for Block 23 Universal Agent Adapter."""

import inspect
import sys
import threading
import unittest
from typing import Any, Dict, List, Optional

from infuse.contracts.capabilities import (
    AdapterRegistration,
    AdapterType,
    AgentCapability,
)
from infuse.contracts.control import (
    ControlCapability,
    ControlOperation,
    ControlResult,
    ControlStatus,
)
from infuse.contracts.events import EventType, ExecutionEvent
from infuse.contracts.governor import GovernorAction
from infuse.control.boundary import ExecutionControlBoundary
from infuse.events.bus import InMemoryEventBus
from infuse.agents.errors import (
    AgentAdapterError,
    AgentControlError,
    AgentExecutionError,
    AgentUnavailableError,
    UnsupportedAgentOperationError,
)
from infuse.agents.interfaces import IUniversalAgentAdapter
from infuse.agents.models import (
    AgentErrorRecord,
    AgentExecutionSession,
    AgentIdentity,
    AgentStepRequest,
    AgentStepResponse,
)
from infuse.agents.reference import ReferenceUniversalAgentAdapter


class TestUniversalAgentAdapter(unittest.TestCase):
    """Test suite verifying Universal Agent Adapter contracts, capabilities, controls, and isolation."""

    def setUp(self) -> None:
        self.adapter = ReferenceUniversalAgentAdapter()

    # 1. Contract tests
    def test_01_interface_compliance(self) -> None:
        """Verify ReferenceUniversalAgentAdapter implements IUniversalAgentAdapter."""
        self.assertIsInstance(self.adapter, IUniversalAgentAdapter)
        self.assertEqual(self.adapter.identity.agent_name, "reference")
        self.assertEqual(self.adapter.identity.version, "1.0.0")

    def test_02_identity_validation(self) -> None:
        """Verify AgentIdentity fields and defaults."""
        ident = AgentIdentity(
            agent_id="agt_custom",
            agent_name="custom_agent",
            version="2.0.0",
            runtime_type="universal",
            metadata={"sandbox": True},
        )
        self.assertEqual(ident.agent_id, "agt_custom")
        self.assertEqual(ident.agent_name, "custom_agent")
        self.assertTrue(ident.metadata.get("sandbox"))

    def test_03_execution_identity_preservation(self) -> None:
        """Verify canonical execution ID is strictly preserved across requests and responses."""
        req = AgentStepRequest(execution_id="canonical_exec_01", step_index=0, prompt="Hello")
        resp = self.adapter.execute_step(req)

        self.assertEqual(resp.execution_id, "canonical_exec_01")
        session = self.adapter.get_session("canonical_exec_01")
        self.assertIsNotNone(session)
        self.assertEqual(session.execution_id, "canonical_exec_01")

    def test_04_pydantic_serialization(self) -> None:
        """Verify model serialization and deserialization."""
        req = AgentStepRequest(
            execution_id="ex_ser_01",
            step_index=1,
            prompt="Analyze code",
            parameters={"temp": 0.2},
        )
        data = req.model_dump()
        self.assertEqual(data["execution_id"], "ex_ser_01")
        self.assertEqual(data["step_index"], 1)

        restored = AgentStepRequest.model_validate(data)
        self.assertEqual(restored.prompt, "Analyze code")

    def test_05_capability_contract_compatibility(self) -> None:
        """Verify AgentCapability contains ControlCapability and aligns with Universal Contracts."""
        cap = self.adapter.get_agent_capability()
        self.assertIsInstance(cap.control_capabilities, ControlCapability)
        self.assertIn("http", cap.supported_protocols)

    def test_06_default_capability_fields(self) -> None:
        """Verify AgentCapability defaults."""
        cap = AgentCapability(agent_name="test_bot")
        self.assertTrue(cap.supports_streaming_events)
        self.assertFalse(cap.supports_tool_interception)
        self.assertEqual(len(cap.supported_protocols), 0)

    # 2. Capability Query tests
    def test_07_supports_cancel_true(self) -> None:
        """Verify supports_cancel returns True when capability declares it."""
        self.assertTrue(self.adapter.supports_cancel())

    def test_08_supports_cancel_false(self) -> None:
        """Verify supports_cancel returns False when disabled."""
        cap = AgentCapability(
            agent_name="no_cancel",
            control_capabilities=ControlCapability(supports_cancel=False),
        )
        self.adapter.set_agent_capability(cap)
        self.assertFalse(self.adapter.supports_cancel())

    def test_09_supports_throttle_true(self) -> None:
        """Verify supports_throttle returns True when enabled."""
        self.assertTrue(self.adapter.supports_throttle())

    def test_10_supports_throttle_false(self) -> None:
        """Verify supports_throttle returns False when disabled."""
        cap = AgentCapability(
            agent_name="no_throttle",
            control_capabilities=ControlCapability(supports_throttle=False),
        )
        self.adapter.set_agent_capability(cap)
        self.assertFalse(self.adapter.supports_throttle())

    def test_11_supports_next_step_switch_true(self) -> None:
        """Verify supports_next_step_switch returns True when enabled."""
        self.assertTrue(self.adapter.supports_next_step_switch())

    def test_12_supports_next_step_switch_false(self) -> None:
        """Verify supports_next_step_switch returns False when disabled."""
        cap = AgentCapability(
            agent_name="no_switch",
            control_capabilities=ControlCapability(supports_next_step_switch=False),
        )
        self.adapter.set_agent_capability(cap)
        self.assertFalse(self.adapter.supports_next_step_switch())

    def test_13_supports_terminate_true(self) -> None:
        """Verify supports_terminate returns True when enabled."""
        self.assertTrue(self.adapter.supports_terminate())

    def test_14_supports_terminate_false(self) -> None:
        """Verify supports_terminate returns False when disabled."""
        cap = AgentCapability(
            agent_name="no_term",
            control_capabilities=ControlCapability(supports_terminate=False),
        )
        self.adapter.set_agent_capability(cap)
        self.assertFalse(self.adapter.supports_terminate())

    def test_15_supports_action_continue_always_true(self) -> None:
        """Verify CONTINUE action is always supported."""
        self.assertTrue(self.adapter.supports_action(GovernorAction.CONTINUE))

    def test_16_supports_action_custom_actions(self) -> None:
        """Verify custom Governor actions in supported_actions are supported."""
        cap = AgentCapability(
            agent_name="custom_actions",
            control_capabilities=ControlCapability(
                supported_actions=[GovernorAction.CONTINUE, GovernorAction.ESCALATE],
            ),
        )
        self.adapter.set_agent_capability(cap)
        self.assertTrue(self.adapter.supports_action(GovernorAction.ESCALATE))
        self.assertFalse(self.adapter.supports_action(GovernorAction.STOP))

    # 3. Control Operation tests
    def test_17_normalized_cancel_execution(self) -> None:
        """Verify STOP/cancel control command execution returns COMPLETED."""
        op = ControlOperation(
            operation_id="op_cancel_1",
            execution_id="ex_ctrl_01",
            action=GovernorAction.STOP,
            params={"graceful": True},
        )
        res = self.adapter.execute_control(op)

        self.assertEqual(res.status, ControlStatus.COMPLETED)
        self.assertEqual(res.action, GovernorAction.STOP)
        self.assertEqual(len(self.adapter.received_controls), 1)

    def test_18_normalized_terminate_execution(self) -> None:
        """Verify STOP/terminate command execution returns COMPLETED."""
        op = ControlOperation(
            operation_id="op_term_1",
            execution_id="ex_ctrl_02",
            action=GovernorAction.STOP,
            params={"hard": True},
        )
        res = self.adapter.execute_control(op)
        self.assertEqual(res.status, ControlStatus.COMPLETED)

    def test_19_normalized_throttle_execution(self) -> None:
        """Verify THROTTLE control command execution returns COMPLETED."""
        op = ControlOperation(
            operation_id="op_throt_1",
            execution_id="ex_ctrl_03",
            action=GovernorAction.THROTTLE,
            params={"delay_ms": 1000},
        )
        res = self.adapter.execute_control(op)
        self.assertEqual(res.status, ControlStatus.COMPLETED)

    def test_20_normalized_switch_execution(self) -> None:
        """Verify SWITCH control command execution returns COMPLETED."""
        op = ControlOperation(
            operation_id="op_switch_1",
            execution_id="ex_ctrl_04",
            action=GovernorAction.SWITCH,
            params={"target_provider": "anthropic"},
        )
        res = self.adapter.execute_control(op)
        self.assertEqual(res.status, ControlStatus.COMPLETED)

    def test_21_unsupported_control_operation(self) -> None:
        """Verify unsupported control operation returns UNSUPPORTED without false success."""
        cap = AgentCapability(
            agent_name="no_control",
            control_capabilities=ControlCapability(
                supports_cancel=False,
                supports_terminate=False,
                supports_throttle=False,
                supports_next_step_switch=False,
                supported_actions=[GovernorAction.CONTINUE],
            ),
        )
        self.adapter.set_agent_capability(cap)

        op = ControlOperation(
            operation_id="op_unsupp_1",
            execution_id="ex_ctrl_05",
            action=GovernorAction.THROTTLE,
        )
        res = self.adapter.execute_control(op)

        self.assertEqual(res.status, ControlStatus.UNSUPPORTED)
        self.assertFalse(res.metadata.get("is_supported"))

    def test_22_failed_control_operation(self) -> None:
        """Verify configured control failure returns FAILED."""
        self.adapter.should_fail_control = True
        op = ControlOperation(
            operation_id="op_fail_1",
            execution_id="ex_ctrl_06",
            action=GovernorAction.STOP,
        )
        res = self.adapter.execute_control(op)
        self.assertEqual(res.status, ControlStatus.FAILED)

    def test_23_control_exception_handling(self) -> None:
        """Verify hardware/runtime crash in control raises AgentControlError."""
        self.adapter.should_raise_control = True
        op = ControlOperation(
            operation_id="op_crash_1",
            execution_id="ex_ctrl_07",
            action=GovernorAction.STOP,
        )
        with self.assertRaises(AgentControlError):
            self.adapter.execute_control(op)

    def test_24_no_false_success_on_control_failure(self) -> None:
        """Verify control failure is never disguised as COMPLETED or ACCEPTED."""
        self.adapter.should_fail_control = True
        op = ControlOperation(
            operation_id="op_fail_2",
            execution_id="ex_ctrl_08",
            action=GovernorAction.THROTTLE,
        )
        res = self.adapter.execute_control(op)
        self.assertNotEqual(res.status, ControlStatus.COMPLETED)
        self.assertNotEqual(res.status, ControlStatus.ACCEPTED)

    # 4. Step Execution tests
    def test_25_execute_step_success(self) -> None:
        """Verify executing an agent step produces valid AgentStepResponse."""
        req = AgentStepRequest(execution_id="ex_step_01", step_index=0, prompt="Plan task")
        resp = self.adapter.execute_step(req)

        self.assertEqual(resp.execution_id, "ex_step_01")
        self.assertEqual(resp.step_index, 0)
        self.assertEqual(resp.finish_reason, "stop")

    def test_26_step_index_and_content_fidelity(self) -> None:
        """Verify step index increments and content matches."""
        req0 = AgentStepRequest(execution_id="ex_step_02", step_index=0)
        req1 = AgentStepRequest(execution_id="ex_step_02", step_index=1)

        resp0 = self.adapter.execute_step(req0)
        resp1 = self.adapter.execute_step(req1)

        self.assertEqual(resp0.step_index, 0)
        self.assertEqual(resp1.step_index, 1)

    def test_27_tool_calls_in_step_response(self) -> None:
        """Verify tool calls in request are mirrored in step response."""
        tools = [{"name": "web_search", "description": "Search the web"}]
        req = AgentStepRequest(execution_id="ex_step_03", step_index=0, tools=tools)
        resp = self.adapter.execute_step(req)

        self.assertIsNotNone(resp.tool_calls)
        self.assertEqual(len(resp.tool_calls), 1)
        self.assertEqual(resp.tool_calls[0]["name"], "web_search")

    def test_28_auto_attachment_on_step_execution(self) -> None:
        """Verify step execution auto-attaches a session if not explicitly attached."""
        req = AgentStepRequest(execution_id="ex_auto_attach", step_index=0)
        self.adapter.execute_step(req)

        session = self.adapter.get_session("ex_auto_attach")
        self.assertIsNotNone(session)
        self.assertTrue(session.is_active)

    def test_29_session_step_counter_increments(self) -> None:
        """Verify session step counter tracks step count monotonically."""
        self.adapter.attach_execution("ex_step_count")
        for i in range(4):
            self.adapter.execute_step(AgentStepRequest(execution_id="ex_step_count", step_index=i))

        session = self.adapter.get_session("ex_step_count")
        self.assertEqual(session.step_count, 4)

    def test_30_step_failure_simulation(self) -> None:
        """Verify should_fail_step raises AgentExecutionError."""
        self.adapter.should_fail_step = True
        req = AgentStepRequest(execution_id="ex_fail_step", step_index=0)
        with self.assertRaises(AgentExecutionError):
            self.adapter.execute_step(req)

    def test_31_step_crash_simulation(self) -> None:
        """Verify should_raise_step raises AgentExecutionError."""
        self.adapter.should_raise_step = True
        req = AgentStepRequest(execution_id="ex_crash_step", step_index=0)
        with self.assertRaises(AgentExecutionError):
            self.adapter.execute_step(req)

    # 5. Attachment & Session Isolation tests
    def test_32_explicit_attach_and_detach(self) -> None:
        """Verify explicit attach and detach lifecycle."""
        session = self.adapter.attach_execution("ex_lifecycle", metadata={"env": "prod"})
        self.assertTrue(session.is_active)
        self.assertEqual(session.metadata.get("env"), "prod")

        self.adapter.detach_execution("ex_lifecycle")
        detached = self.adapter.get_session("ex_lifecycle")
        self.assertFalse(detached.is_active)

    def test_33_execution_isolation_a_and_b(self) -> None:
        """Verify Execution A and B sessions remain strictly isolated."""
        self.adapter.attach_execution("exec_A")
        self.adapter.attach_execution("exec_B")

        self.adapter.execute_step(AgentStepRequest(execution_id="exec_A", step_index=0))
        self.adapter.execute_step(AgentStepRequest(execution_id="exec_A", step_index=1))
        self.adapter.execute_step(AgentStepRequest(execution_id="exec_B", step_index=0))

        sess_a = self.adapter.get_session("exec_A")
        sess_b = self.adapter.get_session("exec_B")

        self.assertEqual(sess_a.step_count, 2)
        self.assertEqual(sess_b.step_count, 1)

    def test_34_control_history_isolation(self) -> None:
        """Verify control operations on Execution A never bleed into Execution B."""
        self.adapter.attach_execution("exec_A")
        self.adapter.attach_execution("exec_B")

        self.adapter.execute_control(ControlOperation(
            operation_id="op_A",
            execution_id="exec_A",
            action=GovernorAction.STOP,
        ))

        sess_a = self.adapter.get_session("exec_A")
        sess_b = self.adapter.get_session("exec_B")

        self.assertEqual(len(sess_a.control_history), 1)
        self.assertEqual(len(sess_b.control_history), 0)

    def test_35_concurrent_session_isolation(self) -> None:
        """Verify multiple simultaneous sessions are tracked independently."""
        for i in range(10):
            self.adapter.attach_execution(f"sim_exec_{i}")

        for i in range(10):
            sess = self.adapter.get_session(f"sim_exec_{i}")
            self.assertIsNotNone(sess)
            self.assertEqual(sess.execution_id, f"sim_exec_{i}")

    # 6. Block 22 Control Boundary Integration tests
    def test_36_register_adapter_with_control_boundary(self) -> None:
        """Verify adapter registers with Block 22 ExecutionControlBoundary as IControlExecutor."""
        boundary = ExecutionControlBoundary()
        boundary.register_executor("ex_bound_01", self.adapter)

        cap = boundary.get_capability("ex_bound_01")
        self.assertIsNotNone(cap)
        self.assertTrue(cap.supports_cancel)

    def test_37_control_boundary_syncs_capability_from_adapter(self) -> None:
        """Verify Control Boundary syncs capability declarations from the adapter."""
        custom_cap = AgentCapability(
            agent_name="custom_sync",
            control_capabilities=ControlCapability(
                supports_throttle=True,
                supports_cancel=False,
            ),
        )
        custom_adapter = ReferenceUniversalAgentAdapter(capability=custom_cap)
        boundary = ExecutionControlBoundary()
        boundary.register_executor("ex_sync_01", custom_adapter)

        self.assertTrue(boundary.supports_throttle("ex_sync_01"))
        self.assertFalse(boundary.supports_cancel("ex_sync_01"))

    def test_38_control_boundary_dispatches_to_agent_adapter(self) -> None:
        """Verify Control Boundary dispatching STOP invokes the agent adapter."""
        boundary = ExecutionControlBoundary()
        boundary.register_executor("ex_disp_01", self.adapter)

        result = boundary.dispatch_control("ex_disp_01", GovernorAction.STOP, params={"graceful": True})
        self.assertEqual(result.status, ControlStatus.COMPLETED)
        self.assertEqual(len(self.adapter.received_controls), 1)

    def test_39_control_boundary_dispatches_throttle_to_adapter(self) -> None:
        """Verify Control Boundary dispatching THROTTLE with delay_ms reaches adapter."""
        boundary = ExecutionControlBoundary()
        boundary.register_executor("ex_disp_02", self.adapter)

        result = boundary.dispatch_control("ex_disp_02", GovernorAction.THROTTLE, params={"delay_ms": 250})
        self.assertEqual(result.status, ControlStatus.COMPLETED)
        self.assertEqual(self.adapter.received_controls[0].params.get("delay_ms"), 250)

    def test_40_control_boundary_unsupported_action_with_adapter(self) -> None:
        """Verify Control Boundary returns UNSUPPORTED when adapter lacks capability."""
        no_throttle_cap = AgentCapability(
            agent_name="no_throt",
            control_capabilities=ControlCapability(supports_throttle=False),
        )
        adapter = ReferenceUniversalAgentAdapter(capability=no_throttle_cap)
        boundary = ExecutionControlBoundary()
        boundary.register_executor("ex_disp_03", adapter)

        result = boundary.dispatch_control("ex_disp_03", GovernorAction.THROTTLE)
        self.assertEqual(result.status, ControlStatus.UNSUPPORTED)
        self.assertEqual(len(adapter.received_controls), 0)

    # 7. Event Integration tests
    def test_41_step_completed_event_emitted(self) -> None:
        """Verify ExecutionCompleted event is emitted on EventBus upon step completion."""
        bus = InMemoryEventBus()
        adapter_with_bus = ReferenceUniversalAgentAdapter(event_bus=bus)

        events: List[ExecutionEvent] = []
        bus.subscribe(lambda ev: events.append(ev))

        adapter_with_bus.execute_step(AgentStepRequest(execution_id="ex_ev_01", step_index=0))

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].type, EventType.EXECUTION_COMPLETED)

    def test_42_event_execution_id_matches(self) -> None:
        """Verify event envelope execution_id matches request execution_id."""
        bus = InMemoryEventBus()
        adapter_with_bus = ReferenceUniversalAgentAdapter(event_bus=bus)

        events: List[ExecutionEvent] = []
        bus.subscribe(lambda ev: events.append(ev))

        adapter_with_bus.execute_step(AgentStepRequest(execution_id="ex_ev_02", step_index=1))
        self.assertEqual(events[0].execution_id, "ex_ev_02")

    def test_43_event_payload_content(self) -> None:
        """Verify event payload contains step_index and agent_id."""
        bus = InMemoryEventBus()
        adapter_with_bus = ReferenceUniversalAgentAdapter(agent_id="agt_event_test", event_bus=bus)

        events: List[ExecutionEvent] = []
        bus.subscribe(lambda ev: events.append(ev))

        adapter_with_bus.execute_step(AgentStepRequest(execution_id="ex_ev_03", step_index=3))
        self.assertEqual(events[0].payload.get("step_index"), 3)
        self.assertEqual(events[0].payload.get("agent_id"), "agt_event_test")

    def test_44_event_bus_exception_safety(self) -> None:
        """Verify step execution succeeds even if event bus subscriber fails."""
        bus = InMemoryEventBus()
        adapter_with_bus = ReferenceUniversalAgentAdapter(event_bus=bus)

        def faulty_subscriber(ev: ExecutionEvent) -> None:
            raise RuntimeError("Subscriber exploded")

        bus.subscribe(faulty_subscriber)

        resp = adapter_with_bus.execute_step(AgentStepRequest(execution_id="ex_ev_04", step_index=0))
        self.assertEqual(resp.execution_id, "ex_ev_04")

    # 8. Error Normalization tests
    def test_45_normalize_exception_error(self) -> None:
        """Verify normalizing a standard Python exception."""
        err = self.adapter.normalize_error(ValueError("Invalid token parameter"), execution_id="ex_norm_01")
        self.assertEqual(err.error_code, "ValueError")
        self.assertIn("Invalid token parameter", err.message)
        self.assertEqual(err.details.get("execution_id"), "ex_norm_01")

    def test_46_normalize_dict_error(self) -> None:
        """Verify normalizing a structured error dictionary."""
        raw = {"code": "RATE_LIMIT_EXCEEDED", "message": "Agent hit API quota"}
        err = self.adapter.normalize_error(raw)
        self.assertEqual(err.error_code, "RATE_LIMIT_EXCEEDED")
        self.assertEqual(err.message, "Agent hit API quota")

    def test_47_normalize_string_error(self) -> None:
        """Verify normalizing a raw error string."""
        err = self.adapter.normalize_error("Process killed by OS")
        self.assertEqual(err.error_code, "AGENT_ERROR")
        self.assertEqual(err.message, "Process killed by OS")

    # 9. Architecture Boundary tests
    def test_48_no_policy_logic_in_adapter(self) -> None:
        """Verify agents package contains zero policy evaluation logic."""
        import infuse.agents
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.agents")]
        for mod in modules:
            src = inspect.getsource(mod)
            self.assertNotIn("GovernancePolicy", src)
            self.assertNotIn("evaluate_policy", src)

    def test_49_no_governor_decision_making(self) -> None:
        """Verify agents package makes zero Governor decisions."""
        import infuse.agents
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.agents")]
        for mod in modules:
            src = inspect.getsource(mod)
            self.assertNotIn("derive_state", src)
            self.assertNotIn("select_action", src)

    def test_50_no_routing_or_model_selection(self) -> None:
        """Verify agents package contains zero provider or model selection routing."""
        import infuse.agents
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.agents")]
        for mod in modules:
            src = inspect.getsource(mod)
            self.assertNotIn("route_request", src)
            self.assertNotIn("select_provider", src)

    def test_51_no_lifecycle_mutation(self) -> None:
        """Verify agents package does not mutate lifecycle states directly."""
        import infuse.agents
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.agents")]
        for mod in modules:
            src = inspect.getsource(mod)
            self.assertNotIn("transition_lifecycle", src)
            self.assertNotIn("set_lifecycle_state", src)

    def test_52_no_observer_coupling(self) -> None:
        """Verify agents package does not invoke observers directly."""
        import infuse.agents
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.agents")]
        for mod in modules:
            src = inspect.getsource(mod)
            self.assertNotIn("TokenObserver", src)
            self.assertNotIn("EconomicsEngine", src)
            self.assertNotIn("HealthEngine", src)

    def test_53_zero_provider_and_agent_sdk_imports(self) -> None:
        """Verify agents package contains zero concrete provider/agent SDK imports."""
        import infuse.agents
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.agents")]
        forbidden = [
            "openai", "anthropic", "google.generativeai", "cohere",
            "claudecode", "opencode", "codex", "hermes", "openclaw", "lovable",
        ]
        for mod in modules:
            src = inspect.getsource(mod)
            for f in forbidden:
                self.assertNotIn(f"import {f}", src)
                self.assertNotIn(f"from {f}", src)

    def test_54_zero_database_and_network_imports(self) -> None:
        """Verify agents package contains zero database or network socket imports."""
        import infuse.agents
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.agents")]
        forbidden = ["sqlite3", "psycopg2", "sqlalchemy", "redis", "requests", "urllib", "httpx", "aiohttp", "socket"]
        for mod in modules:
            src = inspect.getsource(mod)
            for f in forbidden:
                self.assertNotIn(f"import {f}", src)
                self.assertNotIn(f"from {f}", src)

    # 10. Concurrency & Thread Safety tests
    def test_55_thread_safe_concurrent_step_executions(self) -> None:
        """Verify thread-safe concurrent step executions across multiple threads."""
        threads = []
        for i in range(16):
            req = AgentStepRequest(execution_id=f"th_step_exec_{i}", step_index=0)
            t = threading.Thread(target=self.adapter.execute_step, args=(req,))
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        for i in range(16):
            sess = self.adapter.get_session(f"th_step_exec_{i}")
            self.assertIsNotNone(sess)
            self.assertEqual(sess.step_count, 1)

    def test_56_thread_safe_concurrent_control_executions(self) -> None:
        """Verify thread-safe concurrent control operations across multiple threads."""
        threads = []
        for i in range(16):
            op = ControlOperation(
                operation_id=f"th_op_{i}",
                execution_id=f"th_ctrl_exec_{i}",
                action=GovernorAction.STOP,
            )
            t = threading.Thread(target=self.adapter.execute_control, args=(op,))
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(self.adapter.received_controls), 16)


if __name__ == "__main__":
    unittest.main()
