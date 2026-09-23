"""Abstract interface definitions for Block 15 Token Observer."""

from abc import ABC, abstractmethod
from typing import List, Optional

from infuse.contracts.events import ExecutionEvent
from infuse.events.interfaces import IEventBus
from infuse.observer.models import ExecutionTokenSummary


class ITokenObserver(ABC):
    """Abstract interface for execution token and usage observation."""

    @abstractmethod
    def handle_event(self, event: ExecutionEvent) -> None:
        """Process an incoming canonical ExecutionEvent and update token observation state."""
        pass

    @abstractmethod
    def get_observation(self, execution_id: str) -> Optional[ExecutionTokenSummary]:
        """Retrieve the normalized token observation summary for a given execution ID."""
        pass

    @abstractmethod
    def list_observations(self) -> List[ExecutionTokenSummary]:
        """List all current execution token summaries."""
        pass

    @abstractmethod
    def is_finalized(self, execution_id: str) -> bool:
        """Check whether the token observation for an execution is finalized."""
        pass

    @abstractmethod
    def attach_to_bus(self, bus: IEventBus) -> List[str]:
        """Subscribe this observer to relevant token/lifecycle event types on the provided Event Bus."""
        pass

    @abstractmethod
    def detach_from_bus(self, bus: IEventBus) -> None:
        """Unsubscribe this observer from the provided Event Bus."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all in-memory observation records."""
        pass
