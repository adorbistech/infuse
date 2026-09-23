"""Domain exceptions for INFUSE Execution State Engine."""


class StateEngineError(Exception):
    """Base exception for all execution state engine errors."""
    pass


class StateDerivationError(StateEngineError):
    """Raised when state derivation encounters invalid or contradictory inputs."""
    pass


class StateTransitionError(StateEngineError):
    """Raised when an invalid state transition is attempted."""
    pass
