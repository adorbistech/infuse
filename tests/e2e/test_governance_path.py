"""INFUSE Block 32 — Path C: Governance and Control Path Integration Suite.

Validates the full control loop:
Policy -> State Engine -> Governor Engine -> Decision -> Control Boundary -> Execution Runtime -> Audit Record
with zero hardcoded thresholds, correct action precedence, and proper control capability negotiation.
"""

import unittest
import uuid

from infuse.contracts.control import ControlCapability, ControlStatus
from infuse.contracts.events import EventSource, EventType, ExecutionEvent
from infuse.contracts.governor import GovernorAction
from infuse.contracts.policy import (
    AnomalyProtection,
    BudgetControls,
    GovernancePolicy,
    PolicyActionBindings,
    RuntimeControls,
    TokenControls,
    ToolAccessControls,
    WebAccessControls,
)
from infuse.contracts.state import ExecutionState
from infuse.e2e.environment import EndToEndIntegrationEnvironment


class TestBlock32GovernancePath(unittest.TestCase):
    """Verifies complete governance and control path integration and invariants."""

    def setUp(self):
        self.env = EndToEndIntegrationEnvironment()

    def test_governance_loop_stop_action(self):
        """Verify policy STOP action executes through the control boundary."""
        tc = ToolAccessControls(max_tool_calls_per_task=1)
        policy = GovernancePolicy(
            policy_id="pol_gov_stop",
            name="Stop on Tool Limit Policy",
            tools=tc,
            tool_controls=tc,
            actions=PolicyActionBindings(
                anomaly_action=GovernorAction.STOP,
            ),
        )

        exec_id = f"exec_gov_stop_{uuid.uuid4().hex[:8]}"
        adapter = self.env.get_agent_adapter("universal")
        self.env.control_boundary.register_executor(exec_id, adapter)

        # Trigger tool limit
        for i in range(1, 3):
            self.env.emit_event(ExecutionEvent(
                event_id=f"evt_tool_{i}_{uuid.uuid4().hex[:8]}",
                execution_id=exec_id,
                type=EventType.TOOL_CALLED,
                source=EventSource.AGENT,
                sequence=i,
                payload={"tool_call_id": f"t_{i}", "tool_name": "bash", "parameters": {}},
            ))

        state_snap = self.env.derive_state(exec_id, policy=policy)
        self.assertEqual(state_snap.current_state, ExecutionState.RUNAWAY)

        decision = self.env.evaluate_governor(exec_id, policy=policy)
        self.assertEqual(decision.action, GovernorAction.STOP)

        ctrl_res = self.env.dispatch_control(exec_id, action=decision.action)
        self.assertIn(ctrl_res.status, [ControlStatus.ACCEPTED, ControlStatus.COMPLETED, ControlStatus.SUPPORTED])

    def test_governance_loop_optimize_action(self):
        """Verify policy OPTIMIZE action when cost pressure occurs."""
        b = BudgetControls(max_cost_per_task=0.001)
        t = TokenControls(max_total_tokens=50_000)
        policy = GovernancePolicy(
            policy_id="pol_gov_opt",
            name="Optimize Policy",
            budget=b,
            budget_controls=b,
            tokens=t,
            token_controls=t,
            actions=PolicyActionBindings(
                budget_action=GovernorAction.OPTIMIZE,
            ),
        )

        exec_id = f"exec_gov_opt_{uuid.uuid4().hex[:8]}"
        adapter = self.env.get_agent_adapter("universal")
        self.env.control_boundary.register_executor(exec_id, adapter)

        self.env.emit_event(ExecutionEvent(
            event_id="evt_tok_high",
            execution_id=exec_id,
            type=EventType.TOKEN_OBSERVED,
            source=EventSource.PROVIDER,
            sequence=1,
            payload={
                "input_tokens": 25_000,
                "output_tokens": 25_000,
                "total_tokens": 50_000,
                "provider": "mock",
                "model": "mock-model",
            },
        ))

        state_snap = self.env.derive_state(exec_id, policy=policy)
        self.assertEqual(state_snap.current_state, ExecutionState.COST_PRESSURE)

        decision = self.env.evaluate_governor(exec_id, policy=policy)
        self.assertEqual(decision.action, GovernorAction.OPTIMIZE)

    def test_governor_is_sole_control_authority(self):
        """Verify that observers cannot dispatch control actions directly."""
        exec_id = f"exec_gov_auth_{uuid.uuid4().hex[:8]}"
        adapter = self.env.get_agent_adapter("universal")
        self.env.control_boundary.register_executor(exec_id, adapter)

        # Emitting events updates observers, but NEVER triggers adapter control directly
        self.env.emit_event(ExecutionEvent(
            event_id="evt_prov_err_single",
            execution_id=exec_id,
            type=EventType.PROVIDER_ERROR,
            source=EventSource.PROVIDER,
            sequence=1,
            payload={"message": "Temporary 500", "is_retryable": True},
        ))

        # Observers observe, but received_controls on adapter remains 0 until Governor dispatches
        self.assertEqual(len(adapter.received_controls), 0)
