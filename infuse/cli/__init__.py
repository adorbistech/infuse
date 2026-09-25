"""INFUSE CLI Layer (Block 29).

Command-line interface over the frozen Block 28 SDK.
Provides human-friendly and machine-readable JSON operational commands
for agent execution, telemetry inspection, governance policy management,
and control boundary actions.
"""

from infuse.cli.exit_codes import (
    EXIT_AUTHENTICATION_ERROR,
    EXIT_CONFLICT,
    EXIT_CONTROL_ERROR,
    EXIT_GENERIC_ERROR,
    EXIT_MALFORMED_RESPONSE,
    EXIT_NOT_FOUND,
    EXIT_SERVER_ERROR,
    EXIT_SUCCESS,
    EXIT_TIMEOUT,
    EXIT_TRANSPORT_ERROR,
    EXIT_UNSUPPORTED,
    EXIT_USAGE_ERROR,
    EXIT_VALIDATION_ERROR,
    map_error_to_exit_code,
)
from infuse.cli.main import create_parser, main, run_cli

__all__ = [
    "run_cli",
    "create_parser",
    "main",
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
