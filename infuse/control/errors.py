"""Domain exceptions for INFUSE Execution Control Boundary."""


class ControlBoundaryError(Exception):
    """Base exception for all Execution Control Boundary errors."""
    pass


class ControlDispatchError(ControlBoundaryError):
    """Raised when control dispatch encounters invalid parameters or fatal dispatch state."""
    pass


class UnsupportedControlError(ControlBoundaryError):
    """Raised when an unsupported control operation cannot be processed."""
    pass


class ControlExecutorError(ControlBoundaryError):
    """Raised when a control executor fails during physical command execution."""
    pass
