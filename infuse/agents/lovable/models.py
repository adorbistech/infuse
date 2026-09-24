"""Data models, configuration, and secret redaction for Block 27 Lovable Adapter."""

import re
from typing import Any, Dict, List, Optional
from pydantic import Field

from infuse.contracts.common import InfuseBaseModel


def redact_lovable_secrets(text: Optional[str]) -> str:
    """Redact sensitive API keys, tokens, and passwords from Lovable logs and errors."""
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
    # Standalone token patterns (e.g. sk-..., lovable-...)
    redacted = re.sub(r"sk-[A-Za-z0-9_-]{10,}", "[REDACTED]", redacted)
    redacted = re.sub(r"lovable-[A-Za-z0-9_-]{10,}", "[REDACTED]", redacted)
    return redacted


class LovableExecutionOutput(InfuseBaseModel):
    """Raw execution outcome from the Lovable transport layer."""
    response_data: Dict[str, Any] = Field(default_factory=dict, description="Parsed response data from Lovable API.")
    status_code: int = Field(default=200, description="HTTP or transport status code.")
    duration_ms: float = Field(default=0.0, ge=0.0, description="Execution duration in milliseconds.")
    error_message: Optional[str] = Field(default=None, description="Error message if execution failed.")


class LovableAdapterConfig(InfuseBaseModel):
    """Configuration for Lovable cloud/API agent adapter."""
    api_endpoint: str = Field(default="https://api.lovable.dev/v1", description="Lovable API base endpoint.")
    api_key: Optional[str] = Field(default=None, description="API authorization key for Lovable.")
    project_id: Optional[str] = Field(default=None, description="Target Lovable project/workspace ID.")
    timeout_seconds: float = Field(default=60.0, ge=0.1, description="Execution timeout limit in seconds.")
    custom_headers: Dict[str, str] = Field(default_factory=dict, description="Custom headers for API requests.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional adapter configuration options.")


__all__ = [
    "LovableExecutionOutput",
    "LovableAdapterConfig",
    "redact_lovable_secrets",
]
