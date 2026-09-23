"""Interfaces for INFUSE Event Transport and Event Bus."""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Union

from infuse.contracts.events import EventType, ExecutionEvent

EventHandler = Callable[[ExecutionEvent], None]


class IEventBus(ABC):
    """Authoritative abstract interface for in-process and distributed event publication."""

    @abstractmethod
    def publish(self, event: ExecutionEvent) -> None:
        """Validate and publish an execution event to all matching subscribers.
        
        Args:
            event: Canonical ExecutionEvent envelope to validate and distribute.
            
        Raises:
            EventValidationError: If event fails canonical validation.
            DuplicateEventConflictError: If duplicate event_id is published with conflicting content.
            EventDeliveryError: If fatal transport errors occur during distribution.
        """
        pass

    @abstractmethod
    def subscribe(
        self,
        handler: EventHandler,
        event_type: Optional[Union[EventType, str]] = None,
        execution_id: Optional[str] = None
    ) -> str:
        """Register an event handler with optional filtering.
        
        Args:
            handler: Callable invoked with an immutable copy of matching events.
            event_type: Optional specific EventType to listen to (None = listen to all).
            execution_id: Optional specific execution_id to filter events for.
            
        Returns:
            Unique subscription_id token string for subsequent unsubscription.
        """
        pass

    @abstractmethod
    def unsubscribe(self, subscription_id: str) -> bool:
        """Remove a subscription by subscription_id token.
        
        Args:
            subscription_id: Identifier returned from subscribe().
            
        Returns:
            True if subscription was found and removed, False otherwise.
        """
        pass

    @abstractmethod
    def subscriber_count(
        self,
        event_type: Optional[Union[EventType, str]] = None
    ) -> int:
        """Return the number of active subscriptions."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all active subscriptions and internal transient state."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Gracefully shutdown the event bus."""
        pass
