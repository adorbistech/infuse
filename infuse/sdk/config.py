"""Client configuration for the INFUSE SDK (Block 28)."""

import os
from typing import Any, Dict, Optional
from pydantic import Field

from infuse.contracts.common import InfuseBaseModel


class ClientConfig(InfuseBaseModel):
    """Configuration options for initializing an InfuseClient."""

    base_url: str = Field(
        default="http://localhost:8000",
        description="Base URL for the INFUSE Universal HTTP API.",
    )
    api_key: Optional[str] = Field(
        default=None,
        description="Optional API key or bearer authorization token.",
    )
    timeout_seconds: float = Field(
        default=30.0,
        ge=0.1,
        description="Default request timeout in seconds.",
    )
    custom_headers: Dict[str, str] = Field(
        default_factory=dict,
        description="Additional HTTP headers sent with every request.",
    )
    correlation_id_prefix: str = Field(
        default="corr_sdk",
        description="Prefix for client-generated correlation identifiers.",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Client-level configuration extensions.",
    )

    @classmethod
    def from_env(cls) -> "ClientConfig":
        """Load configuration from standard INFUSE environment variables."""
        return cls(
            base_url=os.getenv("INFUSE_BASE_URL", "http://localhost:8000"),
            api_key=os.getenv("INFUSE_API_KEY"),
            timeout_seconds=float(os.getenv("INFUSE_TIMEOUT_SECONDS", "30.0")),
        )


__all__ = ["ClientConfig"]
