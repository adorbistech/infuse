"""Tests for Execution State Contract."""

import unittest
from infuse.contracts.state import ExecutionState, ExecutionActionState, ExecutionStateSnapshot


class TestStateContract(unittest.TestCase):
    """Test canonical execution states and snapshot serialization."""

    def test_canonical_states_complete(self):
        expected_states = {
            "NORMAL", "COST_PRESSURE", "RUNAWAY", "QUALITY_DEGRADED", "PROVIDER_CONSTRAINED"
        }
        actual_states = {s.value for s in ExecutionState}
        self.assertEqual(actual_states, expected_states)

    def test_ui_action_states(self):
        expected_ui_states = {"OPTIMIZED", "THROTTLED", "SWITCHED", "STOPPED"}
        actual_ui_states = {s.value for s in ExecutionActionState}
        self.assertEqual(actual_ui_states, expected_ui_states)

    def test_state_snapshot_model(self):
        snapshot = ExecutionStateSnapshot(
            execution_id="exec_100",
            current_state=ExecutionState.COST_PRESSURE,
            previous_state=ExecutionState.NORMAL,
            reason_codes=["BUDGET_UTILIZATION_82_PERCENT"],
            signals={"budget_used_percent": 82.0, "token_velocity": 450.0},
            transition_metadata={"triggered_by": "TokenObserver"}
        )
        self.assertEqual(snapshot.current_state, ExecutionState.COST_PRESSURE)
        self.assertEqual(snapshot.previous_state, ExecutionState.NORMAL)
        self.assertEqual(snapshot.signals["budget_used_percent"], 82.0)

        # JSON Roundtrip
        json_str = snapshot.model_dump_json()
        loaded = ExecutionStateSnapshot.model_validate_json(json_str)
        self.assertEqual(loaded.current_state, ExecutionState.COST_PRESSURE)
        self.assertEqual(loaded.previous_state, ExecutionState.NORMAL)


if __name__ == "__main__":
    unittest.main()
