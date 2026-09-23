"""Explicit in-memory test event collector for verification and testing."""

import threading
from typing import List, Optional, Union

from infuse.contracts.events import EventType, ExecutionEvent


class InMemoryEventCollector:
    """Thread-safe event collector for recording events in test suites and local debugging."""

    def __init__(self) -> None:
        self._events: List[ExecutionEvent] = []
        self._lock = threading.RLock()

    def __call__(self, event: ExecutionEvent) -> None:
        """Handler method invoked by the EventBus upon event publication."""
        with self._lock:
            # Store deep copy to ensure isolation
            self._events.append(event.model_copy(deep=True))

    def get_events(
        self,
        event_type: Optional[Union[EventType, str]] = None,
        execution_id: Optional[str] = None
    ) -> List[ExecutionEvent]:
        """Retrieve collected events with optional filtering."""
        with self._lock:
            res = list(self._events)
            if event_type is not None:
                type_val = event_type.value if hasattr(event_type, "value") else str(event_type)
                res = [e for e in res if (e.type.value if hasattr(e.type, "value") else str(e.type)) == type_val]
            if execution_id is not None:
                res = [e for e in res if e.execution_id == execution_id]
            return [e.model_copy(deep=True) for e in res]

    @property
    def count(self) -> int:
        """Total number of collected events."""
        with self._lock:
            return len(self._events)

    def clear(self) -> None:
        """Clear all collected events."""
        with self._lock:
            self._events.clear()
