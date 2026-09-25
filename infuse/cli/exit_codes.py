"""INFUSE CLI Exit Codes (Block 29).

Defines deterministic exit codes for operational scripting, automation,
and CI/CD pipelines.
"""

import sys
from typing import Optional

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
    ValidationError,
)

# Deterministic Exit Codes Contract
EXIT_SUCCESS: int = 0
EXIT_GENERIC_ERROR: int = 1
EXIT_USAGE_ERROR: int = 2
EXIT_VALIDATION_ERROR: int = 2
EXIT_AUTHENTICATION_ERROR: int = 3
EXIT_NOT_FOUND: int = 4
EXIT_UNSUPPORTED: int = 5
EXIT_CONTROL_ERROR: int = 6
EXIT_TRANSPORT_ERROR: int = 7
EXIT_TIMEOUT: int = 8
EXIT_SERVER_ERROR: int = 9
EXIT_CONFLICT: int = 10
EXIT_MALFORMED_RESPONSE: int = 11


def map_error_to_exit_code(exc: BaseException) -> int:
    """Map typed SDK or runtime exceptions into deterministic exit codes."""
    if isinstance(exc, SystemExit):
        return exc.code if isinstance(exc.code, int) else EXIT_GENERIC_ERROR
    if isinstance(exc, AuthenticationError):
        return EXIT_AUTHENTICATION_ERROR
    if isinstance(exc, ValidationError):
        return EXIT_VALIDATION_ERROR
    if isinstance(exc, NotFoundError):
        return EXIT_NOT_FOUND
    if isinstance(exc, UnsupportedControlError):
        return EXIT_UNSUPPORTED
    if isinstance(exc, ControlExecutionError):
        return EXIT_CONTROL_ERROR
    if isinstance(exc, TransportError):
        return EXIT_TRANSPORT_ERROR
    if isinstance(exc, TimeoutError):
        return EXIT_TIMEOUT
    if isinstance(exc, ServerError):
        return EXIT_SERVER_ERROR
    if isinstance(exc, ConflictError):
        return EXIT_CONFLICT
    if isinstance(exc, MalformedResponseError):
        return EXIT_MALFORMED_RESPONSE
    if isinstance(exc, (ValueError, KeyError)):
        return EXIT_USAGE_ERROR
    return EXIT_GENERIC_ERROR


__all__ = [
    "EXIT_SUCCESS",
    "EXIT_GENERIC_ERROR",
    "EXIT_USAGE_ERROR",
    "EXIT_VALIDATION_ERROR",
    "EXIT_AUTHENTICATION_ERROR",
    "EXIT_NOT_FOUND",
    "EXIT_UNSUPPORTED",
    "EXIT_CONTROL_ERROR",
    "EXIT_TRANSPORT_ERROR",
    "EXIT_TIMEOUT",
    "EXIT_SERVER_ERROR",
    "EXIT_CONFLICT",
    "EXIT_MALFORMED_RESPONSE",
    "map_error_to_exit_code",
]
