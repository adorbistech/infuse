"""Domain exceptions for INFUSE Web Activity Observer."""


class WebObserverError(Exception):
    """Base exception for all web observer errors."""
    pass


class WebObservationError(WebObserverError):
    """Raised when an invalid event or malformed web payload is received."""
    pass


class WebCorrelationError(WebObserverError):
    """Raised when web request/response correlation fails deterministically."""
    pass
