"""Domain exceptions for Claude Code Agent Adapter."""

from infuse.agents.errors import AgentAdapterError


class ClaudeAdapterError(AgentAdapterError):
    """Base exception for Claude Code agent adapter errors."""
    pass


class ClaudeCLINotFoundError(ClaudeAdapterError):
    """Raised when the claude executable cannot be found on PATH."""
    pass


class ClaudeProcessError(ClaudeAdapterError):
    """Raised when Claude Code subprocess exits with a non-zero code or error."""
    pass


class ClaudeTimeoutError(ClaudeAdapterError):
    """Raised when a Claude Code process execution times out."""
    pass


class ClaudeMalformedOutputError(ClaudeAdapterError):
    """Raised when Claude Code output cannot be parsed into standard schema."""
    pass
