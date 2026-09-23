"""Domain exceptions for INFUSE Observer Layer."""


class ObserverError(Exception):
    """Base exception for all observer layer errors."""
    pass


class TokenObservationError(ObserverError):
    """Raised when token event processing or normalization fails."""
    pass
