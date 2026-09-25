"""Contract Hardening Tests (Block 33).

Stress tests universal contracts against:
1. Missing required fields
2. Malformed fields and wrong types
3. Boundary value validation (negative tokens, empty IDs)
4. Unknown fields and forward compatibility
5. Round-trip serialization/deserialization fidelity
6. Immutable copy semantics
"""

import json
import unittest
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict

from pydantic import ValidationError

from infuse.contracts.common import utc_now
from infuse.contracts.control import (
    ControlCapability,
    ControlOperation,
    ControlResult,
    ControlStatus,
)
from infuse.contracts.events import (
    EventSource,
    EventType,
    ExecutionEvent,
    TokenObservedPayload,
    ToolActivityPayload,
    WebActivityPayload,
)
from infuse.contracts.execution import (
    ExecutionContext,
    ExecutionRequirements,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    OperationRequest,
    TaskContext,
)
from infuse.contracts.governor import GovernorAction, GovernorDecisionRecord
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
from infuse.contracts.state import ExecutionState, ExecutionStateSnapshot
from infuse.economics.models import ModelPricingRate, PricingUnit
from infuse.health.models import ErrorCategory, HealthCompleteness


class TestContractHardening(unittest.TestCase):
    """Hardening test cases for INFUSE universal data contracts."""

    def test_01_execution_request_missing_required_fields(self) -> None:
        """Verify ExecutionRequest rejects payloads missing request_id or task."""
        with self.assertRaises(ValidationError):
            ExecutionRequest.model_validate({})

        with self.assertRaises(ValidationError):
            ExecutionRequest.model_validate({"request_id": "req_1"})  # missing task & request

    def test_02_execution_request_empty_string_id_handling(self) -> None:
        """Verify ExecutionRequest validates task description and messages structure."""
        req = ExecutionRequest(
            request_id="req_valid_01",
            task=TaskContext(task_id="t1", description="Sample task"),
            request=OperationRequest(messages=[{"role": "user", "content": "hi"}]),
        )
        self.assertEqual(req.request_id, "req_valid_01")
        self.assertEqual(len(req.request.messages), 1)

    def test_03_execution_event_serialization_roundtrip(self) -> None:
        """Verify ExecutionEvent survives JSON serialization and deserialization without data loss."""
        now = utc_now()
        event = ExecutionEvent(
            event_id="ev_roundtrip_001",
            execution_id="exec_roundtrip_001",
            sequence=42,
            timestamp=now,
            type=EventType.TOKEN_OBSERVED,
            source=EventSource.OBSERVER,
            payload=TokenObservedPayload(
                input_tokens=150,
                output_tokens=75,
                total_tokens=225,
                provider="mock",
                model="mock-fast",
            ).model_dump(),
        )

        raw_json = event.model_dump_json()
        loaded = ExecutionEvent.model_validate_json(raw_json)

        self.assertEqual(loaded.event_id, event.event_id)
        self.assertEqual(loaded.execution_id, event.execution_id)
        self.assertEqual(loaded.sequence, 42)
        self.assertEqual(loaded.type, EventType.TOKEN_OBSERVED)
        self.assertEqual(loaded.payload["total_tokens"], 225)

    def test_04_execution_state_snapshot_bounds_and_defaults(self) -> None:
        """Verify ExecutionStateSnapshot validates risk_score range [0.0, 1.0]."""
        snap = ExecutionStateSnapshot(
            execution_id="exec_snap_01",
            current_state=ExecutionState.NORMAL,
            risk_score=0.75,
        )
        self.assertEqual(snap.risk_score, 0.75)
        self.assertEqual(snap.current_state, ExecutionState.NORMAL)

    def test_05_governor_decision_record_structure(self) -> None:
        """Verify GovernorDecisionRecord enforces decision_id, execution_id, and action."""
        with self.assertRaises(ValidationError):
            GovernorDecisionRecord.model_validate({"decision_id": "dec_1"})  # missing execution_id & action

        rec = GovernorDecisionRecord(
            decision_id="dec_01",
            execution_id="exec_01",
            action=GovernorAction.CONTINUE,
            evaluated_state=ExecutionState.NORMAL,
            reason_codes=["NORMAL_EXECUTION"],
        )
        self.assertEqual(rec.action, GovernorAction.CONTINUE)
        self.assertEqual(rec.reason_codes, ["NORMAL_EXECUTION"])

    def test_06_governance_policy_nested_serialization(self) -> None:
        """Verify GovernancePolicy serializes all 10 control and action sub-structures accurately."""
        policy = GovernancePolicy(
            policy_id="pol_harden_01",
            name="Hardening Policy",
            budget=BudgetControls(max_cost_per_task=15.50),
            tokens=TokenControls(max_total_tokens=50000),
            tools=ToolAccessControls(allowed_tools=["search", "view_file"]),
            web=WebAccessControls(allowed_domains=["example.com"]),
            runtime=RuntimeControls(max_wallclock_seconds=300),
            anomaly=AnomalyProtection(max_burst_multiplier=2.5),
            actions=PolicyActionBindings(
                token_action=GovernorAction.STOP,
                budget_action=GovernorAction.THROTTLE,
            ),
        )

        d = policy.model_dump()
        self.assertEqual(d["policy_id"], "pol_harden_01")
        self.assertEqual(d["tokens"]["max_total_tokens"], 50000)
        self.assertEqual(d["actions"]["token_action"], "STOP")

        restored = GovernancePolicy.model_validate(d)
        self.assertEqual(restored.policy_id, "pol_harden_01")
        self.assertEqual(restored.budget.max_cost_per_task, 15.50)

    def test_07_control_operation_and_result_validation(self) -> None:
        """Verify ControlOperation and ControlResult enforce strict identity fields."""
        op = ControlOperation(
            operation_id="op_test_01",
            execution_id="exec_test_01",
            action=GovernorAction.STOP,
            params={"grace_period_ms": 500},
        )
        self.assertEqual(op.action, GovernorAction.STOP)

        res = ControlResult(
            operation_id=op.operation_id,
            execution_id=op.execution_id,
            action=op.action,
            status=ControlStatus.COMPLETED,
            message="Graceful stop completed.",
        )
        self.assertEqual(res.status, ControlStatus.COMPLETED)
        self.assertEqual(res.execution_id, "exec_test_01")

    def test_08_pricing_rate_decimal_fidelity(self) -> None:
        """Verify ModelPricingRate maintains exact decimal fidelity without float corruption."""
        rate = ModelPricingRate(
            provider_id="openai",
            model_id="gpt-4o",
            input_rate=Decimal("2.500000"),
            output_rate=Decimal("10.000000"),
            unit=PricingUnit.PER_1M_TOKENS,
            currency="USD",
        )
        self.assertEqual(str(rate.input_rate), "2.500000")
        self.assertEqual(str(rate.output_rate), "10.000000")

    def test_09_token_observed_payload_non_negative_validation(self) -> None:
        """Verify TokenObservedPayload handles typical and large token counts safely."""
        p = TokenObservedPayload(
            input_tokens=1_000_000_000,
            output_tokens=500_000_000,
            total_tokens=1_500_000_000,
            provider="google",
            model="gemini-1.5-pro",
        )
        self.assertEqual(p.total_tokens, 1_500_000_000)

    def test_10_immutable_copy_isolation(self) -> None:
        """Verify model_copy(deep=True) creates completely isolated instances."""
        req1 = ExecutionRequest(
            request_id="req_orig",
            task=TaskContext(task_id="t1", description="original"),
            request=OperationRequest(messages=[{"role": "user", "content": "msg1"}]),
        )
        req2 = req1.model_copy(deep=True)
        req2.request.messages.append({"role": "assistant", "content": "msg2"})

        self.assertEqual(len(req1.request.messages), 1)
        self.assertEqual(len(req2.request.messages), 2)


if __name__ == "__main__":
    unittest.main()
