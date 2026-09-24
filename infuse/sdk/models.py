"""SDK Data Models and canonical contract re-exports (Block 28).

Preserves 100% fidelity with frozen Block 00-27 contracts.
"""

from typing import Any, Dict, List, Optional
from pydantic import Field

from infuse.contracts.common import InfuseBaseModel, utc_now
from infuse.contracts.capabilities import (
    AdapterRegistration,
    AdapterType,
    AgentCapability,
)
from infuse.contracts.control import (
    ControlCapability,
    ControlOperation,
    ControlResult,
    ControlStatus,
)
from infuse.contracts.events import (
    ControlActionIssuedPayload,
    EventSource,
    EventType,
    ExecutionEvent,
    ProviderErrorPayload,
    StateChangedPayload,
    TokenObservedPayload,
    ToolActivityPayload,
    WebActivityPayload,
)
from infuse.contracts.execution import (
    ExecutionContext,
    ExecutionRequirements,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    ExecutionTelemetry,
    NormalizedResponse,
    OperationRequest,
    TaskContext,
)
from infuse.contracts.frontend import (
    ExecutionHistoryItemViewModel,
    ExecutionMetricsViewModel,
    ExecutionStateViewModel,
    ExecutionSummaryViewModel,
    ExecutionTimelineEventViewModel,
    GovernancePolicyViewModel,
    GovernorDecisionViewModel,
    ProviderModelHealthViewModel,
)
from infuse.contracts.governor import (
    GovernorAction,
    GovernorDecision,
)
from infuse.contracts.policy import (
    AnomalyProtection,
    BudgetControls,
    GovernancePolicy,
    PolicyActionBindings,
    ProviderAccessControls,
    RequestControls,
    RetryPolicy,
    RuntimeControls,
    TokenControls,
    ToolAccessControls,
    WebAccessControls,
)
from infuse.contracts.state import (
    ExecutionState,
)
from infuse.version import SCHEMA_VERSION


class ExecutionListResponse(InfuseBaseModel):
    """Response envelope for listing execution summaries."""
    items: List[ExecutionSummaryViewModel] = Field(default_factory=list)
    total: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1)
    offset: int = Field(default=0, ge=0)
    schema_version: str = Field(default=SCHEMA_VERSION)


class PolicyListResponse(InfuseBaseModel):
    """Response envelope for retrieving policies."""
    policies: List[GovernancePolicy] = Field(default_factory=list)
    active_policy: Optional[GovernancePolicy] = Field(default=None)
    schema_version: str = Field(default=SCHEMA_VERSION)


class EventIngestResponse(InfuseBaseModel):
    """Response envelope from ingesting an execution telemetry event."""
    status: str = Field(default="INGESTED")
    event_id: str
    execution_id: str
    schema_version: str = Field(default=SCHEMA_VERSION)


class StateInfo(InfuseBaseModel):
    """Execution state observation details."""
    execution_id: str
    state: ExecutionState
    reason_codes: List[str] = Field(default_factory=list)
    boundary_threshold_percent: float = 80.0
    evaluated_at: Optional[str] = None


class GovernorInfo(InfuseBaseModel):
    """Governor decision observation details."""
    execution_id: str
    action: GovernorAction
    reason_codes: List[str] = Field(default_factory=list)
    action_banner_title: Optional[str] = None
    action_banner_description: Optional[str] = None
    recent_decisions: List[Dict[str, Any]] = Field(default_factory=list)


__all__ = [
    # Core Contracts
    "ExecutionRequest",
    "ExecutionResult",
    "ExecutionStatus",
    "TaskContext",
    "OperationRequest",
    "ExecutionRequirements",
    "ExecutionContext",
    "NormalizedResponse",
    "ExecutionTelemetry",
    "ExecutionState",
    "GovernancePolicy",
    "BudgetControls",
    "TokenControls",
    "RequestControls",
    "RuntimeControls",
    "ProviderAccessControls",
    "WebAccessControls",
    "ToolAccessControls",
    "RetryPolicy",
    "AnomalyProtection",
    "PolicyActionBindings",
    "ExecutionEvent",
    "EventType",
    "EventSource",
    "TokenObservedPayload",
    "ToolActivityPayload",
    "WebActivityPayload",
    "ProviderErrorPayload",
    "StateChangedPayload",
    "ControlActionIssuedPayload",
    "GovernorAction",
    "GovernorDecision",
    "ControlCapability",
    "ControlOperation",
    "ControlResult",
    "ControlStatus",
    "AgentCapability",
    "AdapterRegistration",
    "AdapterType",
    # ViewModels
    "ExecutionSummaryViewModel",
    "ExecutionMetricsViewModel",
    "ExecutionStateViewModel",
    "GovernorDecisionViewModel",
    "ProviderModelHealthViewModel",
    "ExecutionTimelineEventViewModel",
    "ExecutionHistoryItemViewModel",
    "GovernancePolicyViewModel",
    # SDK Envelopes
    "ExecutionListResponse",
    "PolicyListResponse",
    "EventIngestResponse",
    "StateInfo",
    "GovernorInfo",
]
