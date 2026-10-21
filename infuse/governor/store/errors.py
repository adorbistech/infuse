"""Budget Store Exceptions."""

from typing import Any, Dict, Optional


class BudgetStoreError(Exception):
    """Base exception for budget storage errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class BudgetStoreUnavailableError(BudgetStoreError):
    """Raised when the budget storage backend is unreachable or unhealthy (Fail Closed)."""
    pass


class IncompatibleTopologyError(BudgetStoreError):
    """Raised when server topology is incompatible with the selected budget storage backend."""
    pass
