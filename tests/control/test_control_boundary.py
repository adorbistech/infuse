"""Comprehensive Unit, Integration, and Boundary Test Suite for Block 22 Execution Control Boundary."""

import inspect
import sys
import threading
import unittest
from typing import Any, Dict, List, Optional

from infuse.contracts.control import (
    ControlCapability,
    ControlOperation,
    ControlResult,
    ControlStatus,
)
from infuse.contracts.events import EventType, ExecutionEvent
from infuse.contracts.governor import GovernorAction
from infuse.control.boundary import ExecutionControlBoundary
from infuse.control.interfaces import IControlExecutor
from infuse.control.models import ControlAuditRecord
from infuse.events.bus import InMemoryEventBus


class MockControlExecutor(IControlExecutor):
    """Mock physical control executor for testing boundary dispatch."""

    def __init__(
        self,
        executor_id: str = "mock_executor",
        capability: Optional[ControlCapability] = None,
        should_fail: bool = False,
        should_raise: bool = False,
    ) -> None:
        self._executor_id = executor_id
        self._capability = capability or ControlCapability(
            supports_cancel=True,
            supports_throttle=True,
            supports_next_step_switch=True,
            supports_terminate=True,
            supported_actions=[
                GovernorAction.CONTINUE,
                GovernorAction.STOP,
                GovernorAction.THROTTLE,
                GovernorAction.SWITCH,
                GovernorAction.OPTIMIZE,
            ],
        )
        self.should_fail = should_fail
        self.should_raise = should_raise
        self.invocations: List[ControlOperation] = []

    @property
    def executor_id(self) -> str:
        return self._executor_id

    def get_capability(self) -> ControlCapability:
        return self._capability

    def execute_control(self, operation: ControlOperation) -> ControlResult:
        self.invocations.append(operation)
        if self.should_raise:
            raise RuntimeError("Underlying executor hardware fault")
        if self.should_fail:
            return ControlResult(
                operation_id=operation.operation_id,
                execution_id=operation.execution_id,
                action=operation.action,
                status=ControlStatus.FAILED,
                message="Executor physical failure",
            )
        return ControlResult(
            operation_id=operation.operation_id,
            execution_id=operation.execution_id,
            action=operation.action,
            status=ControlStatus.COMPLETED,
            message="Executor successfully completed action",
            metadata={"applied": True},
        )


class TestExecutionControlBoundary(unittest.TestCase):
    """Test suite verifying Execution Control Boundary capabilities, dispatch, safety, and isolation."""

    def setUp(self) -> None:
        self.boundary = ExecutionControlBoundary()

    # 1. Contract tests
    def test_01_boundary_initialization(self) -> None:
        """Verify boundary initializes with empty state and zero registered executors."""
        self.assertIsNone(self.boundary.get_capability("nonexistent"))
        self.assertIsNone(self.boundary.get_latest_result("nonexistent"))
        self.assertEqual(len(self.boundary.get_control_history("nonexistent")), 0)

    def test_02_valid_control_request(self) -> None:
        """Verify dispatching a valid action with params returns a valid ControlResult."""
        cap = ControlCapability(supports_throttle=True)
        self.boundary.register_capability("ex_02", cap)

        result = self.boundary.dispatch_control("ex_02", GovernorAction.THROTTLE, params={"delay_ms": 500})
        self.assertEqual(result.execution_id, "ex_02")
        self.assertEqual(result.action, GovernorAction.THROTTLE)
        self.assertEqual(result.status, ControlStatus.ACCEPTED)

    def test_03_invalid_execution_id_rejected(self) -> None:
        """Verify empty or whitespace execution_id raises ValueError."""
        with self.assertRaises(ValueError):
            self.boundary.dispatch_control("", GovernorAction.STOP)
        with self.assertRaises(ValueError):
            self.boundary.dispatch_control("   ", GovernorAction.STOP)

    def test_04_invalid_action_rejected(self) -> None:
        """Verify None action raises ValueError."""
        with self.assertRaises(ValueError):
            self.boundary.dispatch_control("ex_04", None)  # type: ignore

    def test_05_contract_serialization(self) -> None:
        """Verify Pydantic serialization roundtrip of control models."""
        op = ControlOperation(
            operation_id="op_1",
            execution_id="ex_05",
            action=GovernorAction.SWITCH,
            params={"target": "model_b"},
        )
        data = op.model_dump()
        self.assertEqual(data["action"], "SWITCH")
        self.assertEqual(data["params"]["target"], "model_b")

        res = ControlResult(
            operation_id="op_1",
            execution_id="ex_05",
            action=GovernorAction.SWITCH,
            status=ControlStatus.COMPLETED,
        )
        self.assertEqual(res.status, ControlStatus.COMPLETED)

    def test_06_contract_validation(self) -> None:
        """Verify ControlCapability default fields and validations."""
        cap = ControlCapability()
        self.assertFalse(cap.supports_cancel)
        self.assertFalse(cap.supports_throttle)
        self.assertFalse(cap.supports_next_step_switch)
        self.assertFalse(cap.supports_terminate)
        self.assertIn(GovernorAction.CONTINUE, cap.supported_actions)

    # 2. Capability tests
    def test_07_supports_cancel_true(self) -> None:
        """Verify supports_cancel returns True when capability declares it."""
        self.boundary.register_capability("ex_07", ControlCapability(supports_cancel=True))
        self.assertTrue(self.boundary.supports_cancel("ex_07"))

    def test_08_supports_cancel_false(self) -> None:
        """Verify supports_cancel returns False when undeclared."""
        self.boundary.register_capability("ex_08", ControlCapability(supports_cancel=False))
        self.assertFalse(self.boundary.supports_cancel("ex_08"))

    def test_09_supports_throttle_true(self) -> None:
        """Verify supports_throttle returns True when declared."""
        self.boundary.register_capability("ex_09", ControlCapability(supports_throttle=True))
        self.assertTrue(self.boundary.supports_throttle("ex_09"))

    def test_10_supports_throttle_false(self) -> None:
        """Verify supports_throttle returns False when undeclared."""
        self.boundary.register_capability("ex_10", ControlCapability(supports_throttle=False))
        self.assertFalse(self.boundary.supports_throttle("ex_10"))

    def test_11_supports_next_step_switch_true(self) -> None:
        """Verify supports_next_step_switch returns True when declared."""
        self.boundary.register_capability("ex_11", ControlCapability(supports_next_step_switch=True))
        self.assertTrue(self.boundary.supports_next_step_switch("ex_11"))

    def test_12_supports_next_step_switch_false(self) -> None:
        """Verify supports_next_step_switch returns False when undeclared."""
        self.boundary.register_capability("ex_12", ControlCapability(supports_next_step_switch=False))
        self.assertFalse(self.boundary.supports_next_step_switch("ex_12"))

    def test_13_supports_terminate_true(self) -> None:
        """Verify supports_terminate returns True when declared."""
        self.boundary.register_capability("ex_13", ControlCapability(supports_terminate=True))
        self.assertTrue(self.boundary.supports_terminate("ex_13"))

    def test_14_supports_terminate_false(self) -> None:
        """Verify supports_terminate returns False when undeclared."""
        self.boundary.register_capability("ex_14", ControlCapability(supports_terminate=False))
        self.assertFalse(self.boundary.supports_terminate("ex_14"))

    def test_15_supports_action_continue_always_true(self) -> None:
        """Verify CONTINUE action is always supported even with empty capability."""
        self.assertTrue(self.boundary.supports_action("ex_15", GovernorAction.CONTINUE))

    def test_16_supports_action_custom_supported_actions(self) -> None:
        """Verify supported_actions list explicitly enables listed actions."""
        cap = ControlCapability(supported_actions=[GovernorAction.OPTIMIZE, GovernorAction.ESCALATE])
        self.boundary.register_capability("ex_16", cap)
        self.assertTrue(self.boundary.supports_action("ex_16", GovernorAction.OPTIMIZE))
        self.assertTrue(self.boundary.supports_action("ex_16", GovernorAction.ESCALATE))
        self.assertFalse(self.boundary.supports_action("ex_16", GovernorAction.STOP))

    # 3. Dispatch tests
    def test_17_dispatch_supported_stop_cancel(self) -> None:
        """Verify STOP dispatches when supports_cancel is True."""
        self.boundary.register_capability("ex_17", ControlCapability(supports_cancel=True))
        res = self.boundary.dispatch_control("ex_17", GovernorAction.STOP)
        self.assertEqual(res.status, ControlStatus.ACCEPTED)

    def test_18_dispatch_supported_stop_terminate(self) -> None:
        """Verify STOP dispatches when supports_terminate is True."""
        self.boundary.register_capability("ex_18", ControlCapability(supports_terminate=True))
        res = self.boundary.dispatch_control("ex_18", GovernorAction.STOP)
        self.assertEqual(res.status, ControlStatus.ACCEPTED)

    def test_19_dispatch_supported_throttle(self) -> None:
        """Verify THROTTLE dispatches when supports_throttle is True."""
        self.boundary.register_capability("ex_19", ControlCapability(supports_throttle=True))
        res = self.boundary.dispatch_control("ex_19", GovernorAction.THROTTLE)
        self.assertEqual(res.status, ControlStatus.ACCEPTED)

    def test_20_dispatch_supported_switch(self) -> None:
        """Verify SWITCH dispatches when supports_next_step_switch is True."""
        self.boundary.register_capability("ex_20", ControlCapability(supports_next_step_switch=True))
        res = self.boundary.dispatch_control("ex_20", GovernorAction.SWITCH)
        self.assertEqual(res.status, ControlStatus.ACCEPTED)

    def test_21_dispatch_supported_continue(self) -> None:
        """Verify CONTINUE dispatches and returns COMPLETED status."""
        res = self.boundary.dispatch_control("ex_21", GovernorAction.CONTINUE)
        self.assertEqual(res.status, ControlStatus.COMPLETED)

    def test_22_dispatch_unsupported_action_safely_rejected(self) -> None:
        """Verify unsupported action returns UNSUPPORTED status without raising uncaught exception."""
        self.boundary.register_capability("ex_22", ControlCapability(supports_throttle=False))
        res = self.boundary.dispatch_control("ex_22", GovernorAction.THROTTLE)
        self.assertEqual(res.status, ControlStatus.UNSUPPORTED)
        self.assertIn("not supported", res.message)

    def test_23_dispatch_unsupported_never_reports_success(self) -> None:
        """Verify unsupported capability is NEVER represented as ACCEPTED or COMPLETED."""
        self.boundary.register_capability("ex_23", ControlCapability(supports_cancel=False, supports_terminate=False))
        res = self.boundary.dispatch_control("ex_23", GovernorAction.STOP)
        self.assertNotEqual(res.status, ControlStatus.ACCEPTED)
        self.assertNotEqual(res.status, ControlStatus.COMPLETED)
        self.assertEqual(res.status, ControlStatus.UNSUPPORTED)

    def test_24_executor_success(self) -> None:
        """Verify registered physical executor executes and returns COMPLETED."""
        executor = MockControlExecutor(executor_id="exec_adapter_01")
        self.boundary.register_executor("ex_24", executor)

        res = self.boundary.dispatch_control("ex_24", GovernorAction.STOP, params={"graceful": True})
        self.assertEqual(res.status, ControlStatus.COMPLETED)
        self.assertEqual(len(executor.invocations), 1)
        self.assertEqual(executor.invocations[0].params.get("graceful"), True)

    def test_25_executor_custom_failure(self) -> None:
        """Verify physical executor reporting failure is preserved as FAILED."""
        executor = MockControlExecutor(should_fail=True)
        self.boundary.register_executor("ex_25", executor)

        res = self.boundary.dispatch_control("ex_25", GovernorAction.THROTTLE)
        self.assertEqual(res.status, ControlStatus.FAILED)
        self.assertIn("Executor physical failure", res.message)

    def test_26_executor_exception_handled_safely(self) -> None:
        """Verify executor throwing exception is caught and returned as FAILED without crashing boundary."""
        executor = MockControlExecutor(should_raise=True)
        self.boundary.register_executor("ex_26", executor)

        res = self.boundary.dispatch_control("ex_26", GovernorAction.SWITCH)
        self.assertEqual(res.status, ControlStatus.FAILED)
        self.assertIn("Underlying executor hardware fault", res.message)

    def test_27_no_false_success_on_executor_failure(self) -> None:
        """Verify executor exceptions or failures never masquerade as ACCEPTED or COMPLETED."""
        executor = MockControlExecutor(should_raise=True)
        self.boundary.register_executor("ex_27", executor)

        res = self.boundary.dispatch_control("ex_27", GovernorAction.STOP)
        self.assertNotEqual(res.status, ControlStatus.COMPLETED)
        self.assertNotEqual(res.status, ControlStatus.ACCEPTED)

    def test_28_executor_registration_syncs_capability(self) -> None:
        """Verify registering an executor automatically syncs its declared capabilities."""
        executor = MockControlExecutor(capability=ControlCapability(supports_throttle=True))
        self.boundary.register_executor("ex_28", executor)

        self.assertTrue(self.boundary.supports_throttle("ex_28"))
        self.assertFalse(self.boundary.supports_next_step_switch("ex_28"))

    # 4. Isolation tests
    def test_29_execution_a_cannot_affect_execution_b(self) -> None:
        """Verify capability configuration for Execution A does not bleed into Execution B."""
        self.boundary.register_capability("exec_A", ControlCapability(supports_throttle=True))
        self.boundary.register_capability("exec_B", ControlCapability(supports_throttle=False))

        self.assertTrue(self.boundary.supports_throttle("exec_A"))
        self.assertFalse(self.boundary.supports_throttle("exec_B"))

    def test_30_result_identity_preserved(self) -> None:
        """Verify returned result retains exact execution_id and action."""
        self.boundary.register_capability("ex_30", ControlCapability(supports_cancel=True))
        res = self.boundary.dispatch_control("ex_30", GovernorAction.STOP)
        self.assertEqual(res.execution_id, "ex_30")
        self.assertEqual(res.action, GovernorAction.STOP)

    def test_31_history_isolated_per_execution(self) -> None:
        """Verify audit history remains completely isolated per execution."""
        self.boundary.register_capability("ex_31_A", ControlCapability(supports_throttle=True))
        self.boundary.register_capability("ex_31_B", ControlCapability(supports_next_step_switch=True))

        self.boundary.dispatch_control("ex_31_A", GovernorAction.THROTTLE)
        self.boundary.dispatch_control("ex_31_B", GovernorAction.SWITCH)

        hist_a = self.boundary.get_control_history("ex_31_A")
        hist_b = self.boundary.get_control_history("ex_31_B")

        self.assertEqual(len(hist_a), 1)
        self.assertEqual(len(hist_b), 1)
        self.assertEqual(hist_a[0].operation.action, GovernorAction.THROTTLE)
        self.assertEqual(hist_b[0].operation.action, GovernorAction.SWITCH)

    def test_32_concurrent_executions_isolated(self) -> None:
        """Verify multiple simultaneous executions maintain independent states."""
        for i in range(10):
            exec_id = f"iso_exec_{i}"
            cap = ControlCapability(supports_throttle=(i % 2 == 0))
            self.boundary.register_capability(exec_id, cap)
            self.assertEqual(self.boundary.supports_throttle(exec_id), (i % 2 == 0))

    # 5. Idempotency tests
    def test_33_duplicate_operation_id_returns_cached_result(self) -> None:
        """Verify dispatching with identical operation_id returns cached result."""
        executor = MockControlExecutor()
        self.boundary.register_executor("ex_33", executor)

        res1 = self.boundary.dispatch_control("ex_33", GovernorAction.STOP, operation_id="fixed_op_123")
        res2 = self.boundary.dispatch_control("ex_33", GovernorAction.STOP, operation_id="fixed_op_123")

        self.assertEqual(res1.operation_id, res2.operation_id)
        self.assertEqual(len(executor.invocations), 1)  # Did not re-execute

    def test_34_repeated_dispatch_without_operation_id_increments_sequence(self) -> None:
        """Verify repeated dispatches generate distinct operation IDs and sequence metadata."""
        self.boundary.register_capability("ex_34", ControlCapability(supports_throttle=True))
        r1 = self.boundary.dispatch_control("ex_34", GovernorAction.THROTTLE)
        r2 = self.boundary.dispatch_control("ex_34", GovernorAction.THROTTLE)

        self.assertNotEqual(r1.operation_id, r2.operation_id)
        hist = self.boundary.get_control_history("ex_34")
        self.assertEqual(len(hist), 2)
        self.assertEqual(hist[0].metadata.get("sequence"), 1)
        self.assertEqual(hist[1].metadata.get("sequence"), 2)

    def test_35_idempotent_replay_does_not_reexecute(self) -> None:
        """Verify executor is invoked exactly once for an idempotent operation ID."""
        executor = MockControlExecutor()
        self.boundary.register_executor("ex_35", executor)

        for _ in range(5):
            self.boundary.dispatch_control("ex_35", GovernorAction.THROTTLE, operation_id="idemp_op_99")

        self.assertEqual(len(executor.invocations), 1)

    # 6. Event tests
    def test_36_control_action_issued_emitted_correctly(self) -> None:
        """Verify ControlActionIssued event is emitted to EventBus on dispatch."""
        bus = InMemoryEventBus()
        self.boundary.attach_to_bus(bus)

        events_received: List[ExecutionEvent] = []
        bus.subscribe(lambda ev: events_received.append(ev))

        self.boundary.register_capability("ex_36", ControlCapability(supports_cancel=True))
        self.boundary.dispatch_control("ex_36", GovernorAction.STOP)

        self.assertEqual(len(events_received), 1)
        self.assertEqual(events_received[0].type, EventType.CONTROL_ACTION_ISSUED)

    def test_37_event_contains_correct_execution_id(self) -> None:
        """Verify event envelope has the correct execution_id."""
        bus = InMemoryEventBus()
        self.boundary.attach_to_bus(bus)
        events_received: List[ExecutionEvent] = []
        bus.subscribe(lambda ev: events_received.append(ev))

        self.boundary.register_capability("ex_37", ControlCapability(supports_throttle=True))
        self.boundary.dispatch_control("ex_37", GovernorAction.THROTTLE)

        self.assertEqual(events_received[0].execution_id, "ex_37")

    def test_38_event_contains_correct_action(self) -> None:
        """Verify event payload contains the requested Governor action string."""
        bus = InMemoryEventBus()
        self.boundary.attach_to_bus(bus)
        events_received: List[ExecutionEvent] = []
        bus.subscribe(lambda ev: events_received.append(ev))

        self.boundary.register_capability("ex_38", ControlCapability(supports_next_step_switch=True))
        self.boundary.dispatch_control("ex_38", GovernorAction.SWITCH)

        self.assertEqual(events_received[0].payload.get("action"), "SWITCH")

    def test_39_event_sequence_handling(self) -> None:
        """Verify sequential event sequence numbers increment properly."""
        bus = InMemoryEventBus()
        self.boundary.attach_to_bus(bus)
        events_received: List[ExecutionEvent] = []
        bus.subscribe(lambda ev: events_received.append(ev))

        self.boundary.register_capability("ex_39", ControlCapability(supports_throttle=True))
        self.boundary.dispatch_control("ex_39", GovernorAction.THROTTLE)
        self.boundary.dispatch_control("ex_39", GovernorAction.THROTTLE)

        self.assertEqual(events_received[0].sequence, 1)
        self.assertEqual(events_received[1].sequence, 2)

    def test_40_bus_exception_does_not_crash_dispatch(self) -> None:
        """Verify boundary dispatch succeeds even if event bus subscriber fails."""
        bus = InMemoryEventBus()
        self.boundary.attach_to_bus(bus)

        def faulty_subscriber(ev: ExecutionEvent) -> None:
            raise RuntimeError("Event subscriber exploded")

        bus.subscribe(faulty_subscriber)

        self.boundary.register_capability("ex_40", ControlCapability(supports_cancel=True))
        res = self.boundary.dispatch_control("ex_40", GovernorAction.STOP)
        self.assertEqual(res.status, ControlStatus.ACCEPTED)

    # 7. Governor separation tests
    def test_41_no_governance_decision_made(self) -> None:
        """Verify boundary does not evaluate policy or calculate state."""
        import infuse.control
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.control")]
        for mod in modules:
            src = inspect.getsource(mod)
            self.assertNotIn("GovernancePolicy", src)
            self.assertNotIn("derive_state", src)

    def test_42_no_action_reinterpretation(self) -> None:
        """Verify boundary never converts an unsupported action to another action."""
        self.boundary.register_capability("ex_42", ControlCapability(supports_throttle=False, supports_cancel=True))
        # Governor requested THROTTLE. Even though CANCEL/STOP is supported, boundary must NOT convert THROTTLE to STOP!
        res = self.boundary.dispatch_control("ex_42", GovernorAction.THROTTLE)
        self.assertEqual(res.status, ControlStatus.UNSUPPORTED)
        self.assertEqual(res.action, GovernorAction.THROTTLE)

    def test_43_no_provider_or_model_selection(self) -> None:
        """Verify boundary contains zero routing or provider selection methods."""
        import infuse.control
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.control")]
        for mod in modules:
            src = inspect.getsource(mod)
            self.assertNotIn("select_provider", src)
            self.assertNotIn("route_request", src)

    def test_44_no_retry_loop_or_engine(self) -> None:
        """Verify boundary does not implement retry loops."""
        import infuse.control
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.control")]
        for mod in modules:
            src = inspect.getsource(mod)
            self.assertNotIn("schedule_retry", src)
            self.assertNotIn("execute_retry", src)

    def test_45_no_lifecycle_mutation(self) -> None:
        """Verify boundary does not mutate execution lifecycle state directly."""
        import infuse.control
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.control")]
        for mod in modules:
            src = inspect.getsource(mod)
            self.assertNotIn("transition_lifecycle", src)
            self.assertNotIn("set_lifecycle_state", src)

    # 8. Safety & Fallback tests
    def test_46_missing_capability_data_not_fabricated(self) -> None:
        """Verify unregistered execution ID returns None capability, not assumed True."""
        self.assertIsNone(self.boundary.get_capability("unregistered_exec"))
        self.assertFalse(self.boundary.supports_throttle("unregistered_exec"))
        self.assertFalse(self.boundary.supports_cancel("unregistered_exec"))
        self.assertFalse(self.boundary.supports_next_step_switch("unregistered_exec"))
        self.assertFalse(self.boundary.supports_terminate("unregistered_exec"))

    def test_47_unknown_action_fails_safely(self) -> None:
        """Verify unsupported action returns UNSUPPORTED with clear message."""
        self.boundary.register_capability("ex_47", ControlCapability())
        res = self.boundary.dispatch_control("ex_47", GovernorAction.STOP)
        self.assertEqual(res.status, ControlStatus.UNSUPPORTED)

    def test_48_audit_history_records_support_status(self) -> None:
        """Verify audit record accurately captures support status."""
        self.boundary.register_capability("ex_48", ControlCapability(supports_cancel=True))
        self.boundary.dispatch_control("ex_48", GovernorAction.STOP)
        self.boundary.dispatch_control("ex_48", GovernorAction.THROTTLE)

        hist = self.boundary.get_control_history("ex_48")
        self.assertEqual(len(hist), 2)
        self.assertTrue(hist[0].is_supported)
        self.assertFalse(hist[1].is_supported)

    def test_49_clear_resets_all_boundary_state(self) -> None:
        """Verify clear() wipes all capabilities, executors, and history."""
        self.boundary.register_capability("ex_49", ControlCapability(supports_throttle=True))
        self.boundary.dispatch_control("ex_49", GovernorAction.THROTTLE)
        self.boundary.clear()

        self.assertIsNone(self.boundary.get_capability("ex_49"))
        self.assertIsNone(self.boundary.get_latest_result("ex_49"))
        self.assertEqual(len(self.boundary.get_control_history("ex_49")), 0)

    # 9. Concurrency & Thread Safety
    def test_50_thread_safe_concurrent_dispatches(self) -> None:
        """Verify thread-safe dispatches across concurrent threads."""
        threads = []
        for i in range(16):
            exec_id = f"th_exec_{i}"
            self.boundary.register_capability(exec_id, ControlCapability(supports_cancel=True))
            t = threading.Thread(
                target=self.boundary.dispatch_control,
                args=(exec_id, GovernorAction.STOP),
            )
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        for i in range(16):
            self.assertIsNotNone(self.boundary.get_latest_result(f"th_exec_{i}"))

    def test_51_thread_safe_capability_queries(self) -> None:
        """Verify concurrent capability reads and writes without data race."""
        threads = []
        for i in range(16):
            exec_id = f"cap_exec_{i}"
            t1 = threading.Thread(
                target=self.boundary.register_capability,
                args=(exec_id, ControlCapability(supports_throttle=(i % 2 == 0))),
            )
            t2 = threading.Thread(
                target=self.boundary.supports_throttle,
                args=(exec_id,),
            )
            threads.extend([t1, t2])

        for t in threads:
            t.start()
        for t in threads:
            t.join()

    # 10. Boundary Architecture & Import Isolation
    def test_52_zero_provider_sdk_imports(self) -> None:
        """Verify control package contains zero provider SDK imports."""
        import infuse.control
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.control")]
        forbidden = ["openai", "anthropic", "google.generativeai", "cohere", "litellm"]
        for mod in modules:
            src = inspect.getsource(mod)
            for f in forbidden:
                self.assertNotIn(f"import {f}", src)
                self.assertNotIn(f"from {f}", src)

    def test_53_zero_database_imports(self) -> None:
        """Verify control package contains zero database library imports."""
        import infuse.control
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.control")]
        forbidden = ["sqlite3", "psycopg2", "sqlalchemy", "redis", "pymongo"]
        for mod in modules:
            src = inspect.getsource(mod)
            for f in forbidden:
                self.assertNotIn(f"import {f}", src)
                self.assertNotIn(f"from {f}", src)

    def test_54_zero_network_imports(self) -> None:
        """Verify control package contains zero HTTP or socket network imports."""
        import infuse.control
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.control")]
        forbidden = ["requests", "urllib", "httpx", "aiohttp", "socket"]
        for mod in modules:
            src = inspect.getsource(mod)
            for f in forbidden:
                self.assertNotIn(f"import {f}", src)
                self.assertNotIn(f"from {f}", src)


if __name__ == "__main__":
    unittest.main()
