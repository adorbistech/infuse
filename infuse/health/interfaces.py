"""Interface definitions for Block 17 Health Engine."""

from abc import ABC, abstractmethod
from typing import List, Optional

from infuse.contracts.events import ExecutionEvent
from infuse.events.interfaces import IEventBus
from infuse.health.models import (
    ExecutionHealthSummary,
    ModelHealthAggregate,
    ProviderHealthAggregate,
)


class IHealthEngine(ABC):
    """Abstract interface for health observation and deterministic aggregation."""

    @abstractmethod
    def handle_event(self, event: ExecutionEvent) -> Optional[ExecutionHealthSummary]:
        """Consume a canonical execution event and update health observation state."""
        pass

    @abstractmethod
    def get_execution_health(self, execution_id: str) -> Optional[ExecutionHealthSummary]:
        """Retrieve health summary for a specific execution."""
        pass

    @abstractmethod
    def list_execution_health(self) -> List[ExecutionHealthSummary]:
        """List all active execution health summaries."""
        pass

    @abstractmethod
    def get_provider_aggregate(self, provider_id: str) -> Optional[ProviderHealthAggregate]:
        """Retrieve aggregate health metrics for a provider."""
        pass

    @abstractmethod
    def list_provider_aggregates(self) -> List[ProviderHealthAggregate]:
        """List aggregate health metrics for all observed providers."""
        pass

    @abstractmethod
    def get_model_aggregate(self, provider_id: str, model_id: str) -> Optional[ModelHealthAggregate]:
        """Retrieve aggregate health metrics for a specific model under a provider."""
        pass

    @abstractmethod
    def list_model_aggregates(self) -> List[ModelHealthAggregate]:
        """List aggregate health metrics for all observed models."""
        pass

    @abstractmethod
    def attach_to_bus(self, bus: IEventBus) -> List[str]:
        """Subscribe to relevant canonical events on the Event Bus."""
        pass

    @abstractmethod
    def detach_from_bus(self, bus: IEventBus) -> None:
        """Unsubscribe from the Event Bus."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all in-memory health observations and aggregates."""
        pass
