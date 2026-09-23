"""Authoritative In-Memory Deterministic Event Bus for INFUSE."""

import threading
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

from infuse.contracts.events import EventType, ExecutionEvent
from infuse.events.errors import (
    DuplicateEventConflictError,
    EventDeliveryError,
    EventValidationError,
    SubscriptionError,
)
from infuse.events.interfaces import EventHandler, IEventBus
from infuse.events.validation import validate_execution_event


@dataclass
class _Subscription:
    subscription_id: str
    handler: EventHandler
    event_type: Optional[str]
    execution_id: Optional[str]


class InMemoryEventBus(IEventBus):
    """Deterministic in-process Event Bus with strict validation, isolation, and idempotency."""

    def __init__(self, isolate_handler_errors: bool = True) -> None:
        self._isolate_handler_errors = isolate_handler_errors
        self._subscriptions: Dict[str, _Subscription] = {}
        # Tracks published events for idempotency & conflict detection: {event_id: ExecutionEvent}
        self._published_events: Dict[str, ExecutionEvent] = {}
        # Tracks last observed sequence per execution_id: {execution_id: int}
        self._execution_sequences: Dict[str, int] = {}
        # Records subscriber errors for auditing / assertions
        self._handler_errors: List[Dict[str, Any]] = []
        self._lock = threading.RLock()
        self._is_closed = False

    def publish(self, event: ExecutionEvent) -> None:
        """Validate, verify idempotency, and dispatch event to all matching subscribers."""
        with self._lock:
            if self._is_closed:
                raise EventDeliveryError("Event bus is closed; cannot publish events.")

            # 1. Canonical contract and structural validation
            validated_event = validate_execution_event(event)
            eid = validated_event.event_id
            exec_id = validated_event.execution_id

            # 2. Duplicate ID & Conflict detection
            if eid in self._published_events:
                existing = self._published_events[eid]
                # Compare canonical representations
                if existing.model_dump() == validated_event.model_dump():
                    # Idempotent duplicate: identical event already processed
                    return
                else:
                    raise DuplicateEventConflictError(
                        event_id=eid,
                        message=f"Conflicting duplicate event_id '{eid}' detected for execution '{exec_id}'."
                    )

            # Record event in published registry
            self._published_events[eid] = validated_event.model_copy(deep=True)
            self._execution_sequences[exec_id] = max(
                self._execution_sequences.get(exec_id, -1),
                validated_event.sequence
            )

            # 3. Retrieve matching subscriptions in deterministic registration order
            target_type_str = validated_event.type.value if hasattr(validated_event.type, "value") else str(validated_event.type)
            matching_subs = []
            for sub in self._subscriptions.values():
                if sub.event_type is not None and sub.event_type != target_type_str:
                    continue
                if sub.execution_id is not None and sub.execution_id != exec_id:
                    continue
                matching_subs.append(sub)

        # 4. Dispatch outside global state lock to prevent subscriber deadlocks
        errors = []
        for sub in matching_subs:
            try:
                # Defensive deep copy ensures subscriber isolation
                event_copy = validated_event.model_copy(deep=True)
                sub.handler(event_copy)
            except Exception as exc:
                err_record = {
                    "subscription_id": sub.subscription_id,
                    "event_id": eid,
                    "execution_id": exec_id,
                    "error": str(exc),
                    "exception_type": type(exc).__name__
                }
                with self._lock:
                    self._handler_errors.append(err_record)
                if not self._isolate_handler_errors:
                    errors.append(exc)

        if errors and not self._isolate_handler_errors:
            raise EventDeliveryError(
                f"Handler execution failed for event '{eid}'",
                handler_errors=errors
            )

    def subscribe(
        self,
        handler: EventHandler,
        event_type: Optional[Union[EventType, str]] = None,
        execution_id: Optional[str] = None
    ) -> str:
        """Register a subscriber handler with optional type and execution filters."""
        if not callable(handler):
            raise SubscriptionError("Handler must be a callable.")

        type_str = None
        if event_type is not None:
            type_str = event_type.value if hasattr(event_type, "value") else str(event_type)

        with self._lock:
            if self._is_closed:
                raise SubscriptionError("Event bus is closed; cannot subscribe.")

            sub_id = f"sub_{uuid.uuid4().hex[:12]}"
            self._subscriptions[sub_id] = _Subscription(
                subscription_id=sub_id,
                handler=handler,
                event_type=type_str,
                execution_id=execution_id
            )
            return sub_id

    def unsubscribe(self, subscription_id: str) -> bool:
        """Remove a subscriber by its subscription ID."""
        with self._lock:
            if subscription_id in self._subscriptions:
                del self._subscriptions[subscription_id]
                return True
            return False

    def subscriber_count(
        self,
        event_type: Optional[Union[EventType, str]] = None
    ) -> int:
        """Return the count of active subscriptions, optionally filtered by event type."""
        with self._lock:
            if event_type is None:
                return len(self._subscriptions)
            target = event_type.value if hasattr(event_type, "value") else str(event_type)
            return sum(
                1 for sub in self._subscriptions.values()
                if sub.event_type is None or sub.event_type == target
            )

    @property
    def handler_errors(self) -> List[Dict[str, Any]]:
        """Return captured handler errors for assertions and diagnostics."""
        with self._lock:
            return list(self._handler_errors)

    def clear(self) -> None:
        """Clear subscriptions, published event cache, and captured errors."""
        with self._lock:
            self._subscriptions.clear()
            self._published_events.clear()
            self._execution_sequences.clear()
            self._handler_errors.clear()

    def close(self) -> None:
        """Close the event bus."""
        with self._lock:
            self._is_closed = True
            self.clear()
