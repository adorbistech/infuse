"""Domain exceptions for Codex Agent Adapter (Block 26)."""

from infuse.agents.errors import AgentAdapterError


class CodexAdapterError(AgentAdapterError):
    """Base exception for Codex agent adapter errors."""
    pass


class CodexCLINotFoundError(CodexAdapterError):
    """Raised when the codex executable cannot be found on PATH."""
    pass


class CodexProcessError(CodexAdapterError):
    """Raised when Codex subprocess exits with a non-zero code or error."""
    pass


class CodexTimeoutError(CodexAdapterError):
    """Raised when a Codex process execution times out."""
    pass


class CodexMalformedOutputError(CodexAdapterError):
    """Raised when Codex output cannot be parsed into standard schema."""
    pass
