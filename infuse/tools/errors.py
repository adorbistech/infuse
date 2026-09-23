"""Domain exceptions for INFUSE Tool Activity Observer."""


class ToolObserverError(Exception):
    """Base exception for all tool observer errors."""
    pass


class ToolObservationError(ToolObserverError):
    """Raised when an invalid event or malformed tool payload is received."""
    pass


class CorrelationError(ToolObserverError):
    """Raised when tool correlation fails deterministically."""
    pass
