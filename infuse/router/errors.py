"""Router exception taxonomy."""

from typing import Any, Dict, Optional


class RouterError(Exception):
    """Base exception for all router operations."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NoCompatibleTargetsError(RouterError):
    """Raised when no compatible targets exist in the capability resolution result."""
    pass


class InvalidRoutingConfigurationError(RouterError):
    """Raised when routing strategy or parameters are malformed."""
    pass
