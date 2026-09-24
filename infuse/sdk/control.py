"""Execution Control Client for the INFUSE SDK (Block 28).

Provides typed access to execution control operations (cancel, terminate, throttle, switch).
All control operations flow strictly through the Execution Control Boundary (Block 22).
The SDK NEVER manipulates agent runtimes or subprocesses directly.
"""

from typing import Any, Dict, List, Optional

from infuse.contracts.control import (
    ControlCapability,
    ControlOperation,
    ControlResult,
    ControlStatus,
)
from infuse.contracts.governor import GovernorAction
from infuse.control.boundary import ExecutionControlBoundary
from infuse.control.interfaces import IExecutionControlBoundary
from infuse.sdk.errors import (
    ControlExecutionError,
    UnsupportedControlError,
)
from infuse.sdk.transport import ITransport


class ControlClient:
    """Developer-facing interface for Execution Control operations."""

    def __init__(
        self,
        transport: ITransport,
        boundary: Optional[IExecutionControlBoundary] = None,
    ) -> None:
        self._transport = transport
        self._boundary = boundary or ExecutionControlBoundary()

    def dispatch(
        self,
        execution_id: str,
        action: GovernorAction,
        params: Optional[Dict[str, Any]] = None,
        operation_id: Optional[str] = None,
    ) -> ControlResult:
        """Dispatch a control command through the Execution Control Boundary.

        The boundary verifies runtime capability before dispatching.
        Unsupported actions strictly return ControlStatus.UNSUPPORTED.
        """
        if not execution_id or not execution_id.strip():
            raise ValueError("execution_id must not be empty.")
        if action is None:
            raise ValueError("action must not be None.")

        clean_id = execution_id.strip()
        gov_action = GovernorAction(action) if not isinstance(action, GovernorAction) else action

        # Dispatch through the authoritative Control Boundary
        result = self._boundary.dispatch_control(
            execution_id=clean_id,
            action=gov_action,
            params=params,
            operation_id=operation_id,
        )

        return result

    def cancel(self, execution_id: str) -> ControlResult:
        """Request graceful cancellation of an active execution."""
        return self.dispatch(
            execution_id=execution_id,
            action=GovernorAction.STOP,
            params={"hard": False},
        )

    def terminate(self, execution_id: str) -> ControlResult:
        """Request hard termination of an active execution."""
        return self.dispatch(
            execution_id=execution_id,
            action=GovernorAction.STOP,
            params={"hard": True, "terminate": True},
        )

    def throttle(self, execution_id: str, delay_ms: int = 1000) -> ControlResult:
        """Request execution pacing / delay throttling."""
        return self.dispatch(
            execution_id=execution_id,
            action=GovernorAction.THROTTLE,
            params={"delay_ms": delay_ms},
        )

    def switch(self, execution_id: str, target_model: str) -> ControlResult:
        """Request mid-execution step model / route switch."""
        return self.dispatch(
            execution_id=execution_id,
            action=GovernorAction.SWITCH,
            params={"target_model": target_model},
        )

    def get_capability(self, execution_id: str) -> Optional[ControlCapability]:
        """Retrieve declared control capabilities for a given execution."""
        return self._boundary.get_capability(execution_id)

    def get_latest(self, execution_id: str) -> Optional[ControlResult]:
        """Retrieve the most recent control result for an execution."""
        return self._boundary.get_latest_result(execution_id)

    def get_history(self, execution_id: str) -> List[Any]:
        """Retrieve full chronological control audit history for an execution."""
        return self._boundary.get_control_history(execution_id)


__all__ = ["ControlClient"]
