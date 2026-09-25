"""INFUSE Block 34 — Governance Authority and Control Boundary Security Suite.

Validates that:
- Policy input validation rejects malformed, negative, or invalid action bindings
- Policies, Observers, and State cannot directly dispatch or enforce control actions
- The Governor is the sole control decision authority
- The Execution Control Boundary is the sole physical translation/dispatch path
- Cross-execution control attempts cannot affect foreign executions
- Unsupported control capabilities are safely reported as UNSUPPORTED
- Executor exceptions during control operations are safely isolated
"""

import unittest
import uuid
from decimal import Decimal

from infuse.contracts.capabilities import AgentCapability
from infuse.contracts.control import ControlCapability, ControlOperation, ControlStatus
from infuse.contracts.governor import GovernorAction, GovernorDecisionRecord
from infuse.contracts.policy import (
    AnomalyProtection,
    BudgetControls,
    GovernancePolicy,
    PolicyActionBindings,
    RequestControls,
    RuntimeControls,
    TokenControls,
)
from infuse.contracts.state import ExecutionState, ExecutionStateSnapshot
from infuse.control.boundary import ExecutionControlBoundary
from infuse.e2e.environment import EndToEndIntegrationEnvironment
from infuse.governor.engine import GovernorEngine
from infuse.policy.errors import PolicyValidationError
from infuse.policy.manager import PolicyManager


class TestGovernanceAuthorizationSecurity(unittest.TestCase):
    """Verifies that governance authority invariants cannot be forged, bypassed, or tampered."""

    def setUp(self) -> None:
        self.env = EndToEndIntegrationEnvironment()
        self.governor = GovernorEngine()
        self.boundary = ExecutionControlBoundary()
        self.policy_mgr = PolicyManager()

    def test_01_policy_validation_rejects_negative_budget(self) -> None:
        """Verify policy manager rejects policies with negative budget constraints."""
        from infuse.policy.validation import validate_policy
        policy = GovernancePolicy(
            policy_id="pol_malicious_neg",
            name="Negative Budget Policy",
            budget=BudgetControls(max_cost_per_task=Decimal("-10.00")),
            actions=PolicyActionBindings(),
        )
        with self.assertRaises(PolicyValidationError):
            validate_policy(policy)

    def test_02_policy_validation_rejects_negative_tokens(self) -> None:
        """Verify policy manager rejects policies with negative token limits."""
        from infuse.policy.validation import validate_policy
        policy = GovernancePolicy(
            policy_id="pol_malicious_tokens",
            name="Negative Tokens Policy",
            tokens=TokenControls(max_total_tokens=-500),
            actions=PolicyActionBindings(),
        )
        with self.assertRaises(PolicyValidationError):
            validate_policy(policy)

    def test_03_policy_cannot_directly_execute_control_actions(self) -> None:
        """Verify GovernancePolicy has no execution/dispatch methods."""
        policy = GovernancePolicy(
            policy_id="pol_data_only",
            name="Data Only Policy",
            actions=PolicyActionBindings(),
        )
        self.assertFalse(hasattr(policy, "execute"))
        self.assertFalse(hasattr(policy, "dispatch"))
        self.assertFalse(hasattr(policy, "enforce"))

    def test_04_observers_cannot_directly_dispatch_control_actions(self) -> None:
        """Verify telemetry observers contain zero control dispatch mechanisms."""
        self.assertFalse(hasattr(self.env.token_observer, "dispatch_control"))
        self.assertFalse(hasattr(self.env.health_engine, "dispatch_control"))
        self.assertFalse(hasattr(self.env.economics_engine, "dispatch_control"))
        self.assertFalse(hasattr(self.env.tool_observer, "dispatch_control"))
        self.assertFalse(hasattr(self.env.web_observer, "dispatch_control"))

    def test_05_state_engine_cannot_directly_dispatch_control_actions(self) -> None:
        """Verify ExecutionStateEngine derives facts only and cannot dispatch control."""
        self.assertFalse(hasattr(self.env.state_engine, "dispatch_control"))
        self.assertFalse(hasattr(self.env.state_engine, "enforce_decision"))

    def test_06_governor_evaluates_deterministically_from_state(self) -> None:
        """Verify Governor returns immutable DecisionRecord and does not perform physical execution."""
        exec_id = f"exec_gov_sec_{uuid.uuid4().hex[:8]}"
        state_snap = ExecutionStateSnapshot(
            execution_id=exec_id,
            current_state=ExecutionState.RUNAWAY,
            reason_codes=["ANOMALY_RUNAWAY"],
        )
        policy = GovernancePolicy(
            policy_id="pol_stop_on_crit",
            name="Stop Policy",
            actions=PolicyActionBindings(anomaly_action=GovernorAction.STOP),
        )

        decision = self.governor.evaluate(
            execution_id=exec_id,
            state_snapshot=state_snap,
            policy=policy,
        )

        self.assertIsInstance(decision, GovernorDecisionRecord)
        self.assertEqual(decision.action, GovernorAction.STOP)
        self.assertEqual(decision.execution_id, exec_id)

    def test_07_control_boundary_enforces_executor_registration(self) -> None:
        """Verify dispatching control on unregistered execution fails safely."""
        unregistered_id = "exec_unregistered_phantom_1234"
        result = self.boundary.dispatch_control(
            execution_id=unregistered_id,
            action=GovernorAction.STOP,
        )
        self.assertEqual(result.status, ControlStatus.UNSUPPORTED)
        self.assertIn("not supported", result.message)

    def test_08_cross_execution_control_isolation(self) -> None:
        """Verify executor registered for Execution A cannot be hijacked by Execution B."""
        exec_a = "exec_alpha_1"
        exec_b = "exec_beta_2"

        adapter_a = self.env.get_agent_adapter("universal")
        self.boundary.register_executor(exec_a, adapter_a)

        # Attempt to dispatch decision for exec_b through boundary
        result_b = self.boundary.dispatch_control(
            execution_id=exec_b,
            action=GovernorAction.STOP,
        )
        self.assertEqual(result_b.status, ControlStatus.UNSUPPORTED)
        self.assertIn("not supported", result_b.message)

    def test_09_unsupported_capability_safely_rejected(self) -> None:
        """Verify agent adapter with unsupported action returns UNSUPPORTED status."""
        exec_id = "exec_unsupported_cap"
        adapter = self.env.get_agent_adapter("universal")
        adapter.set_agent_capability(AgentCapability(
            agent_name="universal",
            control_capabilities=ControlCapability(
                supports_cancel=False,
                supports_throttle=False,
                supports_next_step_switch=False,
                supports_terminate=False,
                supported_actions=[GovernorAction.CONTINUE],
            ),
        ))
        self.boundary.register_executor(exec_id, adapter)

        result = self.boundary.dispatch_control(
            execution_id=exec_id,
            action=GovernorAction.THROTTLE,
        )
        self.assertEqual(result.status, ControlStatus.UNSUPPORTED)

    def test_10_control_executor_exception_containment(self) -> None:
        """Verify exception raised inside an executor is safely caught and returns FAILED status."""
        class ExplodingExecutor:
            executor_id = "exploding_1"
            def get_capability(self):
                return ControlCapability(supports_cancel=True, supported_actions=[GovernorAction.STOP])
            def execute_control(self, operation):
                raise RuntimeError("Hardware failure during control dispatch!")

        exec_id = "exec_exploding"
        self.boundary.register_executor(exec_id, ExplodingExecutor())

        result = self.boundary.dispatch_control(
            execution_id=exec_id,
            action=GovernorAction.STOP,
        )
        self.assertEqual(result.status, ControlStatus.FAILED)
        self.assertIn("Hardware failure", result.message)


if __name__ == "__main__":
    unittest.main()
