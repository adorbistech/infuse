"""Domain exceptions for INFUSE Health Engine."""


class HealthError(Exception):
    """Base exception for all health layer errors."""
    pass


class HealthObservationError(HealthError):
    """Raised when an invalid event or malformed observation payload is received."""
    pass


class InvalidEventError(HealthError):
    """Raised when an event does not adhere to canonical contract schemas."""
    pass
