"""Error formatting and mapping for INFUSE MCP Server (Block 30)."""

from typing import Any, Dict, Optional
from pydantic import ValidationError as PydanticValidationError

from infuse.sdk.errors import (
    AuthenticationError,
    ConflictError,
    ControlExecutionError,
    InfuseSdkError,
    MalformedResponseError,
    NotFoundError,
    ServerError,
    TimeoutError,
    TransportError,
    UnsupportedControlError,
    ValidationError as SdkValidationError,
    redact_sdk_secrets,
)


def map_error_to_code(exc: Exception) -> str:
    """Map exception to a stable machine-readable error code string."""
    if isinstance(exc, (SdkValidationError, PydanticValidationError)):
        return "VALIDATION_ERROR"
    elif isinstance(exc, AuthenticationError):
        return "AUTHENTICATION_ERROR"
    elif isinstance(exc, NotFoundError):
        return "NOT_FOUND"
    elif isinstance(exc, UnsupportedControlError):
        return "UNSUPPORTED_OPERATION"
    elif isinstance(exc, ControlExecutionError):
        return "CONTROL_FAILURE"
    elif isinstance(exc, TransportError):
        return "TRANSPORT_ERROR"
    elif isinstance(exc, TimeoutError):
        return "TIMEOUT_ERROR"
    elif isinstance(exc, ServerError):
        return "SERVER_ERROR"
    elif isinstance(exc, ConflictError):
        return "CONFLICT_ERROR"
    elif isinstance(exc, MalformedResponseError):
        return "MALFORMED_RESPONSE"
    elif isinstance(exc, InfuseSdkError):
        return "SDK_ERROR"
    elif isinstance(exc, ValueError):
        return "INVALID_ARGUMENT"
    else:
        return "INTERNAL_ERROR"


def format_mcp_error(exc: Exception) -> Dict[str, Any]:
    """Format an exception into a safe, redacted, machine-readable MCP error dictionary."""
    code = map_error_to_code(exc)
    raw_message = str(exc)
    safe_message = redact_sdk_secrets(raw_message)

    err_dict: Dict[str, Any] = {
        "error": True,
        "code": code,
        "message": safe_message,
        "exception_type": exc.__class__.__name__,
    }

    details = getattr(exc, "details", None)
    if details:
        if isinstance(details, (str, bytes)):
            err_dict["details"] = redact_sdk_secrets(details)
        elif isinstance(details, dict):
            redacted_dict = {}
            for k, v in details.items():
                if any(sec in k.lower() for sec in ["key", "token", "secret", "password", "auth", "bearer"]):
                    redacted_dict[k] = "[REDACTED]"
                elif isinstance(v, str):
                    redacted_dict[k] = redact_sdk_secrets(v)
                else:
                    redacted_dict[k] = v
            err_dict["details"] = redacted_dict
        else:
            err_dict["details"] = details

    status_code = getattr(exc, "status_code", None)
    if status_code is not None:
        err_dict["status_code"] = status_code

    return err_dict


__all__ = [
    "map_error_to_code",
    "format_mcp_error",
]
