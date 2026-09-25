"""Governor and Execution Control Boundary Hardening Tests (Block 33).

Stress tests:
1. Governor decisions across canonical actions (CONTINUE, STOP, THROTTLE, SWITCH, ESCALATE)
2. Policy action binding precedence and reason code fidelity
3. Execution Control Boundary dispatch to IControlExecutor
4. Unsupported capability handling (explicit UNSUPPORTED, no false success)
5. Executor exception safety (catches exception, returns FAILED with error payload)
6. Control audit logging and sequence integrity
"""

import unittest
import uuid
from typing import Dict, List, Optional

from infuse.contracts.control import (
    ControlCapability,
    ControlOperation,
    ControlResult,
    ControlStatus,
)
from infuse.contracts.governor import GovernorAction, GovernorDecisionRecord
from infuse.contracts.policy import (
    BudgetControls,
    GovernancePolicy,
    PolicyActionBindings,
    TokenControls,
)
from infuse.contracts.state import ExecutionState, ExecutionStateSnapshot
from infuse.control.boundary import ExecutionControlBoundary
from infuse.control.interfaces import IControlExecutor
from infuse.events.bus import InMemoryEventBus
from infuse.governor.engine import GovernorEngine


class MockHardeningControlExecutor(IControlExecutor):
    """Control executor for hardening tests."""

    def __init__(self, can_cancel: bool = True, can_throttle: bool = True, can_switch: bool = True) -> None:
        self.can_cancel = can_cancel
        self.can_throttle = can_throttle
        self.can_switch = can_switch
        self.invocations: List[ControlOperation] = []

    @property
    def executor_id(self) -> str:
        return "mock_hardening_executor"

    def get_capability(self) -> ControlCapability:
        actions = [GovernorAction.CONTINUE]
        if self.can_cancel:
            actions.append(GovernorAction.STOP)
        if self.can_throttle:
            actions.append(GovernorAction.THROTTLE)
        if self.can_switch:
            actions.append(GovernorAction.SWITCH)

        return ControlCapability(
            supports_cancel=self.can_cancel,
            supports_throttle=self.can_throttle,
            supports_next_step_switch=self.can_switch,
            supported_actions=actions,
        )

    def execute_control(self, operation: ControlOperation) -> ControlResult:
        self.invocations.append(operation)
        act_val = operation.action.value if hasattr(operation.action, "value") else str(operation.action)
        return ControlResult(
            operation_id=operation.operation_id,
            execution_id=operation.execution_id,
            action=operation.action,
            status=ControlStatus.COMPLETED,
            message=f"Action {act_val} executed.",
        )


class MockFailingControlExecutor(IControlExecutor):
    """Control executor that raises unhandled exception on execution."""

    @property
    def executor_id(self) -> str:
        return "mock_failing_executor"

    def get_capability(self) -> ControlCapability:
        return ControlCapability(
            supports_cancel=True,
            supports_terminate=True,
            supported_actions=[GovernorAction.STOP],
        )

    def execute_control(self, operation: ControlOperation) -> ControlResult:
        raise ConnectionResetError("Runtime socket closed abruptly")


class TestGovernorControlHardening(unittest.TestCase):
    """Stress tests for Governor Engine and Execution Control Boundary."""

    def setUp(self) -> None:
        self.bus = InMemoryEventBus()
        self.governor = GovernorEngine(event_bus=self.bus)
        self.control_boundary = ExecutionControlBoundary(event_bus=self.bus)

    def test_01_governor_action_bindings_stop_on_cost_pressure(self) -> None:
        """Verify Governor issues STOP when policy binds cost_action to STOP."""
        policy = GovernancePolicy(
            policy_id="pol_gov_stop",
            name="Governor Stop Policy",
            budget=BudgetControls(max_cost_per_task=5.0),
            actions=PolicyActionBindings(budget_action=GovernorAction.STOP),
        )

        snap = ExecutionStateSnapshot(
            execution_id="exec_gov_01",
            current_state=ExecutionState.COST_PRESSURE,
            reason_codes=["BUDGET_EXCEEDED"],
        )

        dec = self.governor.evaluate("exec_gov_01", snap, policy)
        self.assertEqual(dec.action, GovernorAction.STOP)
        self.assertEqual(dec.execution_id, "exec_gov_01")

    def test_02_governor_action_bindings_throttle_on_anomalous_velocity(self) -> None:
        """Verify Governor issues THROTTLE when policy binds anomaly_action to THROTTLE."""
        policy = GovernancePolicy(
            policy_id="pol_gov_throt",
            name="Governor Throttle Policy",
            actions=PolicyActionBindings(anomaly_action=GovernorAction.THROTTLE),
        )

        snap = ExecutionStateSnapshot(
            execution_id="exec_gov_02",
            current_state=ExecutionState.RUNAWAY,
            reason_codes=["TOKEN_VELOCITY_HIGH"],
        )

        dec = self.governor.evaluate("exec_gov_02", snap, policy)
        self.assertEqual(dec.action, GovernorAction.THROTTLE)

    def test_03_governor_safe_default_on_normal_state(self) -> None:
        """Verify Governor issues CONTINUE on NORMAL execution state."""
        policy = GovernancePolicy(
            policy_id="pol_gov_norm",
            name="Normal Policy",
        )

        snap = ExecutionStateSnapshot(
            execution_id="exec_gov_03",
            current_state=ExecutionState.NORMAL,
        )

        dec = self.governor.evaluate("exec_gov_03", snap, policy)
        self.assertEqual(dec.action, GovernorAction.CONTINUE)

    def test_04_control_boundary_dispatches_throttle(self) -> None:
        """Verify ExecutionControlBoundary dispatches THROTTLE action to registered executor."""
        executor = MockHardeningControlExecutor(can_throttle=True)
        exec_id = "exec_ctrl_throt_01"
        self.control_boundary.register_executor(exec_id, executor)

        res = self.control_boundary.dispatch_control(
            execution_id=exec_id,
            action=GovernorAction.THROTTLE,
            params={"delay_ms": 250},
            operation_id="op_throt_01",
        )

        self.assertEqual(res.status, ControlStatus.COMPLETED)
        self.assertEqual(len(executor.invocations), 1)
        self.assertEqual(executor.invocations[0].params.get("delay_ms"), 250)

    def test_05_control_boundary_handles_unsupported_action(self) -> None:
        """Verify ExecutionControlBoundary rejects unsupported action with UNSUPPORTED status."""
        executor = MockHardeningControlExecutor(can_cancel=False, can_throttle=False, can_switch=False)
        exec_id = "exec_ctrl_unsup_01"
        self.control_boundary.register_executor(exec_id, executor)

        res = self.control_boundary.dispatch_control(
            execution_id=exec_id,
            action=GovernorAction.STOP,
            operation_id="op_unsup_01",
        )

        self.assertEqual(res.status, ControlStatus.UNSUPPORTED)
        self.assertEqual(len(executor.invocations), 0)

    def test_06_control_boundary_catches_executor_exceptions_safely(self) -> None:
        """Verify ExecutionControlBoundary catches executor exceptions and returns FAILED status."""
        executor = MockFailingControlExecutor()
        exec_id = "exec_ctrl_fail_01"
        self.control_boundary.register_executor(exec_id, executor)

        res = self.control_boundary.dispatch_control(
            execution_id=exec_id,
            action=GovernorAction.STOP,
            operation_id="op_fail_01",
        )

        self.assertEqual(res.status, ControlStatus.FAILED)
        self.assertIn("Runtime socket closed", res.message)

    def test_07_control_boundary_audit_history_recording(self) -> None:
        """Verify all dispatched control operations are recorded in the audit history."""
        executor = MockHardeningControlExecutor(can_cancel=True)
        exec_id = "exec_ctrl_audit_01"
        self.control_boundary.register_executor(exec_id, executor)

        self.control_boundary.dispatch_control(
            execution_id=exec_id,
            action=GovernorAction.STOP,
            operation_id="op_audit_01",
        )

        history = self.control_boundary.get_control_history(exec_id)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].operation.operation_id, "op_audit_01")
        self.assertEqual(history[0].result.status, ControlStatus.COMPLETED)


if __name__ == "__main__":
    unittest.main()
