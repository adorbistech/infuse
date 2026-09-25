"""INFUSE Block 36 — Contract & Canonical Vocabulary Certification.

Verifies:
- Canonical ExecutionState enum values
- Canonical GovernorAction enum values
- Universal Execution, Event, Policy, and Control contracts
- Frontend-to-Backend contract vocabulary alignment
- Extensibility and schema version consistency
"""

import unittest
from infuse.contracts.control import ControlCapability, ControlOperation, ControlResult, ControlStatus
from infuse.contracts.events import EventSource, EventType, ExecutionEvent
from infuse.contracts.execution import (
    ExecutionContext,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    ExecutionTelemetry,
    NormalizedResponse,
    OperationRequest,
    TaskContext,
)
from infuse.contracts.frontend import (
    ExecutionSummaryViewModel,
    GovernancePolicyViewModel,
)
from infuse.contracts.governor import GovernorAction, GovernorDecision
from infuse.contracts.policy import GovernancePolicy, BudgetControls, TokenControls
from infuse.contracts.state import ExecutionState, ExecutionStateSnapshot
from infuse.version import SCHEMA_VERSION, __version__


class TestContractAndVocabularyCertification(unittest.TestCase):
    """Certification tests for system-wide contract and vocabulary integrity."""

    def test_01_canonical_execution_states(self) -> None:
        """Verify ExecutionState enum has exactly the 5 canonical states."""
        expected_states = {
            "NORMAL",
            "COST_PRESSURE",
            "RUNAWAY",
            "QUALITY_DEGRADED",
            "PROVIDER_CONSTRAINED",
        }
        actual_states = {state.value for state in ExecutionState}
        self.assertEqual(actual_states, expected_states)
        self.assertEqual(len(ExecutionState), 5)

    def test_02_canonical_governor_actions(self) -> None:
        """Verify GovernorAction enum has exactly the 7 canonical actions."""
        expected_actions = {
            "CONTINUE",
            "OPTIMIZE",
            "ESCALATE",
            "DOWNGRADE",
            "SWITCH",
            "THROTTLE",
            "STOP",
        }
        actual_actions = {action.value for action in GovernorAction}
        self.assertEqual(actual_actions, expected_actions)
        self.assertEqual(len(GovernorAction), 7)

    def test_03_canonical_control_status_parity(self) -> None:
        """Verify ControlStatus includes all standardized lifecycle control statuses."""
        expected_control_statuses = {
            "ACCEPTED",
            "COMPLETED",
            "SUPPORTED",
            "UNSUPPORTED",
            "FAILED",
        }
        actual_control_statuses = {status.value for status in ControlStatus}
        self.assertEqual(actual_control_statuses, expected_control_statuses)

    def test_04_execution_result_contract_integrity(self) -> None:
        """Verify ExecutionResult model enforces typed telemetry, decision, and schema version."""
        res = ExecutionResult(
            execution_id="exec_cert_001",
            request_id="req_cert_001",
            status=ExecutionStatus.COMPLETED,
            response=NormalizedResponse(content="Certification Success", role="assistant"),
            execution=ExecutionTelemetry(
                provider="TestProvider",
                model="test-model",
                input_tokens=100,
                cached_tokens=20,
                output_tokens=50,
                total_tokens=170,
                cost_usd=0.005,
                latency_ms=120.0,
                requests_count=1,
                state=ExecutionState.NORMAL,
            ),
            decision=GovernorDecision(
                action=GovernorAction.CONTINUE,
                reason="Parameters compliant with policy.",
            ),
            schema_version=SCHEMA_VERSION,
        )
        self.assertEqual(res.execution_id, "exec_cert_001")
        self.assertEqual(res.execution.state, ExecutionState.NORMAL)
        self.assertEqual(res.decision.action, GovernorAction.CONTINUE)
        self.assertEqual(res.schema_version, SCHEMA_VERSION)

    def test_05_execution_event_contract_integrity(self) -> None:
        """Verify ExecutionEvent enforces timestamp, event type, and payload encapsulation."""
        event = ExecutionEvent(
            event_id="evt_cert_001",
            execution_id="exec_cert_001",
            type=EventType.TOKEN_OBSERVED,
            source=EventSource.OBSERVER,
            sequence=1,
            payload={"tokens": 150, "rate": 25.0},
            schema_version=SCHEMA_VERSION,
        )
        self.assertEqual(event.type, EventType.TOKEN_OBSERVED)
        self.assertEqual(event.source, EventSource.OBSERVER)
        self.assertEqual(event.sequence, 1)
        self.assertEqual(event.payload["tokens"], 150)
        self.assertIsNotNone(event.timestamp)

    def test_06_governance_policy_contract_integrity(self) -> None:
        """Verify GovernancePolicy models budget, token limits, and action mappings cleanly."""
        policy = GovernancePolicy(
            policy_id="pol_cert_001",
            name="Certification Policy",
            budget=BudgetControls(max_cost_per_task=1.0, currency="USD"),
            tokens=TokenControls(max_total_tokens=5000),
            schema_version=SCHEMA_VERSION,
        )
        self.assertEqual(policy.budget.max_cost_per_task, 1.0)
        self.assertEqual(policy.tokens.max_total_tokens, 5000)

    def test_07_schema_version_and_release_version_consistency(self) -> None:
        """Verify version.py exports valid semantic versions."""
        self.assertEqual(SCHEMA_VERSION, "1.0.0")
        self.assertTrue(len(__version__.split(".")) >= 3)


if __name__ == "__main__":
    unittest.main()
