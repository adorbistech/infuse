"""Typed error hierarchy for the INFUSE SDK (Block 28).

All exceptions preserve machine-readable metadata and ensure sensitive
credentials (tokens, API keys, passwords) are safely redacted.
"""

import re
from typing import Any, Dict, Optional


def redact_sdk_secrets(text: Optional[str]) -> str:
    """Redact sensitive API keys, bearer tokens, and secrets from error messages."""
    if not text:
        return ""
    redacted = text
    # Key-value secret patterns
    redacted = re.sub(
        r"(?i)(api[_-]?key|secret|token|password|auth|bearer)\s*[:=]\s*['\"]?([A-Za-z0-9_\-\.]{8,})['\"]?",
        r"\1: [REDACTED]",
        redacted,
    )
    # Bearer tokens
    redacted = re.sub(
        r"(?i)\bbearer\s+([A-Za-z0-9_\-\.]{8,})",
        "Bearer [REDACTED]",
        redacted,
    )
    # Standalone token formats
    redacted = re.sub(r"sk-[A-Za-z0-9_-]{10,}", "[REDACTED]", redacted)
    redacted = re.sub(r"infuse-[A-Za-z0-9_-]{10,}", "[REDACTED]", redacted)
    return redacted


class InfuseSdkError(Exception):
    """Base exception for all INFUSE SDK errors."""

    def __init__(
        self,
        message: str,
        code: str = "SDK_ERROR",
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        clean_msg = redact_sdk_secrets(message)
        super().__init__(clean_msg)
        self.message = clean_msg
        self.code = code
        self.status_code = status_code
        self.details = details or {}

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(code='{self.code}', status_code={self.status_code}, message='{self.message}')"


class TransportError(InfuseSdkError):
    """Raised when transport communication fails (network, connection refused, DNS)."""

    def __init__(
        self,
        message: str = "Transport communication failed.",
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message=message, code="TRANSPORT_ERROR", status_code=status_code, details=details)


class AuthenticationError(InfuseSdkError):
    """Raised when authentication credentials are missing, invalid, or unauthorized."""

    def __init__(
        self,
        message: str = "Authentication failed or credentials unauthorized.",
        status_code: int = 401,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message=message, code="AUTHENTICATION_ERROR", status_code=status_code, details=details)


class ValidationError(InfuseSdkError):
    """Raised when request payload or parameters fail schema validation."""

    def __init__(
        self,
        message: str = "Request validation failed.",
        status_code: int = 422,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message=message, code="VALIDATION_ERROR", status_code=status_code, details=details)


class NotFoundError(InfuseSdkError):
    """Raised when requested execution, policy, or resource is not found."""

    def __init__(
        self,
        message: str = "Requested resource was not found.",
        status_code: int = 404,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message=message, code="NOT_FOUND", status_code=status_code, details=details)


class ConflictError(InfuseSdkError):
    """Raised when an operation conflicts with existing resource state."""

    def __init__(
        self,
        message: str = "Operation conflict with existing resource state.",
        status_code: int = 409,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message=message, code="CONFLICT", status_code=status_code, details=details)


class UnsupportedControlError(InfuseSdkError):
    """Raised when attempting a control action not supported by the execution runtime."""

    def __init__(
        self,
        message: str = "Control action is unsupported by target runtime.",
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message=message, code="UNSUPPORTED_CONTROL", status_code=status_code, details=details)


class ControlExecutionError(InfuseSdkError):
    """Raised when a control operation fails during execution."""

    def __init__(
        self,
        message: str = "Control operation execution failed.",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message=message, code="CONTROL_EXECUTION_ERROR", status_code=status_code, details=details)


class MalformedResponseError(InfuseSdkError):
    """Raised when server response cannot be decoded or parsed into expected contract."""

    def __init__(
        self,
        message: str = "Server returned a malformed or non-decodable response.",
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message=message, code="MALFORMED_RESPONSE", status_code=status_code, details=details)


class TimeoutError(InfuseSdkError):
    """Raised when an operation or transport request times out."""

    def __init__(
        self,
        message: str = "Operation timed out.",
        status_code: int = 504,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message=message, code="TIMEOUT", status_code=status_code, details=details)


class ServerError(InfuseSdkError):
    """Raised when INFUSE server or internal service encounters an internal error."""

    def __init__(
        self,
        message: str = "Internal server error occurred.",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message=message, code="INTERNAL_ERROR", status_code=status_code, details=details)


__all__ = [
    "InfuseSdkError",
    "TransportError",
    "AuthenticationError",
    "ValidationError",
    "NotFoundError",
    "ConflictError",
    "UnsupportedControlError",
    "ControlExecutionError",
    "MalformedResponseError",
    "TimeoutError",
    "ServerError",
    "redact_sdk_secrets",
]
