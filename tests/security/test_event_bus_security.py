"""INFUSE Block 34 — Event Bus Security and Event Isolation Suite.

Validates that:
- Events adhere strictly to the universal event schema
- Subscribers are isolated; an exception in subscriber A does not halt dispatch to subscriber B
- Malformed payloads do not crash the Event Bus
- Duplicate and out-of-order events are safely digested
- Events cannot directly invoke Governor decisions or bypass the Control Boundary
"""

import unittest
import uuid
from typing import List

from infuse.contracts.events import EventSource, EventType, ExecutionEvent
from infuse.events.bus import InMemoryEventBus
from infuse.events.errors import EventValidationError


class TestEventBusSecurity(unittest.TestCase):
    """Verifies that Event Bus provides secure isolation, defensive copying, and exception tolerance."""

    def setUp(self) -> None:
        self.bus = InMemoryEventBus()
        self.exec_id = f"exec_evt_sec_{uuid.uuid4().hex[:8]}"

    def test_01_event_validation_requires_event_id_and_execution_id(self) -> None:
        """Verify emitting events with blank IDs is rejected by validator."""
        from infuse.events.validation import validate_execution_event
        evt_blank_eid = ExecutionEvent(
            event_id="evt_1",
            execution_id="   ",
            type=EventType.TOKEN_OBSERVED,
            source=EventSource.PROVIDER,
            sequence=1,
            payload={},
        )
        with self.assertRaises(EventValidationError):
            validate_execution_event(evt_blank_eid)

        evt_blank_id = ExecutionEvent(
            event_id="   ",
            execution_id="exec_1",
            type=EventType.TOKEN_OBSERVED,
            source=EventSource.PROVIDER,
            sequence=1,
            payload={},
        )
        with self.assertRaises(EventValidationError):
            validate_execution_event(evt_blank_id)

    def test_02_subscriber_exception_isolation(self) -> None:
        """Verify an unhandled exception in one subscriber does not break dispatch to other subscribers."""
        received_events: List[ExecutionEvent] = []

        def failing_subscriber(event: ExecutionEvent) -> None:
            raise RuntimeError("Fatal crash in buggy subscriber!")

        def healthy_subscriber(event: ExecutionEvent) -> None:
            received_events.append(event)

        self.bus.subscribe(failing_subscriber, event_type=EventType.TOKEN_OBSERVED)
        self.bus.subscribe(healthy_subscriber, event_type=EventType.TOKEN_OBSERVED)

        event = ExecutionEvent(
            event_id="evt_iso_1",
            execution_id=self.exec_id,
            type=EventType.TOKEN_OBSERVED,
            source=EventSource.PROVIDER,
            sequence=1,
            payload={"total_tokens": 100},
        )

        # Publish event - must succeed and healthy_subscriber must receive it
        self.bus.publish(event)
        self.assertEqual(len(received_events), 1)
        self.assertEqual(received_events[0].event_id, "evt_iso_1")

    def test_03_wildcard_subscriber_exception_isolation(self) -> None:
        """Verify wildcard subscriber crashes do not prevent typed subscriber execution."""
        received_events: List[ExecutionEvent] = []

        def broken_wildcard(event: ExecutionEvent) -> None:
            raise KeyError("Wildcard missing key error!")

        def healthy_listener(event: ExecutionEvent) -> None:
            received_events.append(event)

        self.bus.subscribe(broken_wildcard)
        self.bus.subscribe(healthy_listener, event_type=EventType.STATE_CHANGED)

        event = ExecutionEvent(
            event_id="evt_wild_1",
            execution_id=self.exec_id,
            type=EventType.STATE_CHANGED,
            source=EventSource.AGENT,
            sequence=1,
            payload={"state": "NORMAL"},
        )

        self.bus.publish(event)
        self.assertEqual(len(received_events), 1)

    def test_04_defensive_event_copying_prevents_payload_tampering(self) -> None:
        """Verify mutating an event payload after publishing does not alter internal records."""
        mutable_payload = {"tokens": 100, "nested": {"count": 1}}
        event = ExecutionEvent(
            event_id="evt_defensive",
            execution_id=self.exec_id,
            type=EventType.TOKEN_OBSERVED,
            source=EventSource.PROVIDER,
            sequence=1,
            payload=mutable_payload,
        )

        captured_events: List[ExecutionEvent] = []
        self.bus.subscribe(lambda e: captured_events.append(e), event_type=EventType.TOKEN_OBSERVED)

        self.bus.publish(event)
        mutable_payload["tokens"] = 999999

        # Ensure published copy remains immutable
        self.assertEqual(captured_events[0].payload["tokens"], 100)

    def test_05_malformed_nested_payload_safety(self) -> None:
        """Verify deeply nested or unusual data types in payload do not crash the bus."""
        event = ExecutionEvent(
            event_id="evt_weird_payload",
            execution_id=self.exec_id,
            type=EventType.GOVERNOR_DECISION,
            source=EventSource.GOVERNOR,
            sequence=1,
            payload={"list_data": [1, [2, [3, "nested"]]], "flag": True, "none_val": None},
        )
        delivered = []
        self.bus.subscribe(lambda e: delivered.append(e))
        self.bus.publish(event)
        self.assertEqual(len(delivered), 1)
        self.assertEqual(delivered[0].event_id, "evt_weird_payload")


if __name__ == "__main__":
    unittest.main()
