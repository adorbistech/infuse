"""Domain exceptions for OpenClaw Agent Adapter (Block 27)."""

from infuse.agents.errors import AgentAdapterError


class OpenClawAdapterError(AgentAdapterError):
    """Base exception for OpenClaw agent adapter errors."""
    pass


class OpenClawCLINotFoundError(OpenClawAdapterError):
    """Raised when the openclaw executable cannot be found on PATH."""
    pass


class OpenClawProcessError(OpenClawAdapterError):
    """Raised when OpenClaw subprocess exits with a non-zero code or error."""
    pass


class OpenClawTimeoutError(OpenClawAdapterError):
    """Raised when an OpenClaw process execution times out."""
    pass


class OpenClawMalformedOutputError(OpenClawAdapterError):
    """Raised when OpenClaw output cannot be parsed into standard schema."""
    pass
