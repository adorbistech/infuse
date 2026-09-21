"""Execution Control Boundary contract definitions.

The Execution Control Boundary bridges Governor decisions and the physical execution runtime.
It determines which actions an agent adapter/runtime can actually perform and dispatches control commands.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import Field

from infuse.contracts.common import InfuseBaseModel, utc_now
from infuse.contracts.governor import GovernorAction


class ControlStatus(str, Enum):
    """Execution control operation status."""
    ACCEPTED = "ACCEPTED"
    COMPLETED = "COMPLETED"
    SUPPORTED = "SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    FAILED = "FAILED"


class ControlCapability(InfuseBaseModel):
    """Declared control capabilities of an agent adapter or execution runtime."""
    supports_cancel: bool = Field(
        default=False,
        description="Whether the runtime supports graceful mid-flight cancellation."
    )
    supports_throttle: bool = Field(
        default=False,
        description="Whether the runtime supports artificial pacing/rate throttling."
    )
    supports_next_step_switch: bool = Field(
        default=False,
        description="Whether the runtime supports model/provider routing changes at step boundaries."
    )
    supports_terminate: bool = Field(
        default=False,
        description="Whether the runtime supports hard process termination as a fallback."
    )
    supported_actions: List[GovernorAction] = Field(
        default_factory=lambda: [GovernorAction.CONTINUE],
        description="Explicit list of Governor actions supported by this runtime."
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Adapter-specific capability metadata."
    )


class ControlOperation(InfuseBaseModel):
    """Payload representing a control command dispatched to the Execution Control Boundary."""
    operation_id: str = Field(
        ...,
        description="Unique identifier for the control operation."
    )
    execution_id: str = Field(
        ...,
        description="Target execution identifier."
    )
    action: GovernorAction = Field(
        ...,
        description="Governor action being executed."
    )
    params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Action-specific parameters (e.g., throttle delay ms, new route target)."
    )
    dispatched_at: datetime = Field(
        default_factory=utc_now,
        description="Timestamp of dispatch."
    )


class ControlResult(InfuseBaseModel):
    """Result returned by the Execution Control Boundary following a control dispatch."""
    operation_id: str = Field(
        ...,
        description="Corresponding operation identifier."
    )
    execution_id: str = Field(
        ...,
        description="Target execution identifier."
    )
    action: GovernorAction = Field(
        ...,
        description="Attempted action."
    )
    status: ControlStatus = Field(
        ...,
        description="Outcome of the control operation."
    )
    message: Optional[str] = Field(
        default=None,
        description="Explanatory message or error details."
    )
    executed_at: datetime = Field(
        default_factory=utc_now,
        description="Timestamp when the control action completed."
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional execution metadata."
    )
