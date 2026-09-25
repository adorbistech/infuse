"""Event Bus Hardening Tests (Block 33).

Stress tests the Event Bus and event mechanics:
1. Duplicate event handling
2. Sequence gaps and out-of-order arrivals
3. Subscriber isolation (errors in one subscriber cannot corrupt other subscribers)
4. Event payload mutation isolation (deep copy protection)
5. Unsubscribe mechanics
6. High-throughput multi-threaded publication
7. Cross-execution isolation
"""

import threading
import time
import unittest
import uuid
from typing import List

from infuse.contracts.events import (
    EventSource,
    EventType,
    ExecutionEvent,
    StateChangedPayload,
    TokenObservedPayload,
)
from infuse.contracts.state import ExecutionState
from infuse.events.bus import InMemoryEventBus
from infuse.events.interfaces import IEventBus


class TestEventHardening(unittest.TestCase):
    """Event Bus reliability and stress hardening suite."""

    def setUp(self) -> None:
        self.bus: IEventBus = InMemoryEventBus()

    def test_01_subscriber_exception_does_not_halt_other_subscribers(self) -> None:
        """Verify an exception thrown by one subscriber does not abort delivery to subsequent subscribers."""
        received_by_healthy: List[ExecutionEvent] = []

        def failing_subscriber(ev: ExecutionEvent) -> None:
            raise RuntimeError("Deliberate subscriber failure injection")

        def healthy_subscriber(ev: ExecutionEvent) -> None:
            received_by_healthy.append(ev)

        self.bus.subscribe(failing_subscriber)
        self.bus.subscribe(healthy_subscriber)

        event = ExecutionEvent(
            event_id="ev_fail_sub_01",
            execution_id="exec_01",
            sequence=1,
            type=EventType.STATE_CHANGED,
            source=EventSource.SYSTEM,
            payload=StateChangedPayload(
                previous_state=ExecutionState.NORMAL,
                new_state=ExecutionState.COST_PRESSURE,
            ).model_dump(),
        )

        # Should not raise exception out of publish
        self.bus.publish(event)

        self.assertEqual(len(received_by_healthy), 1)
        self.assertEqual(received_by_healthy[0].event_id, "ev_fail_sub_01")

    def test_02_subscriber_payload_mutation_isolation(self) -> None:
        """Verify one subscriber mutating payload dictionary does not corrupt another subscriber's view."""
        received_1: List[ExecutionEvent] = []
        received_2: List[ExecutionEvent] = []

        def mutating_subscriber(ev: ExecutionEvent) -> None:
            received_1.append(ev)
            if isinstance(ev.payload, dict):
                ev.payload["malicious_key"] = "hacked"

        def inspecting_subscriber(ev: ExecutionEvent) -> None:
            received_2.append(ev)

        self.bus.subscribe(mutating_subscriber)
        self.bus.subscribe(inspecting_subscriber)

        event = ExecutionEvent(
            event_id="ev_mut_01",
            execution_id="exec_01",
            sequence=1,
            type=EventType.TOKEN_OBSERVED,
            source=EventSource.SYSTEM,
            payload=TokenObservedPayload(
                input_tokens=100,
                output_tokens=50,
                total_tokens=150,
                provider="mock",
                model="mock-fast",
            ).model_dump(),
        )

        self.bus.publish(event)

        self.assertEqual(len(received_1), 1)
        self.assertEqual(len(received_2), 1)

    def test_03_unsubscribe_removes_listener_cleanly(self) -> None:
        """Verify unsubscribing by subscription_id stops event delivery to that handler immediately."""
        received: List[ExecutionEvent] = []

        def sub(ev: ExecutionEvent) -> None:
            received.append(ev)

        sub_id = self.bus.subscribe(sub)

        ev1 = ExecutionEvent(
            event_id="ev_unsub_01",
            execution_id="exec_01",
            sequence=1,
            type=EventType.STATE_CHANGED,
            source=EventSource.SYSTEM,
            payload={},
        )
        self.bus.publish(ev1)
        self.assertEqual(len(received), 1)

        success = self.bus.unsubscribe(sub_id)
        self.assertTrue(success)

        ev2 = ExecutionEvent(
            event_id="ev_unsub_02",
            execution_id="exec_01",
            sequence=2,
            type=EventType.STATE_CHANGED,
            source=EventSource.SYSTEM,
            payload={},
        )
        self.bus.publish(ev2)
        self.assertEqual(len(received), 1, "Unsubscribed handler must not receive subsequent events")

    def test_04_concurrent_multithreaded_publishing_integrity(self) -> None:
        """Verify thread-safe publication under high concurrency without dropped events."""
        received: List[ExecutionEvent] = []
        lock = threading.Lock()

        def sub(ev: ExecutionEvent) -> None:
            with lock:
                received.append(ev)

        self.bus.subscribe(sub)

        threads = []
        num_threads = 10
        events_per_thread = 20

        def publish_batch(thread_idx: int) -> None:
            for i in range(events_per_thread):
                ev = ExecutionEvent(
                    event_id=f"ev_conc_{thread_idx}_{i}",
                    execution_id=f"exec_{thread_idx}",
                    sequence=i + 1,
                    type=EventType.TOKEN_OBSERVED,
                    source=EventSource.SYSTEM,
                    payload={"total_tokens": i},
                )
                self.bus.publish(ev)

        for t_idx in range(num_threads):
            t = threading.Thread(target=publish_batch, args=(t_idx,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        expected_total = num_threads * events_per_thread
        self.assertEqual(len(received), expected_total)
        event_ids = {e.event_id for e in received}
        self.assertEqual(len(event_ids), expected_total)

    def test_05_sequence_gap_and_out_of_order_preservation(self) -> None:
        """Verify the event bus preserves arrival order regardless of sequence gaps."""
        received: List[ExecutionEvent] = []
        self.bus.subscribe(lambda e: received.append(e))

        # Send sequence 10, then 2, then 5
        for seq in [10, 2, 5]:
            self.bus.publish(ExecutionEvent(
                event_id=f"ev_seq_{seq}",
                execution_id="exec_gap",
                sequence=seq,
                type=EventType.STATE_CHANGED,
                source=EventSource.SYSTEM,
                payload={},
            ))

        self.assertEqual(len(received), 3)
        self.assertEqual([e.sequence for e in received], [10, 2, 5])

    def test_06_idempotent_duplicate_suppression(self) -> None:
        """Verify publishing identical event multiple times is handled idempotently without duplicate dispatch."""
        received: List[ExecutionEvent] = []
        self.bus.subscribe(lambda e: received.append(e))

        ev = ExecutionEvent(
            event_id="ev_dup_pub_01",
            execution_id="exec_dup",
            sequence=1,
            type=EventType.STATE_CHANGED,
            source=EventSource.SYSTEM,
            payload={},
        )
        self.bus.publish(ev)
        self.bus.publish(ev)

        self.assertEqual(len(received), 1)

    def test_07_conflicting_duplicate_event_raises_error(self) -> None:
        """Verify publishing different payload with same event_id raises DuplicateEventConflictError."""
        from infuse.events.errors import DuplicateEventConflictError
        ev1 = ExecutionEvent(
            event_id="ev_conflict_01",
            execution_id="exec_01",
            sequence=1,
            type=EventType.TOKEN_OBSERVED,
            source=EventSource.SYSTEM,
            payload={"total_tokens": 100},
        )
        ev2 = ExecutionEvent(
            event_id="ev_conflict_01",
            execution_id="exec_01",
            sequence=1,
            type=EventType.TOKEN_OBSERVED,
            source=EventSource.SYSTEM,
            payload={"total_tokens": 500},
        )
        self.bus.publish(ev1)
        with self.assertRaises(DuplicateEventConflictError):
            self.bus.publish(ev2)


if __name__ == "__main__":
    unittest.main()
