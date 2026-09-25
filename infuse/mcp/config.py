"""Configuration models and loaders for INFUSE MCP Server (Block 30)."""

import os
from typing import Optional
from pydantic import Field

from infuse.contracts.common import InfuseBaseModel
from infuse.sdk.config import ClientConfig
from infuse.version import __version__


class McpServerConfig(InfuseBaseModel):
    """Configuration options for the INFUSE MCP Server."""

    name: str = Field(
        default="infuse",
        description="MCP server name identifier registered with clients.",
    )
    version: str = Field(
        default=__version__,
        description="INFUSE MCP server version.",
    )
    base_url: Optional[str] = Field(
        default=None,
        description="INFUSE Core API endpoint URL (defaults to SDK default).",
    )
    api_key: Optional[str] = Field(
        default=None,
        description="INFUSE API authorization key.",
    )
    timeout_seconds: float = Field(
        default=30.0,
        ge=0.1,
        description="HTTP request timeout in seconds.",
    )
    transport: str = Field(
        default="stdio",
        description="Transport mode (stdio, streamable_http, sse).",
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level for server diagnostics.",
    )

    @classmethod
    def from_env(cls) -> "McpServerConfig":
        """Load configuration from environment variables."""
        return cls(
            name=os.getenv("INFUSE_MCP_SERVER_NAME", "infuse"),
            version=__version__,
            base_url=os.getenv("INFUSE_BASE_URL", "http://localhost:8000"),
            api_key=os.getenv("INFUSE_API_KEY"),
            timeout_seconds=float(os.getenv("INFUSE_TIMEOUT_SECONDS", "30.0")),
            transport=os.getenv("INFUSE_MCP_TRANSPORT", "stdio"),
            log_level=os.getenv("INFUSE_LOG_LEVEL", "INFO"),
        )

    def to_client_config(self) -> ClientConfig:
        """Convert MCP server configuration into SDK ClientConfig."""
        return ClientConfig(
            base_url=self.base_url or "http://localhost:8000",
            api_key=self.api_key,
            timeout_seconds=self.timeout_seconds,
        )


__all__ = ["McpServerConfig"]
