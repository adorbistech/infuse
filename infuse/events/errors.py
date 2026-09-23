"""Domain exceptions for INFUSE Event Contract and Event Bus."""


class EventError(Exception):
    """Base exception for all event and event bus errors."""
    pass


class EventValidationError(EventError):
    """Raised when an event fails canonical contract or structural validation."""
    def __init__(self, message: str, details: dict = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class DuplicateEventConflictError(EventError):
    """Raised when an event is published with a duplicate event_id but conflicting content."""
    def __init__(self, event_id: str, message: str = None) -> None:
        msg = message or f"Event with id '{event_id}' already exists with conflicting content."
        super().__init__(msg)
        self.event_id = event_id


class SubscriptionError(EventError):
    """Raised on invalid subscription or unsubscription operations."""
    pass


class EventDeliveryError(EventError):
    """Raised when fatal delivery failures occur during publication."""
    def __init__(self, message: str, handler_errors: list = None) -> None:
        super().__init__(message)
        self.message = message
        self.handler_errors = handler_errors or []
