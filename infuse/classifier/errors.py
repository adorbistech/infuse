"""Workload Classifier exception taxonomy."""

from typing import Any, Dict, Optional


class WorkloadClassifierError(Exception):
    """Base exception for all Workload Classifier operations."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ClassificationError(WorkloadClassifierError):
    """Raised when an execution context cannot be classified due to invalid input."""
    pass
