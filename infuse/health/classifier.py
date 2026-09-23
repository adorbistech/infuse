"""Deterministic Error Categorization for Block 17 Health Engine."""

from typing import Optional
from infuse.health.models import ErrorCategory


def classify_error_category(
    error_type: Optional[str] = None,
    error_code: Optional[str] = None,
    message: Optional[str] = None,
    http_status: Optional[int] = None
) -> ErrorCategory:
    """Deterministically classify an observed error into a normalized ErrorCategory."""
    # 1. Check HTTP Status code if present
    if http_status is not None:
        if http_status in (408, 504):
            return ErrorCategory.TIMEOUT
        if http_status == 429:
            return ErrorCategory.RATE_LIMIT
        if http_status in (401, 403):
            return ErrorCategory.AUTHENTICATION
        if http_status in (502, 503):
            return ErrorCategory.UNAVAILABLE
        if http_status in (400, 422):
            return ErrorCategory.INVALID_REQUEST
        if http_status == 500:
            return ErrorCategory.PROVIDER_ERROR

    # 2. Check textual signals across error_type, error_code, message
    combined = f"{error_type or ''} {error_code or ''} {message or ''}".lower()

    if any(k in combined for k in ("timeout", "timed out", "timed_out", "deadline")):
        return ErrorCategory.TIMEOUT
    if any(k in combined for k in ("rate_limit", "rate limit", "quota", "too many requests", "429")):
        return ErrorCategory.RATE_LIMIT
    if any(k in combined for k in ("auth", "unauthorized", "forbidden", "api_key", "api key", "credential", "permission", "401", "403")):
        return ErrorCategory.AUTHENTICATION
    if any(k in combined for k in ("unavailable", "bad_gateway", "overloaded", "capacity", "503", "502")):
        return ErrorCategory.UNAVAILABLE
    if any(k in combined for k in ("invalid_request", "bad request", "invalid argument", "schema_validation", "400")):
        return ErrorCategory.INVALID_REQUEST
    if any(k in combined for k in ("provider_error", "upstream", "internal server error", "500")):
        return ErrorCategory.PROVIDER_ERROR
    if any(k in combined for k in ("execution_error", "resolution_error", "runtime_error")):
        return ErrorCategory.EXECUTION_ERROR

    return ErrorCategory.UNKNOWN
