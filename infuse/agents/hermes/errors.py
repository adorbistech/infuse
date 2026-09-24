"""Domain exceptions for Hermes Agent Adapter (Block 27)."""

from infuse.agents.errors import AgentAdapterError


class HermesAdapterError(AgentAdapterError):
    """Base exception for Hermes agent adapter errors."""
    pass


class HermesCLINotFoundError(HermesAdapterError):
    """Raised when the hermes executable cannot be found on PATH."""
    pass


class HermesProcessError(HermesAdapterError):
    """Raised when Hermes subprocess exits with a non-zero code or error."""
    pass


class HermesTimeoutError(HermesAdapterError):
    """Raised when a Hermes process execution times out."""
    pass


class HermesMalformedOutputError(HermesAdapterError):
    """Raised when Hermes output cannot be parsed into standard schema."""
    pass
