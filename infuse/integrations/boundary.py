"""Integration Boundary and Data Normalization for Block 31.

Guarantees:
1. Zero external object graph leakage into canonical INFUSE contracts.
2. Canonical normalization of third-party responses, errors, and token counts.
3. Strict secret redaction in all external payload representations and diagnostics.
4. No artificial fabrication of success, health, or pricing.
"""

import re
from typing import Any, Dict, Optional, Tuple, Union
from pydantic import ValidationError

from infuse.contracts.events import ProviderErrorPayload
from infuse.contracts.execution import NormalizedResponse
from infuse.sdk.errors import redact_sdk_secrets

SECRET_PATTERN = re.compile(
    r"(sk-[a-zA-Z0-9_\-]{8,}|ghp_[a-zA-Z0-9]{8,}|gho_[a-zA-Z0-9]{8,}|bearer\s+[a-zA-Z0-9_\-\.]{8,}|key-[a-zA-Z0-9]{8,})",
    re.IGNORECASE,
)


class IntegrationBoundary:
    """Isolates third-party components behind canonical INFUSE boundaries."""

    @staticmethod
    def sanitize_secrets(value: Any) -> Any:
        """Recursively redact sensitive API keys, tokens, and credentials."""
        if isinstance(value, str):
            redacted = redact_sdk_secrets(value)
            return SECRET_PATTERN.sub("[REDACTED]", redacted)
        elif isinstance(value, dict):
            sanitized: Dict[str, Any] = {}
            for k, v in value.items():
                if any(
                    sec in str(k).lower()
                    for sec in ["key", "token", "secret", "password", "auth", "bearer"]
                ):
                    sanitized[k] = "[REDACTED]"
                else:
                    sanitized[k] = IntegrationBoundary.sanitize_secrets(v)
            return sanitized
        elif isinstance(value, (list, tuple)):
            return [IntegrationBoundary.sanitize_secrets(item) for item in value]
        return value

    @staticmethod
    def normalize_response(
        raw_output: Any,
        provider: str,
        model: str,
        raw_usage: Optional[Dict[str, Any]] = None,
    ) -> NormalizedResponse:
        """Convert third-party raw response into canonical NormalizedResponse."""
        content = ""
        role = "assistant"
        input_tokens = 0
        output_tokens = 0
        total_tokens = 0

        # Handle object or dict
        if isinstance(raw_output, dict):
            # Dict extraction (e.g. OpenAI/LiteLLM JSON format)
            if "choices" in raw_output and isinstance(raw_output["choices"], list):
                if len(raw_output["choices"]) > 0:
                    first_choice = raw_output["choices"][0]
                    if isinstance(first_choice, dict):
                        msg = first_choice.get("message", {})
                        if isinstance(msg, dict):
                            content = str(msg.get("content", ""))
                            role = str(msg.get("role", "assistant"))
                        elif hasattr(msg, "content"):
                            content = str(getattr(msg, "content", ""))
                            role = str(getattr(msg, "role", "assistant"))
            elif "content" in raw_output:
                content = str(raw_output["content"])
                role = str(raw_output.get("role", "assistant"))

            usage = raw_output.get("usage") or raw_usage or {}
            if isinstance(usage, dict):
                input_tokens = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
                output_tokens = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
                total_tokens = int(usage.get("total_tokens") or (input_tokens + output_tokens))
        elif hasattr(raw_output, "choices"):
            # Object attribute extraction (e.g. ModelResponse object)
            choices = getattr(raw_output, "choices", [])
            if choices and len(choices) > 0:
                first = choices[0]
                msg = getattr(first, "message", None)
                if msg is not None:
                    content = str(getattr(msg, "content", ""))
                    role = str(getattr(msg, "role", "assistant"))

            usage = getattr(raw_output, "usage", None) or raw_usage
            if usage:
                input_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
                output_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
                total_tokens = int(getattr(usage, "total_tokens", 0) or (input_tokens + output_tokens))
        elif isinstance(raw_output, str):
            content = raw_output
        else:
            content = str(raw_output)

        if total_tokens == 0:
            total_tokens = input_tokens + output_tokens

        # Redact any secrets leaked into returned content
        safe_content = IntegrationBoundary.sanitize_secrets(content)

        return NormalizedResponse(
            content=safe_content,
            role=role,
            model=model,
            provider=provider,
            input_tokens=max(0, input_tokens),
            output_tokens=max(0, output_tokens),
            total_tokens=max(0, total_tokens),
            raw_response=None,  # Do not leak raw third party object
        )

    @staticmethod
    def normalize_error(
        exc: Exception,
        provider: str,
        model: str,
    ) -> ProviderErrorPayload:
        """Translate third-party exception into canonical ProviderErrorPayload."""
        raw_msg = str(exc)
        safe_msg = IntegrationBoundary.sanitize_secrets(raw_msg)
        err_type = exc.__class__.__name__

        is_retryable = False
        status_code = getattr(exc, "status_code", None) or getattr(exc, "http_status", None)

        # Detect retryable error indicators
        if status_code in (429, 500, 502, 503, 504):
            is_retryable = True
        elif any(
            tok in err_type.lower() or tok in raw_msg.lower()
            for tok in ["rate_limit", "ratelimit", "timeout", "timedout", "connection", "overloaded"]
        ):
            is_retryable = True

        return ProviderErrorPayload(
            provider=provider,
            model=model,
            error_code=err_type.upper(),
            error_type=err_type,
            message=safe_msg,
            is_retryable=is_retryable,
            http_status=int(status_code) if status_code else None,
        )


__all__ = ["IntegrationBoundary"]
