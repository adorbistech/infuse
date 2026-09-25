"""Production Deployment Configuration for Block 35.

Provides strictly validated, environment-driven configuration for INFUSE
production deployments without hardcoding secrets, credentials, or customer rules.
"""

import os
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import Field, field_validator

from infuse.contracts.common import InfuseBaseModel


class EnvironmentType(str, Enum):
    """Execution deployment environments."""
    PRODUCTION = "production"
    STAGING = "staging"
    DEVELOPMENT = "development"
    TEST = "test"


class LogLevel(str, Enum):
    """Standard logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DeploymentConfig(InfuseBaseModel):
    """Immutable, strongly typed production deployment configuration."""

    # Network & Binding
    host: str = Field(default="0.0.0.0", description="IP address or hostname to bind server to.")
    port: int = Field(default=8000, ge=1, le=65535, description="Port number for HTTP API.")

    # Environment & Logging
    environment: EnvironmentType = Field(
        default=EnvironmentType.PRODUCTION,
        description="Deployment target environment.",
    )
    log_level: LogLevel = Field(
        default=LogLevel.INFO,
        description="Logging verbosity level.",
    )

    # Server Execution & Concurrency
    workers: int = Field(default=1, ge=1, le=128, description="Number of worker processes.")
    graceful_shutdown_timeout_sec: float = Field(
        default=15.0,
        ge=0.1,
        le=300.0,
        description="Graceful shutdown timeout in seconds.",
    )
    max_request_size_bytes: int = Field(
        default=10_485_760,
        ge=1024,
        le=104_857_600,
        description="Maximum incoming HTTP request payload size in bytes (default: 10MB).",
    )

    # Security & CORS
    cors_origins: List[str] = Field(
        default_factory=lambda: ["*"],
        description="Allowed CORS origin patterns.",
    )
    cors_allow_credentials: bool = Field(
        default=False,
        description="Whether to allow credentials in cross-origin requests.",
    )

    # Health & Observability Probes
    enable_metrics: bool = Field(
        default=True,
        description="Whether telemetry and performance metrics are enabled.",
    )
    enable_readiness_probe: bool = Field(
        default=True,
        description="Whether deep system readiness probe (/ready) is enabled.",
    )

    # MCP Sidecar Integration
    mcp_server_enabled: bool = Field(
        default=False,
        description="Whether to run or expose MCP server endpoints.",
    )
    mcp_server_port: int = Field(
        default=8001,
        ge=1,
        le=65535,
        description="Port for the optional MCP server sidecar.",
    )

    # Storage & Persistence Boundary
    storage_backend: str = Field(
        default="inmemory",
        description="Persistence backend category (e.g. inmemory, filesystem).",
    )
    storage_path: Optional[str] = Field(
        default=None,
        description="Optional directory path for filesystem persistence.",
    )

    @field_validator("host")
    @classmethod
    def validate_host(cls, v: str) -> str:
        v_stripped = v.strip()
        if not v_stripped:
            raise ValueError("Host must not be empty.")
        return v_stripped

    @field_validator("cors_origins", mode="before")
    @classmethod
    def normalize_cors_origins(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            if v.strip() == "*":
                return ["*"]
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        if isinstance(v, (list, tuple, set)):
            return [str(origin).strip() for origin in v if str(origin).strip()]
        return ["*"]

    def to_safe_dict(self) -> Dict[str, Any]:
        """Return sanitized dictionary suitable for logging and diagnostic inspection."""
        data = self.model_dump()
        # Ensure enum values are serialized as clean strings
        data["environment"] = self.environment.value if hasattr(self.environment, "value") else str(self.environment)
        data["log_level"] = self.log_level.value if hasattr(self.log_level, "value") else str(self.log_level)
        return data


def load_deployment_config(env_dict: Optional[Dict[str, str]] = None) -> DeploymentConfig:
    """Load and validate deployment configuration from environment variables.

    Reads variables prefixed with INFUSE_:
    - INFUSE_HOST (default: 0.0.0.0)
    - INFUSE_PORT (default: 8000)
    - INFUSE_ENVIRONMENT / INFUSE_ENV (default: production)
    - INFUSE_LOG_LEVEL (default: INFO)
    - INFUSE_WORKERS (default: 1)
    - INFUSE_SHUTDOWN_TIMEOUT_SEC (default: 15.0)
    - INFUSE_MAX_REQUEST_SIZE_BYTES (default: 10485760)
    - INFUSE_CORS_ORIGINS (default: "*")
    - INFUSE_ENABLE_METRICS (default: true)
    - INFUSE_ENABLE_READINESS_PROBE (default: true)
    - INFUSE_MCP_SERVER_ENABLED (default: false)
    - INFUSE_MCP_SERVER_PORT (default: 8001)
    - INFUSE_STORAGE_BACKEND (default: inmemory)
    - INFUSE_STORAGE_PATH (default: None)
    """
    env = env_dict if env_dict is not None else os.environ

    kwargs: Dict[str, Any] = {}

    if "INFUSE_HOST" in env:
        kwargs["host"] = env["INFUSE_HOST"]

    if "INFUSE_PORT" in env:
        try:
            kwargs["port"] = int(env["INFUSE_PORT"])
        except ValueError:
            raise ValueError(f"Invalid INFUSE_PORT: '{env['INFUSE_PORT']}' must be an integer.")

    raw_env = env.get("INFUSE_ENVIRONMENT") or env.get("INFUSE_ENV")
    if raw_env:
        try:
            kwargs["environment"] = EnvironmentType(raw_env.lower().strip())
        except ValueError:
            valid_envs = [e.value for e in EnvironmentType]
            raise ValueError(f"Invalid INFUSE_ENVIRONMENT '{raw_env}'. Must be one of: {valid_envs}")

    if "INFUSE_LOG_LEVEL" in env:
        raw_log = env["INFUSE_LOG_LEVEL"].upper().strip()
        try:
            kwargs["log_level"] = LogLevel(raw_log)
        except ValueError:
            valid_logs = [l.value for l in LogLevel]
            raise ValueError(f"Invalid INFUSE_LOG_LEVEL '{raw_log}'. Must be one of: {valid_logs}")

    if "INFUSE_WORKERS" in env:
        try:
            kwargs["workers"] = int(env["INFUSE_WORKERS"])
        except ValueError:
            raise ValueError(f"Invalid INFUSE_WORKERS: '{env['INFUSE_WORKERS']}' must be an integer.")

    if "INFUSE_SHUTDOWN_TIMEOUT_SEC" in env:
        try:
            kwargs["graceful_shutdown_timeout_sec"] = float(env["INFUSE_SHUTDOWN_TIMEOUT_SEC"])
        except ValueError:
            raise ValueError(
                f"Invalid INFUSE_SHUTDOWN_TIMEOUT_SEC: '{env['INFUSE_SHUTDOWN_TIMEOUT_SEC']}' must be a float."
            )

    if "INFUSE_MAX_REQUEST_SIZE_BYTES" in env:
        try:
            kwargs["max_request_size_bytes"] = int(env["INFUSE_MAX_REQUEST_SIZE_BYTES"])
        except ValueError:
            raise ValueError(
                f"Invalid INFUSE_MAX_REQUEST_SIZE_BYTES: '{env['INFUSE_MAX_REQUEST_SIZE_BYTES']}' must be an integer."
            )

    if "INFUSE_CORS_ORIGINS" in env:
        kwargs["cors_origins"] = env["INFUSE_CORS_ORIGINS"]

    if "INFUSE_ENABLE_METRICS" in env:
        kwargs["enable_metrics"] = env["INFUSE_ENABLE_METRICS"].lower().strip() in ("1", "true", "yes", "on")

    if "INFUSE_ENABLE_READINESS_PROBE" in env:
        kwargs["enable_readiness_probe"] = (
            env["INFUSE_ENABLE_READINESS_PROBE"].lower().strip() in ("1", "true", "yes", "on")
        )

    if "INFUSE_MCP_SERVER_ENABLED" in env:
        kwargs["mcp_server_enabled"] = (
            env["INFUSE_MCP_SERVER_ENABLED"].lower().strip() in ("1", "true", "yes", "on")
        )

    if "INFUSE_MCP_SERVER_PORT" in env:
        try:
            kwargs["mcp_server_port"] = int(env["INFUSE_MCP_SERVER_PORT"])
        except ValueError:
            raise ValueError(
                f"Invalid INFUSE_MCP_SERVER_PORT: '{env['INFUSE_MCP_SERVER_PORT']}' must be an integer."
            )

    if "INFUSE_STORAGE_BACKEND" in env:
        kwargs["storage_backend"] = env["INFUSE_STORAGE_BACKEND"].strip().lower()

    if "INFUSE_STORAGE_PATH" in env:
        kwargs["storage_path"] = env["INFUSE_STORAGE_PATH"].strip()

    return DeploymentConfig(**kwargs)
