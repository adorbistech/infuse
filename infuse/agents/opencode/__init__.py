"""OpenCode Agent Adapter package (Block 25)."""

from infuse.agents.opencode.adapter import OpenCodeAdapter
from infuse.agents.opencode.errors import (
    OpenCodeAdapterError,
    OpenCodeCLINotFoundError,
    OpenCodeMalformedOutputError,
    OpenCodeProcessError,
    OpenCodeTimeoutError,
)
from infuse.agents.opencode.models import (
    OpenCodeAdapterConfig,
    OpenCodeExecutionOutput,
    redact_opencode_secrets,
)
from infuse.agents.opencode.transport import (
    IOpenCodeTransport,
    OpenCodeReferenceTransport,
    OpenCodeSubprocessTransport,
)

__all__ = [
    "OpenCodeAdapter",
    "OpenCodeAdapterError",
    "OpenCodeCLINotFoundError",
    "OpenCodeMalformedOutputError",
    "OpenCodeProcessError",
    "OpenCodeTimeoutError",
    "OpenCodeAdapterConfig",
    "OpenCodeExecutionOutput",
    "redact_opencode_secrets",
    "IOpenCodeTransport",
    "OpenCodeSubprocessTransport",
    "OpenCodeReferenceTransport",
]
