"""Policy Manager error taxonomy and exception definitions."""

from typing import Any, Dict, List, Optional


class PolicyManagerError(Exception):
    """Base exception for all Policy Manager errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class PolicyValidationError(PolicyManagerError):
    """Raised when a governance policy violates contract, range, or logical constraints."""
    def __init__(self, message: str, violations: Optional[List[str]] = None) -> None:
        super().__init__(message, details={"violations": violations or []})
        self.violations = violations or []


class PolicyNotFoundError(PolicyManagerError):
    """Raised when a requested policy or policy revision is not found."""
    pass


class PolicyConflictError(PolicyManagerError):
    """Raised when a policy operation encounters an identifier, version, or state conflict."""
    pass
