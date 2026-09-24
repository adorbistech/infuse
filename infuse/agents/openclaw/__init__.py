"""OpenClaw Agent Adapter package (Block 27)."""

from infuse.agents.openclaw.adapter import OpenClawAdapter
from infuse.agents.openclaw.errors import (
    OpenClawAdapterError,
    OpenClawCLINotFoundError,
    OpenClawMalformedOutputError,
    OpenClawProcessError,
    OpenClawTimeoutError,
)
from infuse.agents.openclaw.models import (
    OpenClawAdapterConfig,
    OpenClawExecutionOutput,
    redact_openclaw_secrets,
)
from infuse.agents.openclaw.transport import (
    IOpenClawTransport,
    OpenClawReferenceTransport,
    OpenClawSubprocessTransport,
)

__all__ = [
    "OpenClawAdapter",
    "OpenClawAdapterError",
    "OpenClawCLINotFoundError",
    "OpenClawMalformedOutputError",
    "OpenClawProcessError",
    "OpenClawTimeoutError",
    "OpenClawAdapterConfig",
    "OpenClawExecutionOutput",
    "redact_openclaw_secrets",
    "IOpenClawTransport",
    "OpenClawSubprocessTransport",
    "OpenClawReferenceTransport",
]
