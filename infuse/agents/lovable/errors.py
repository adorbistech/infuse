"""Domain exceptions for Lovable Agent Adapter (Block 27)."""

from infuse.agents.errors import AgentAdapterError


class LovableAdapterError(AgentAdapterError):
    """Base exception for Lovable agent adapter errors."""
    pass


class LovableAuthenticationError(LovableAdapterError):
    """Raised when authentication with Lovable API fails."""
    pass


class LovableNetworkError(LovableAdapterError):
    """Raised when network transport to Lovable API fails."""
    pass


class LovableTimeoutError(LovableAdapterError):
    """Raised when a Lovable project/execution times out."""
    pass


class LovableMalformedOutputError(LovableAdapterError):
    """Raised when Lovable output cannot be parsed into standard schema."""
    pass
