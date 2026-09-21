"""Tests for Governor Action & Decision Contract."""

import unittest
from infuse.contracts.governor import GovernorAction, GovernorDecision, GovernorDecisionRecord


class TestGovernorContract(unittest.TestCase):
    """Test canonical Governor action enum and decision payload structures."""

    def test_canonical_actions_complete(self):
        expected_actions = {
            "CONTINUE", "OPTIMIZE", "ESCALATE", "DOWNGRADE", "SWITCH", "THROTTLE", "STOP"
        }
        actual_actions = {a.value for a in GovernorAction}
        self.assertEqual(actual_actions, expected_actions)

    def test_governor_decision_defaults(self):
        decision = GovernorDecision()
        self.assertEqual(decision.action, GovernorAction.CONTINUE)
        self.assertEqual(decision.reason_codes, [])

    def test_governor_decision_record_audit(self):
        record = GovernorDecisionRecord(
            decision_id="dec_001",
            execution_id="exec_100",
            action=GovernorAction.SWITCH,
            reason_codes=["PRIMARY_PROVIDER_503_ERROR"],
            message="Switching to backup provider due to 503 service unavailable",
            evaluated_state="PROVIDER_CONSTRAINED",
            signals={"provider_error_rate": 1.0},
            effective_policy_id="pol_default"
        )
        self.assertEqual(record.action, GovernorAction.SWITCH)
        self.assertEqual(record.evaluated_state, "PROVIDER_CONSTRAINED")
        self.assertEqual(record.effective_policy_id, "pol_default")

        # Roundtrip JSON
        json_str = record.model_dump_json()
        loaded = GovernorDecisionRecord.model_validate_json(json_str)
        self.assertEqual(loaded.decision_id, "dec_001")
        self.assertEqual(loaded.action, GovernorAction.SWITCH)


if __name__ == "__main__":
    unittest.main()
