"""Interface definitions for Block 19 Web Activity Observer."""

from abc import ABC, abstractmethod
from typing import List, Optional

from infuse.contracts.events import ExecutionEvent
from infuse.events.interfaces import IEventBus
from infuse.web.models import ExecutionWebSummary, WebActivityRecord


class IWebActivityObserver(ABC):
    """Abstract interface for web activity observation and deterministic aggregation."""

    @abstractmethod
    def handle_event(self, event: ExecutionEvent) -> Optional[ExecutionWebSummary]:
        """Consume a canonical web event and update web observation state."""
        pass

    @abstractmethod
    def get_execution_summary(self, execution_id: str) -> Optional[ExecutionWebSummary]:
        """Retrieve aggregated web activity summary for a specific execution."""
        pass

    @abstractmethod
    def list_execution_summaries(self) -> List[ExecutionWebSummary]:
        """List all active execution web summaries."""
        pass

    @abstractmethod
    def get_activity(self, execution_id: str, request_id: str) -> Optional[WebActivityRecord]:
        """Retrieve a specific web activity record by execution_id and request_id."""
        pass

    @abstractmethod
    def attach_to_bus(self, bus: IEventBus) -> List[str]:
        """Subscribe to WebRequest and WebResponse events on the Event Bus."""
        pass

    @abstractmethod
    def detach_from_bus(self, bus: IEventBus) -> None:
        """Unsubscribe from the Event Bus."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all in-memory web observations and summaries."""
        pass
