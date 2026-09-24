"""Domain exceptions for OpenCode Agent Adapter (Block 25)."""

from infuse.agents.errors import AgentAdapterError


class OpenCodeAdapterError(AgentAdapterError):
    """Base exception for OpenCode agent adapter errors."""
    pass


class OpenCodeCLINotFoundError(OpenCodeAdapterError):
    """Raised when the opencode executable cannot be found on PATH."""
    pass


class OpenCodeProcessError(OpenCodeAdapterError):
    """Raised when OpenCode subprocess exits with a non-zero code or error."""
    pass


class OpenCodeTimeoutError(OpenCodeAdapterError):
    """Raised when an OpenCode process execution times out."""
    pass


class OpenCodeMalformedOutputError(OpenCodeAdapterError):
    """Raised when OpenCode output cannot be parsed into standard schema."""
    pass
