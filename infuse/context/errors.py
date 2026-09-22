"""Execution Context exception definitions."""

from typing import Any, Dict, List, Optional


class ExecutionContextError(Exception):
    """Base exception for all Execution Context operations."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ExecutionContextValidationError(ExecutionContextError):
    """Raised when an execution context violates structural or invariant constraints."""
    def __init__(self, message: str, violations: Optional[List[str]] = None) -> None:
        super().__init__(message, details={"violations": violations or []})
        self.violations = violations or []


class ExecutionContextNotFoundError(ExecutionContextError):
    """Raised when a requested execution context does not exist."""
    pass
