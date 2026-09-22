"""Capability Resolver exception taxonomy."""

from typing import Any, Dict, Optional


class CapabilityResolverError(Exception):
    """Base exception for all capability resolver operations."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ResolutionInputError(CapabilityResolverError):
    """Raised when resolver input contracts are malformed or missing required metadata."""
    pass
