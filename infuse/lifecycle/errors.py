"""Execution Lifecycle Layer exceptions."""

from typing import Any, Dict, Optional


class LifecycleError(Exception):
    """Base exception for all execution lifecycle operations."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ExecutionNotFoundError(LifecycleError):
    """Raised when an execution run cannot be found by its execution_id."""

    def __init__(self, execution_id: str) -> None:
        super().__init__(
            f"Execution '{execution_id}' not found.",
            details={"execution_id": execution_id}
        )
        self.execution_id = execution_id


class ExecutionAlreadyExistsError(LifecycleError):
    """Raised when an execution run with the same execution_id already exists."""

    def __init__(self, execution_id: str) -> None:
        super().__init__(
            f"Execution '{execution_id}' already exists.",
            details={"execution_id": execution_id}
        )
        self.execution_id = execution_id


class InvalidStateTransitionError(LifecycleError):
    """Raised when an invalid lifecycle state transition is attempted."""

    def __init__(self, execution_id: str, from_state: str, to_state: str) -> None:
        super().__init__(
            f"Invalid lifecycle transition for execution '{execution_id}': cannot move from '{from_state}' to '{to_state}'.",
            details={
                "execution_id": execution_id,
                "from_state": from_state,
                "to_state": to_state
            }
        )
        self.execution_id = execution_id
        self.from_state = from_state
        self.to_state = to_state


class ExecutionCancellationError(LifecycleError):
    """Raised when an execution cannot be cancelled in its current state."""

    def __init__(self, execution_id: str, reason: str) -> None:
        super().__init__(
            f"Cannot cancel execution '{execution_id}': {reason}",
            details={"execution_id": execution_id, "reason": reason}
        )
        self.execution_id = execution_id
        self.reason = reason
