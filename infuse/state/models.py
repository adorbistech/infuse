"""Normalized Data Models and Re-exports for Block 20 Execution State Engine."""

from datetime import datetime
from enum import IntEnum
from typing import Any, Dict, List, Optional
from pydantic import Field

from infuse.contracts.common import InfuseBaseModel, utc_now
from infuse.contracts.policy import GovernancePolicy
from infuse.contracts.state import ExecutionActionState, ExecutionState, ExecutionStateSnapshot
from infuse.economics.models import ExecutionEconomicSummary
from infuse.health.models import ExecutionHealthSummary
from infuse.observer.models import ExecutionTokenSummary
from infuse.tools.models import ExecutionToolSummary
from infuse.version import SCHEMA_VERSION
from infuse.web.models import ExecutionWebSummary


class StateSeverity(IntEnum):
    """Deterministic severity ranking for multiple concurrent state signals."""
    NORMAL = 1
    COST_PRESSURE = 2
    QUALITY_DEGRADED = 3
    PROVIDER_CONSTRAINED = 4
    RUNAWAY = 5


class ObservationBundle(InfuseBaseModel):
    """Container for all normalized observations associated with an execution."""
    execution_id: str = Field(..., description="Target execution identifier.")
    token_summary: Optional[ExecutionTokenSummary] = Field(
        default=None,
        description="Normalized token observation summary from Block 15."
    )
    economic_summary: Optional[ExecutionEconomicSummary] = Field(
        default=None,
        description="Normalized economic observation summary from Block 16."
    )
    health_summary: Optional[ExecutionHealthSummary] = Field(
        default=None,
        description="Normalized health observation summary from Block 17."
    )
    tool_summary: Optional[ExecutionToolSummary] = Field(
        default=None,
        description="Normalized tool activity observation summary from Block 18."
    )
    web_summary: Optional[ExecutionWebSummary] = Field(
        default=None,
        description="Normalized web activity observation summary from Block 19."
    )
    policy: Optional[GovernancePolicy] = Field(
        default=None,
        description="Active governance policy for threshold evaluation."
    )
    context_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional execution context or signals."
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        description="Timestamp of last observation bundle update."
    )


class ExecutionStateRecord(InfuseBaseModel):
    """Complete internal state record containing snapshot and full derivation signals."""
    snapshot: ExecutionStateSnapshot = Field(..., description="Active state snapshot.")
    bundle: ObservationBundle = Field(..., description="Source observations bundle.")
    transitions_count: int = Field(default=0, ge=0, description="Total state transitions recorded.")
    derivation_count: int = Field(default=0, ge=0, description="Total derivation evaluations.")
    schema_version: str = Field(default=SCHEMA_VERSION, description="Schema version.")


__all__ = [
    "ExecutionState",
    "ExecutionActionState",
    "ExecutionStateSnapshot",
    "StateSeverity",
    "ObservationBundle",
    "ExecutionStateRecord",
]
