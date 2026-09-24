"""Data models, configuration, and secret redaction for Block 27 Hermes Adapter."""

import re
from typing import Any, Dict, List, Optional
from pydantic import Field

from infuse.contracts.common import InfuseBaseModel


def redact_hermes_secrets(text: Optional[str]) -> str:
    """Redact sensitive API keys, tokens, and passwords from Hermes logs and errors."""
    if not text:
        return ""
    redacted = text
    # Key-value secret patterns
    redacted = re.sub(
        r"(?i)(api[_-]?key|secret|token|password|auth|bearer)\s*[:=]\s*['\"]?([A-Za-z0-9_\-\.]{8,})['\"]?",
        r"\1: [REDACTED]",
        redacted,
    )
    # Bearer auth tokens
    redacted = re.sub(
        r"(?i)\bbearer\s+([A-Za-z0-9_\-\.]{8,})",
        "Bearer [REDACTED]",
        redacted,
    )
    # Standalone token patterns (e.g. sk-..., hermes-...)
    redacted = re.sub(r"sk-[A-Za-z0-9_-]{10,}", "[REDACTED]", redacted)
    redacted = re.sub(r"hermes-[A-Za-z0-9_-]{10,}", "[REDACTED]", redacted)
    return redacted


class HermesExecutionOutput(InfuseBaseModel):
    """Raw execution outcome from the Hermes transport layer."""
    stdout: str = Field(default="", description="Standard output stream.")
    stderr: str = Field(default="", description="Standard error stream.")
    return_code: int = Field(default=0, description="Process return status code.")
    parsed_json: Optional[Dict[str, Any]] = Field(default=None, description="Parsed JSON output if available.")
    duration_ms: float = Field(default=0.0, ge=0.0, description="Execution duration in milliseconds.")


class HermesAdapterConfig(InfuseBaseModel):
    """Configuration for Hermes agent adapter."""
    cli_path: Optional[str] = Field(default=None, description="Explicit path to hermes CLI executable.")
    default_model: Optional[str] = Field(default=None, description="Default model override (e.g., 'anthropic/claude-sonnet-4.6').")
    timeout_seconds: float = Field(default=60.0, ge=0.1, description="Execution timeout limit in seconds.")
    working_directory: Optional[str] = Field(default=None, description="Working directory for CLI subprocesses.")
    accept_hooks: bool = Field(default=True, description="Auto-approve hooks without TTY prompt (--accept-hooks).")
    yolo_mode: bool = Field(default=False, description="Bypass all command approval prompts (--yolo).")
    env_vars: Dict[str, str] = Field(default_factory=dict, description="Custom environment variables to pass to subprocess.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional adapter configuration options.")


__all__ = [
    "HermesExecutionOutput",
    "HermesAdapterConfig",
    "redact_hermes_secrets",
]
