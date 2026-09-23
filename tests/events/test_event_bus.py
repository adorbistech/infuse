"""Comprehensive Unit, Integration, and Architectural Isolation Test Suite for Block 14 Event Bus."""

import inspect
import sys
import unittest
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from infuse.contracts.events import (
    ControlActionIssuedPayload,
    EventSource,
    EventType,
    ExecutionEvent,
    ProviderErrorPayload,
    StateChangedPayload,
    TokenObservedPayload,
    ToolActivityPayload,
    WebActivityPayload,
)
from infuse.contracts.execution import (
    ExecutionContext,
    ExecutionRequest,
    ExecutionRequirements,
    ExecutionStatus,
    OperationRequest,
    TaskContext,
)
from infuse.contracts.governor import GovernorAction
from infuse.contracts.state import ExecutionState
from infuse.events.bus import InMemoryEventBus
from infuse.events.collector import InMemoryEventCollector
from infuse.events.errors import (
    DuplicateEventConflictError,
    EventDeliveryError,
    EventError,
    EventValidationError,
    SubscriptionError,
)
from infuse.events.interfaces import EventHandler, IEventBus
from infuse.events.models import (
    ExecutionCompletedPayload,
    ExecutionFailedPayload,
    ExecutionStartedPayload,
)
from infuse.events.validation import validate_execution_event
from infuse.lifecycle.service import ExecutionLifecycleService
from infuse.providers.adapters.mock import MockProviderAdapter
from infuse.providers.registry import InMemoryProviderAdapterRegistry
from infuse.providers.service import ProviderAdapterService
from infuse.registry.repository import InMemoryProviderModelRegistry


class TestEventBusLayer(unittest.TestCase):
    """Test suite verifying event validation, bus operations, delivery invariants, and isolation."""

    def setUp(self) -> None:
        self.bus = InMemoryEventBus(isolate_handler_errors=True)
        self.collector = InMemoryEventCollector()

    def _sample_event(
        self,
        event_id: str = "evt_test_01",
        execution_id: str = "exec_test_01",
        event_type: EventType = EventType.EXECUTION_STARTED,
        source: EventSource = EventSource.SYSTEM,
        sequence: int = 0,
        payload: Optional[Dict[str, Any]] = None
    ) -> ExecutionEvent:
        return ExecutionEvent(
            event_id=event_id,
            execution_id=execution_id,
            type=event_type,
            source=source,
            sequence=sequence,
            payload=payload or {"status": "starting"}
        )

    # 1. Validation Tests
    def test_01_canonical_event_validation_success(self) -> None:
        """Verify compliant ExecutionEvent passes validation without mutation."""
        event = self._sample_event()
        validated = validate_execution_event(event)
        self.assertEqual(validated.event_id, "evt_test_01")
        self.assertEqual(validated.execution_id, "exec_test_01")
        self.assertEqual(validated.type, EventType.EXECUTION_STARTED)
        self.assertEqual(validated.sequence, 0)
        self.assertEqual(validated.schema_version, "1.0.0")

    def test_02_validation_rejection_empty_ids(self) -> None:
        """Verify empty event_id and execution_id are rejected."""
        with self.assertRaises(EventValidationError):
            validate_execution_event({"event_id": "", "execution_id": "exec_01", "type": "ExecutionStarted", "sequence": 0})
        with self.assertRaises(EventValidationError):
            validate_execution_event({"event_id": "evt_01", "execution_id": "  ", "type": "ExecutionStarted", "sequence": 0})

    def test_03_validation_rejection_negative_sequence(self) -> None:
        """Verify negative sequence numbers are rejected."""
        with self.assertRaises(Exception):
            ExecutionEvent(
                event_id="evt_neg",
                execution_id="exec_01",
                type=EventType.TOKEN_OBSERVED,
                sequence=-1,
                payload={}
            )
        with self.assertRaises(EventValidationError):
            validate_execution_event({
                "event_id": "evt_neg",
                "execution_id": "exec_01",
                "type": "TokenObserved",
                "sequence": -1,
                "payload": {}
            })

    def test_04_validation_rejection_unknown_event_type(self) -> None:
        """Verify invalid or uncontracted event types are rejected."""
        with self.assertRaises(Exception):
            ExecutionEvent(
                event_id="evt_bad_type",
                execution_id="exec_01",
                type="UnknownCustomType",
                sequence=0,
                payload={}
            )

    def test_05_canonical_event_taxonomy_completeness(self) -> None:
        """Verify all 14 canonical event types from Block 00 are supported."""
        canonical_types = [
            EventType.EXECUTION_STARTED,
            EventType.EXECUTION_COMPLETED,
            EventType.EXECUTION_FAILED,
            EventType.TOKEN_OBSERVED,
            EventType.USAGE_UPDATED,
            EventType.TOOL_CALLED,
            EventType.TOOL_COMPLETED,
            EventType.WEB_REQUEST,
            EventType.WEB_RESPONSE,
            EventType.RETRY_STARTED,
            EventType.PROVIDER_ERROR,
            EventType.STATE_CHANGED,
            EventType.GOVERNOR_DECISION,
            EventType.CONTROL_ACTION_ISSUED,
        ]
        self.assertEqual(len(canonical_types), 14)
        for t in canonical_types:
            evt = self._sample_event(event_id=f"evt_{t.value}", event_type=t)
            self.assertEqual(evt.type, t)

    # 2. Publication and Subscription Tests
    def test_06_event_publication_and_delivery(self) -> None:
        """Verify published event is received by subscriber."""
        self.bus.subscribe(self.collector)
        evt = self._sample_event()
        self.bus.publish(evt)

        self.assertEqual(self.collector.count, 1)
        delivered = self.collector.get_events()[0]
        self.assertEqual(delivered.event_id, "evt_test_01")
        self.assertEqual(delivered.type, EventType.EXECUTION_STARTED)

    def test_07_event_type_filtering(self) -> None:
        """Verify subscriber only receives events matching subscribed type."""
        token_collector = InMemoryEventCollector()
        self.bus.subscribe(token_collector, event_type=EventType.TOKEN_OBSERVED)

        # Publish different event types
        self.bus.publish(self._sample_event(event_id="evt_start", event_type=EventType.EXECUTION_STARTED))
        self.bus.publish(self._sample_event(event_id="evt_token", event_type=EventType.TOKEN_OBSERVED))
        self.bus.publish(self._sample_event(event_id="evt_tool", event_type=EventType.TOOL_CALLED))

        self.assertEqual(token_collector.count, 1)
        self.assertEqual(token_collector.get_events()[0].event_id, "evt_token")

    def test_08_execution_id_filtering(self) -> None:
        """Verify subscriber only receives events matching execution_id."""
        exec_collector = InMemoryEventCollector()
        self.bus.subscribe(exec_collector, execution_id="exec_target")

        self.bus.publish(self._sample_event(event_id="e1", execution_id="exec_other"))
        self.bus.publish(self._sample_event(event_id="e2", execution_id="exec_target"))

        self.assertEqual(exec_collector.count, 1)
        self.assertEqual(exec_collector.get_events()[0].event_id, "e2")

    def test_09_deterministic_delivery_order(self) -> None:
        """Verify handlers are invoked in registration order."""
        call_order = []
        def handler_a(e):
            call_order.append("A")
        def handler_b(e):
            call_order.append("B")
        def handler_c(e):
            call_order.append("C")

        self.bus.subscribe(handler_a)
        self.bus.subscribe(handler_b)
        self.bus.subscribe(handler_c)

        self.bus.publish(self._sample_event())
        self.assertEqual(call_order, ["A", "B", "C"])

    # 3. Idempotency and Duplicate Handling
    def test_10_identical_duplicate_event_is_idempotent(self) -> None:
        """Verify duplicate publication of identical event is safely idempotent."""
        self.bus.subscribe(self.collector)
        evt = self._sample_event(event_id="evt_dup_same")

        # Publish twice
        self.bus.publish(evt)
        self.bus.publish(evt)

        # Should only dispatch once
        self.assertEqual(self.collector.count, 1)

    def test_11_conflicting_duplicate_event_rejection(self) -> None:
        """Verify duplicate event_id with conflicting content raises DuplicateEventConflictError."""
        evt1 = self._sample_event(event_id="evt_conflict", sequence=0, payload={"val": 1})
        evt2 = self._sample_event(event_id="evt_conflict", sequence=1, payload={"val": 2})

        self.bus.publish(evt1)
        with self.assertRaises(DuplicateEventConflictError):
            self.bus.publish(evt2)

    # 4. Subscriber Isolation and Immutability
    def test_12_subscriber_mutation_isolation(self) -> None:
        """Verify a mutating subscriber cannot corrupt events received by other subscribers."""
        def malicious_subscriber(event: ExecutionEvent):
            event.payload["corrupted"] = True
            event.payload["nested"] = "tampered"

        collector = InMemoryEventCollector()

        self.bus.subscribe(malicious_subscriber)
        self.bus.subscribe(collector)

        evt = self._sample_event(payload={"original": "clean"})
        self.bus.publish(evt)

        received = collector.get_events()[0]
        self.assertEqual(received.payload, {"original": "clean"})
        self.assertNotIn("corrupted", received.payload)

    def test_13_subscriber_failure_isolation(self) -> None:
        """Verify subscriber exception does not crash the bus or abort subsequent subscribers."""
        def faulty_subscriber(event: ExecutionEvent):
            raise RuntimeError("Fatal subscriber crash")

        collector = InMemoryEventCollector()
        self.bus.subscribe(faulty_subscriber)
        self.bus.subscribe(collector)

        evt = self._sample_event()
        self.bus.publish(evt)

        # Subsequent subscriber still received event
        self.assertEqual(collector.count, 1)
        self.assertEqual(len(self.bus.handler_errors), 1)
        self.assertEqual(self.bus.handler_errors[0]["exception_type"], "RuntimeError")

    def test_14_subscriber_failure_propagation_mode(self) -> None:
        """Verify when error isolation is disabled, EventDeliveryError is raised."""
        strict_bus = InMemoryEventBus(isolate_handler_errors=False)
        def crashing_handler(event: ExecutionEvent):
            raise ValueError("Direct test failure")

        strict_bus.subscribe(crashing_handler)
        with self.assertRaises(EventDeliveryError):
            strict_bus.publish(self._sample_event())

    # 5. Unsubscription and Count Tests
    def test_15_unsubscription_and_count(self) -> None:
        """Verify unsubscription stops delivery and subscriber_count updates."""
        sub_id = self.bus.subscribe(self.collector, event_type=EventType.EXECUTION_STARTED)
        self.assertEqual(self.bus.subscriber_count(), 1)
        self.assertEqual(self.bus.subscriber_count(EventType.EXECUTION_STARTED), 1)

        self.bus.publish(self._sample_event(event_id="e1"))
        self.assertEqual(self.collector.count, 1)

        unsub_res = self.bus.unsubscribe(sub_id)
        self.assertTrue(unsub_res)
        self.assertEqual(self.bus.subscriber_count(), 0)

        # Publishing again should not reach collector
        self.bus.publish(self._sample_event(event_id="e2"))
        self.assertEqual(self.collector.count, 1)

    # 6. Lifecycle Service Integration Tests
    def test_16_lifecycle_publishes_started_and_completed_events(self) -> None:
        """Verify ExecutionLifecycleService publishes ExecutionStarted and ExecutionCompleted."""
        collector = InMemoryEventCollector()
        self.bus.subscribe(collector)

        service = ExecutionLifecycleService(event_bus=self.bus)
        req = ExecutionRequest(
            request_id="req_ev_01",
            task=TaskContext(task_id="task_ev_01", description="Lifecycle event test"),
            request=OperationRequest(messages=[{"role": "user", "content": "Hello event bus"}]),
            execution_context=ExecutionContext(session_id="sess_ev_01", workflow_id="wf_ev_01")
        )

        result = service.execute(req, execution_id="exec_ev_01")
        self.assertEqual(result.status, ExecutionStatus.COMPLETED)

        # Verify events
        events = collector.get_events()
        self.assertEqual(len(events), 2)

        start_evt = events[0]
        self.assertEqual(start_evt.type, EventType.EXECUTION_STARTED)
        self.assertEqual(start_evt.execution_id, "exec_ev_01")
        self.assertEqual(start_evt.sequence, 0)
        self.assertEqual(start_evt.payload["request_id"], "req_ev_01")
        self.assertEqual(start_evt.payload["session_id"], "sess_ev_01")

        comp_evt = events[1]
        self.assertEqual(comp_evt.type, EventType.EXECUTION_COMPLETED)
        self.assertEqual(comp_evt.execution_id, "exec_ev_01")
        self.assertEqual(comp_evt.sequence, 1)
        self.assertEqual(comp_evt.payload["status"], "COMPLETED")
        self.assertGreater(comp_evt.payload["duration_ms"], 0.0)
        self.assertEqual(comp_evt.payload["total_tokens"], 195)

    def test_17_lifecycle_publishes_failed_event_on_provider_error(self) -> None:
        """Verify ExecutionLifecycleService publishes ExecutionFailed upon provider failure."""
        collector = InMemoryEventCollector()
        self.bus.subscribe(collector)

        def raise_err(r):
            class ProviderOverloaded(Exception):
                status_code = 503
            return ProviderOverloaded("Service unavailable")

        err_adapter = MockProviderAdapter(
            provider_id="openai",
            supported_models=["gpt-4o"],
            error_generator=raise_err
        )
        adapter_reg = InMemoryProviderAdapterRegistry()
        adapter_reg.register(err_adapter)
        adapter_svc = ProviderAdapterService(registry=adapter_reg)

        service = ExecutionLifecycleService(
            adapter_service=adapter_svc,
            event_bus=self.bus
        )
        req = ExecutionRequest(
            request_id="req_fail_ev",
            task=TaskContext(task_id="task_fail_ev"),
            request=OperationRequest(messages=[{"role": "user", "content": "Trigger failure"}]),
            requirements=ExecutionRequirements(preferred_models=["gpt-4o"])
        )

        result = service.execute(req, execution_id="exec_fail_ev_01")
        self.assertEqual(result.status, ExecutionStatus.FAILED)

        # Check published events: ExecutionStarted then ExecutionFailed
        events = collector.get_events()
        self.assertGreaterEqual(len(events), 2)
        failed_evt = events[-1]
        self.assertEqual(failed_evt.type, EventType.EXECUTION_FAILED)
        self.assertEqual(failed_evt.execution_id, "exec_fail_ev_01")
        self.assertEqual(failed_evt.payload["status"], "FAILED")
        self.assertIn("Service unavailable", failed_evt.payload["error_message"])

    def test_18_lifecycle_execution_safe_if_event_bus_fails(self) -> None:
        """Verify lifecycle execution succeeds even if event publication throws."""
        class BrokenBus(IEventBus):
            def publish(self, event):
                raise RuntimeError("Broker connection died")
            def subscribe(self, handler, event_type=None, execution_id=None):
                return "sub"
            def unsubscribe(self, subscription_id):
                return True
            def subscriber_count(self, event_type=None):
                return 0
            def clear(self):
                pass
            def close(self):
                pass

        service = ExecutionLifecycleService(event_bus=BrokenBus())
        req = ExecutionRequest(
            request_id="req_broken_bus",
            task=TaskContext(task_id="task_broken_bus"),
            request=OperationRequest(messages=[{"role": "user", "content": "Test safety"}])
        )
        # Should not raise exception
        result = service.execute(req, execution_id="exec_safe_01")
        self.assertEqual(result.status, ExecutionStatus.COMPLETED)

    # 7. Architectural Isolation Tests
    def test_19_zero_database_imports_in_events_package(self) -> None:
        """Verify events package contains zero database library imports."""
        import infuse.events
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.events")]

        forbidden = ["sqlite3", "psycopg2", "asyncpg", "sqlalchemy", "redis", "qdrant_client", "motor", "pymongo"]
        for mod in modules:
            src = inspect.getsource(mod)
            for f in forbidden:
                self.assertNotIn(f"import {f}", src)
                self.assertNotIn(f"from {f}", src)

    def test_20_zero_provider_and_broker_sdk_imports(self) -> None:
        """Verify events package contains zero real provider or broker SDK imports."""
        import infuse.events
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.events")]

        forbidden = [
            "openai", "anthropic", "google.generativeai", "cohere", "langchain", "crewai", "autogen",
            "kafka", "pika", "nats", "redis", "aioredis", "celery", "kombu"
        ]
        for mod in modules:
            src = inspect.getsource(mod)
            for f in forbidden:
                self.assertNotIn(f"import {f}", src)
                self.assertNotIn(f"from {f}", src)

    def test_21_zero_governor_or_economics_logic_in_events(self) -> None:
        """Verify events package contains zero Governor decisions, pricing calculations, or health scoring."""
        import infuse.events
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.events")]

        forbidden_patterns = [
            "calculate_cost",
            "calculate_price",
            "calculate_margin",
            "issue_action",
            "apply_governance",
            "score_health",
            "detect_runaway",
            "detect_anomaly"
        ]
        for mod in modules:
            src = inspect.getsource(mod)
            for p in forbidden_patterns:
                self.assertNotIn(p, src)


if __name__ == "__main__":
    unittest.main()
