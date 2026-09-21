"""Governor action and decision contract definitions.

The Governor is the sole control authority in the INFUSE architecture.
Observers produce signals; the Governor evaluates policy and state to emit decisions.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import Field

from infuse.contracts.common import InfuseBaseModel, utc_now


class GovernorAction(str, Enum):
    """Canonical Governor action vocabulary across all INFUSE subsystems."""
    CONTINUE = "CONTINUE"
    OPTIMIZE = "OPTIMIZE"
    ESCALATE = "ESCALATE"
    DOWNGRADE = "DOWNGRADE"
    SWITCH = "SWITCH"
    THROTTLE = "THROTTLE"
    STOP = "STOP"


class GovernorDecision(InfuseBaseModel):
    """Normalized Governor decision payload attached to execution results or emitted as events."""
    action: GovernorAction = Field(
        default=GovernorAction.CONTINUE,
        description="The control action decided by the Governor."
    )
    reason_codes: List[str] = Field(
        default_factory=list,
        description="Machine-readable taxonomy codes explaining the rationale for the decision."
    )
    message: Optional[str] = Field(
        default=None,
        description="Human-readable explanation of why the action was selected."
    )
    suggested_route: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Suggested provider/model route when action is SWITCH, OPTIMIZE, or DOWNGRADE."
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional evaluation metadata (e.g. threshold breaches, signal scores)."
    )


class GovernorDecisionRecord(InfuseBaseModel):
    """Immutable audit record of an evaluated Governor decision."""
    decision_id: str = Field(
        ...,
        description="Unique identifier for this decision evaluation."
    )
    execution_id: str = Field(
        ...,
        description="Target execution identifier."
    )
    action: GovernorAction = Field(
        ...,
        description="The control action decided by the Governor."
    )
    reason_codes: List[str] = Field(
        default_factory=list,
        description="Machine-readable reason codes."
    )
    message: Optional[str] = Field(
        default=None,
        description="Human-readable decision rationale."
    )
    evaluated_at: datetime = Field(
        default_factory=utc_now,
        description="Timestamp when the Governor evaluation occurred."
    )
    evaluated_state: str = Field(
        ...,
        description="Execution state at the time of evaluation."
    )
    signals: Dict[str, Any] = Field(
        default_factory=dict,
        description="Snapshot of active signals consumed during evaluation."
    )
    effective_policy_id: Optional[str] = Field(
        default=None,
        description="Identifier of the effective policy evaluated against."
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional audit metadata."
    )
