"""Hermes Agent Adapter package (Block 27)."""

from infuse.agents.hermes.adapter import HermesAdapter
from infuse.agents.hermes.errors import (
    HermesAdapterError,
    HermesCLINotFoundError,
    HermesMalformedOutputError,
    HermesProcessError,
    HermesTimeoutError,
)
from infuse.agents.hermes.models import (
    HermesAdapterConfig,
    HermesExecutionOutput,
    redact_hermes_secrets,
)
from infuse.agents.hermes.transport import (
    HermesReferenceTransport,
    HermesSubprocessTransport,
    IHermesTransport,
)

__all__ = [
    "HermesAdapter",
    "HermesAdapterError",
    "HermesCLINotFoundError",
    "HermesMalformedOutputError",
    "HermesProcessError",
    "HermesTimeoutError",
    "HermesAdapterConfig",
    "HermesExecutionOutput",
    "redact_hermes_secrets",
    "IHermesTransport",
    "HermesSubprocessTransport",
    "HermesReferenceTransport",
]
