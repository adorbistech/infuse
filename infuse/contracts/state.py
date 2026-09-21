"""Execution State contract definitions.

Execution State is the central normalized representation of execution health and behavior.
The future Execution State Engine owns state transitions; this module defines the data contract.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import Field

from infuse.contracts.common import InfuseBaseModel, utc_now


class ExecutionState(str, Enum):
    """Canonical internal execution states derived from observation signals."""
    NORMAL = "NORMAL"
    COST_PRESSURE = "COST_PRESSURE"
    RUNAWAY = "RUNAWAY"
    QUALITY_DEGRADED = "QUALITY_DEGRADED"
    PROVIDER_CONSTRAINED = "PROVIDER_CONSTRAINED"


class ExecutionActionState(str, Enum):
    """UI action states representing applied Governor interventions."""
    OPTIMIZED = "OPTIMIZED"
    THROTTLED = "THROTTLED"
    SWITCHED = "SWITCHED"
    STOPPED = "STOPPED"


class ExecutionStateSnapshot(InfuseBaseModel):
    """Immutable snapshot of an execution state at a point in time."""
    execution_id: str = Field(
        ...,
        description="Target execution identifier."
    )
    current_state: ExecutionState = Field(
        default=ExecutionState.NORMAL,
        description="Current active execution state."
    )
    previous_state: Optional[ExecutionState] = Field(
        default=None,
        description="Previous execution state before last transition."
    )
    entered_at: datetime = Field(
        default_factory=utc_now,
        description="Timestamp when current state was entered."
    )
    reason_codes: List[str] = Field(
        default_factory=list,
        description="Reason codes triggering the current state."
    )
    signals: Dict[str, Any] = Field(
        default_factory=dict,
        description="Aggregated signal values that caused the state transition."
    )
    transition_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Contextual metadata for the transition."
    )
