"""Claude Code Agent Adapter package (Block 24)."""

from infuse.agents.claude.adapter import ClaudeCodeAdapter
from infuse.agents.claude.errors import (
    ClaudeAdapterError,
    ClaudeCLINotFoundError,
    ClaudeMalformedOutputError,
    ClaudeProcessError,
    ClaudeTimeoutError,
)
from infuse.agents.claude.models import (
    ClaudeAdapterConfig,
    ClaudeExecutionOutput,
    redact_secrets,
)
from infuse.agents.claude.transport import (
    ClaudeReferenceTransport,
    ClaudeSubprocessTransport,
    IClaudeTransport,
)

__all__ = [
    "ClaudeCodeAdapter",
    "ClaudeAdapterError",
    "ClaudeCLINotFoundError",
    "ClaudeMalformedOutputError",
    "ClaudeProcessError",
    "ClaudeTimeoutError",
    "ClaudeAdapterConfig",
    "ClaudeExecutionOutput",
    "redact_secrets",
    "IClaudeTransport",
    "ClaudeSubprocessTransport",
    "ClaudeReferenceTransport",
]
