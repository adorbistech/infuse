"""Tests for Execution Event Contract."""

import unittest
from infuse.contracts.events import (
    EventType,
    EventSource,
    ExecutionEvent,
    TokenObservedPayload,
    ToolActivityPayload,
    ProviderErrorPayload,
    StateChangedPayload,
    ControlActionIssuedPayload,
)
from infuse.contracts.governor import GovernorAction
from infuse.contracts.state import ExecutionState


class TestEventContract(unittest.TestCase):
    """Test immutability, structure, taxonomy, and typing of execution events."""

    def test_canonical_event_creation(self):
        event = ExecutionEvent(
            event_id="evt_001",
            execution_id="exec_001",
            type=EventType.EXECUTION_STARTED,
            source=EventSource.AGENT,
            sequence=0,
            payload={"task_id": "task_101", "agent": "opencode"}
        )
        self.assertEqual(event.event_id, "evt_001")
        self.assertEqual(event.type, EventType.EXECUTION_STARTED)
        self.assertEqual(event.sequence, 0)
        self.assertEqual(event.schema_version, "1.0.0")

    def test_typed_token_observed_payload(self):
        payload = TokenObservedPayload(
            input_tokens=1000,
            output_tokens=250,
            cached_tokens=200,
            total_tokens=1250,
            is_authoritative=True,
            provider="anthropic",
            model="claude-sonnet"
        )
        event = ExecutionEvent(
            event_id="evt_002",
            execution_id="exec_001",
            type=EventType.TOKEN_OBSERVED,
            source=EventSource.PROVIDER,
            sequence=1,
            payload=payload.model_dump()
        )
        self.assertEqual(event.type, EventType.TOKEN_OBSERVED)
        self.assertEqual(event.payload["total_tokens"], 1250)
        self.assertTrue(event.payload["is_authoritative"])

    def test_typed_tool_activity_payload(self):
        payload = ToolActivityPayload(
            tool_name="read_file",
            call_id="call_99",
            arguments={"path": "/src/auth.py"},
            success=True,
            duration_ms=45.2
        )
        event = ExecutionEvent(
            event_id="evt_003",
            execution_id="exec_001",
            type=EventType.TOOL_COMPLETED,
            source=EventSource.AGENT,
            sequence=2,
            payload=payload.model_dump()
        )
        self.assertEqual(event.payload["tool_name"], "read_file")
        self.assertTrue(event.payload["success"])

    def test_typed_provider_error_payload(self):
        payload = ProviderErrorPayload(
            provider="openai",
            error_type="RateLimitError",
            message="Rate limit exceeded",
            is_retryable=True,
            http_status=429
        )
        event = ExecutionEvent(
            event_id="evt_004",
            execution_id="exec_001",
            type=EventType.PROVIDER_ERROR,
            source=EventSource.PROVIDER,
            sequence=3,
            payload=payload.model_dump()
        )
        self.assertTrue(event.payload["is_retryable"])
        self.assertEqual(event.payload["http_status"], 429)

    def test_state_changed_event(self):
        payload = StateChangedPayload(
            previous_state=ExecutionState.NORMAL,
            new_state=ExecutionState.COST_PRESSURE,
            reason_codes=["BUDGET_THRESHOLD_80_PERCENT"]
        )
        event = ExecutionEvent(
            event_id="evt_005",
            execution_id="exec_001",
            type=EventType.STATE_CHANGED,
            source=EventSource.OBSERVER,
            sequence=4,
            payload=payload.model_dump()
        )
        self.assertEqual(event.payload["new_state"], ExecutionState.COST_PRESSURE)

    def test_control_action_issued_event(self):
        payload = ControlActionIssuedPayload(
            action=GovernorAction.OPTIMIZE,
            operation_id="op_123",
            params={"compress_context": True},
            target_boundary="opencode-agent-boundary"
        )
        event = ExecutionEvent(
            event_id="evt_006",
            execution_id="exec_001",
            type=EventType.CONTROL_ACTION_ISSUED,
            source=EventSource.GOVERNOR,
            sequence=5,
            payload=payload.model_dump()
        )
        self.assertEqual(event.payload["action"], GovernorAction.OPTIMIZE)


if __name__ == "__main__":
    unittest.main()
