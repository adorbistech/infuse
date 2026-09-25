"""Execution control commands for INFUSE CLI (Block 29)."""

import sys
from typing import Optional

from infuse.cli.exit_codes import (
    EXIT_CONTROL_ERROR,
    EXIT_SUCCESS,
    EXIT_UNSUPPORTED,
)
from infuse.cli.formatter import format_control_result
from infuse.contracts.control import ControlResult, ControlStatus
from infuse.contracts.governor import GovernorAction
from infuse.sdk.client import InfuseClient


def _handle_control_outcome(result: ControlResult, json_mode: bool = False) -> int:
    """Print control result and return corresponding deterministic exit code."""
    print(format_control_result(result, json_mode=json_mode))
    if result.status == ControlStatus.UNSUPPORTED:
        return EXIT_UNSUPPORTED
    if result.status == ControlStatus.FAILED:
        return EXIT_CONTROL_ERROR
    return EXIT_SUCCESS


def handle_control_cancel(
    client: InfuseClient,
    execution_id: str,
    reason: Optional[str] = None,
    json_mode: bool = False,
) -> int:
    """Request graceful cancellation of an execution."""
    result = client.control.dispatch(
        execution_id=execution_id,
        action=GovernorAction.STOP,
        params={"hard": False, "reason": reason} if reason else {"hard": False},
    )
    return _handle_control_outcome(result, json_mode=json_mode)


def handle_control_terminate(
    client: InfuseClient,
    execution_id: str,
    reason: Optional[str] = None,
    json_mode: bool = False,
) -> int:
    """Request hard termination of an execution."""
    result = client.control.dispatch(
        execution_id=execution_id,
        action=GovernorAction.STOP,
        params={"hard": True, "terminate": True, "reason": reason} if reason else {"hard": True, "terminate": True},
    )
    return _handle_control_outcome(result, json_mode=json_mode)


def handle_control_throttle(
    client: InfuseClient,
    execution_id: str,
    delay_ms: int = 1000,
    reason: Optional[str] = None,
    json_mode: bool = False,
) -> int:
    """Request pacing / delay throttling for an execution."""
    result = client.control.dispatch(
        execution_id=execution_id,
        action=GovernorAction.THROTTLE,
        params={"delay_ms": delay_ms, "reason": reason} if reason else {"delay_ms": delay_ms},
    )
    return _handle_control_outcome(result, json_mode=json_mode)


def handle_control_switch(
    client: InfuseClient,
    execution_id: str,
    target_model: str,
    target_provider: Optional[str] = None,
    reason: Optional[str] = None,
    json_mode: bool = False,
) -> int:
    """Request route/model switch for an execution."""
    params = {"target_model": target_model}
    if target_provider:
        params["target_provider"] = target_provider
    if reason:
        params["reason"] = reason

    result = client.control.dispatch(
        execution_id=execution_id,
        action=GovernorAction.SWITCH,
        params=params,
    )
    return _handle_control_outcome(result, json_mode=json_mode)


__all__ = [
    "handle_control_cancel",
    "handle_control_terminate",
    "handle_control_throttle",
    "handle_control_switch",
]
