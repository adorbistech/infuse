"""Interface definitions for Block 18 Tool Activity Observer."""

from abc import ABC, abstractmethod
from typing import List, Optional

from infuse.contracts.events import ExecutionEvent
from infuse.events.interfaces import IEventBus
from infuse.tools.models import ExecutionToolSummary, ToolInvocationRecord


class IToolActivityObserver(ABC):
    """Abstract interface for tool activity observation and deterministic aggregation."""

    @abstractmethod
    def handle_event(self, event: ExecutionEvent) -> Optional[ExecutionToolSummary]:
        """Consume a canonical tool event and update tool observation state."""
        pass

    @abstractmethod
    def get_execution_summary(self, execution_id: str) -> Optional[ExecutionToolSummary]:
        """Retrieve aggregated tool activity summary for a specific execution."""
        pass

    @abstractmethod
    def list_execution_summaries(self) -> List[ExecutionToolSummary]:
        """List all active execution tool summaries."""
        pass

    @abstractmethod
    def get_invocation(self, execution_id: str, call_id: str) -> Optional[ToolInvocationRecord]:
        """Retrieve a specific tool invocation record by execution_id and call_id."""
        pass

    @abstractmethod
    def attach_to_bus(self, bus: IEventBus) -> List[str]:
        """Subscribe to ToolCalled and ToolCompleted events on the Event Bus."""
        pass

    @abstractmethod
    def detach_from_bus(self, bus: IEventBus) -> None:
        """Unsubscribe from the Event Bus."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all in-memory tool observations and summaries."""
        pass
