"""Data models, configuration, and secret redaction for Block 26 Codex Adapter."""

import re
from typing import Any, Dict, List, Optional
from pydantic import Field

from infuse.contracts.common import InfuseBaseModel


def redact_codex_secrets(text: Optional[str]) -> str:
    """Redact sensitive API keys, tokens, and passwords from Codex logs and errors."""
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
    # Standalone token patterns (e.g. sk-..., codex-...)
    redacted = re.sub(r"sk-[A-Za-z0-9_-]{10,}", "[REDACTED]", redacted)
    redacted = re.sub(r"codex-[A-Za-z0-9_-]{10,}", "[REDACTED]", redacted)
    return redacted


class CodexExecutionOutput(InfuseBaseModel):
    """Raw execution outcome from the Codex transport layer."""
    stdout: str = Field(default="", description="Standard output stream.")
    stderr: str = Field(default="", description="Standard error stream.")
    return_code: int = Field(default=0, description="Process return status code.")
    parsed_json: Optional[Dict[str, Any]] = Field(default=None, description="Parsed JSON/JSONL output if available.")
    events_jsonl: List[Dict[str, Any]] = Field(default_factory=list, description="Parsed JSONL events if available.")
    duration_ms: float = Field(default=0.0, ge=0.0, description="Execution duration in milliseconds.")


class CodexAdapterConfig(InfuseBaseModel):
    """Configuration for Codex agent adapter."""
    cli_path: Optional[str] = Field(default=None, description="Explicit path to codex CLI executable.")
    default_model: Optional[str] = Field(default=None, description="Default model alias or override (e.g., 'o3', 'gpt-4o').")
    timeout_seconds: float = Field(default=60.0, ge=0.1, description="Execution timeout limit in seconds.")
    working_directory: Optional[str] = Field(default=None, description="Working directory for CLI subprocesses.")
    sandbox_mode: Optional[str] = Field(default=None, description="Codex sandbox mode (e.g., 'read-only', 'workspace-write').")
    skip_git_repo_check: bool = Field(default=True, description="Allow running Codex outside a Git repository.")
    ephemeral: bool = Field(default=True, description="Run without persisting session files to disk.")
    env_vars: Dict[str, str] = Field(default_factory=dict, description="Custom environment variables to pass to subprocess.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional adapter configuration options.")


__all__ = [
    "CodexExecutionOutput",
    "CodexAdapterConfig",
    "redact_codex_secrets",
]
