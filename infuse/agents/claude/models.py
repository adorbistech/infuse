"""Data models and configuration for Block 24 Claude Code Adapter."""

import re
from typing import Any, Dict, Optional
from pydantic import Field

from infuse.contracts.common import InfuseBaseModel


def redact_secrets(text: Optional[str]) -> str:
    """Redact sensitive API keys, tokens, and passwords from strings."""
    if not text:
        return ""
    redacted = text
    # Key-value secret patterns with : or =
    redacted = re.sub(
        r"(?i)(api[_-]?key|secret|token|password|auth|bearer)\s*[:=]\s*['\"]?([A-Za-z0-9_\-\.]{8,})['\"]?",
        r"\1: [REDACTED]",
        redacted,
    )
    # Bearer auth tokens: "Bearer <token>"
    redacted = re.sub(
        r"(?i)\bbearer\s+([A-Za-z0-9_\-\.]{8,})",
        "Bearer [REDACTED]",
        redacted,
    )
    # Standalone token patterns (e.g. sk-ant-..., claude-...)
    redacted = re.sub(r"sk-[A-Za-z0-9_-]{10,}", "[REDACTED]", redacted)
    redacted = re.sub(r"claude-[A-Za-z0-9_-]{10,}", "[REDACTED]", redacted)
    return redacted


class ClaudeExecutionOutput(InfuseBaseModel):
    """Raw execution outcome from the Claude Code transport layer."""
    stdout: str = Field(default="", description="Standard output stream.")
    stderr: str = Field(default="", description="Standard error stream.")
    return_code: int = Field(default=0, description="Process return status code.")
    parsed_json: Optional[Dict[str, Any]] = Field(default=None, description="Parsed JSON output if available.")
    duration_ms: float = Field(default=0.0, ge=0.0, description="Execution duration in milliseconds.")


class ClaudeAdapterConfig(InfuseBaseModel):
    """Configuration for Claude Code agent adapter."""
    cli_path: Optional[str] = Field(default=None, description="Explicit path to claude CLI executable.")
    default_model: Optional[str] = Field(default="claude-3-7-sonnet", description="Default model alias.")
    permission_mode: str = Field(default="auto", description="CLI permission mode (acceptEdits, auto, dontAsk, plan).")
    timeout_seconds: float = Field(default=60.0, ge=0.1, description="Execution timeout limit in seconds.")
    working_directory: Optional[str] = Field(default=None, description="Working directory for CLI subprocesses.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional adapter configuration options.")


__all__ = [
    "ClaudeExecutionOutput",
    "ClaudeAdapterConfig",
    "redact_secrets",
]
