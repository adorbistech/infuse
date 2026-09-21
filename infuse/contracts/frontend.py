"""Frontend Data & ViewModel Contract definitions.

These models define the exact normalized data shapes delivered to the INFUSE Stitch frontend.
The UI consumes these ViewModels via API rather than querying internal databases or runtime objects directly.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import Field

from infuse.contracts.common import InfuseBaseModel, utc_now
from infuse.contracts.events import EventType
from infuse.contracts.governor import GovernorAction
from infuse.contracts.policy import GovernancePolicy
from infuse.contracts.state import ExecutionState


class ExecutionSummaryViewModel(InfuseBaseModel):
    """Top context card on the Information screen."""
    execution_id: str
    agent_name: str
    task_description: str
    status: str
    is_live: bool = True
    provider: str
    model: str
    routing_mode: str = "Auto-Governor"
    isolation_pool: Optional[str] = None
    started_at: datetime = Field(default_factory=utc_now)
    runtime_seconds: int = 0
    formatted_runtime: str = "00m 00s"


class ExecutionMetricsViewModel(InfuseBaseModel):
    """8-Card metric grid and time-series telemetry on Information screen."""
    input_tokens: int = 0
    cached_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    current_cost_usd: float = 0.0
    budget_limit_usd: Optional[float] = None
    budget_consumed_percent: float = 0.0
    requests_count: int = 0
    requests_per_minute: float = 0.0
    errors_count: int = 0
    retries_count: int = 0
    web_requests_count: int = 0
    tool_calls_count: int = 0
    # Chart series data
    token_growth_series: List[Dict[str, Any]] = Field(default_factory=list)
    cost_series: List[Dict[str, Any]] = Field(default_factory=list)


class ExecutionStateViewModel(InfuseBaseModel):
    """Execution state section with status badge, pill selector, and rationale."""
    current_state: ExecutionState = ExecutionState.NORMAL
    state_display_name: str = "NORMAL"
    description: str = "Execution progressing within standard policy bounds."
    policy_boundary_threshold_percent: float = 80.0
    reason_codes: List[str] = Field(default_factory=list)
    available_states: List[ExecutionState] = Field(
        default_factory=lambda: list(ExecutionState)
    )


class GovernorDecisionViewModel(InfuseBaseModel):
    """Governor panel on Information screen."""
    current_action: GovernorAction = GovernorAction.CONTINUE
    action_banner_title: str = "Active Regulation: Standard"
    action_banner_description: str = "Execution permitted to continue without intervention."
    reason_codes: List[str] = Field(default_factory=list)
    recent_decisions: List[Dict[str, Any]] = Field(default_factory=list)


class ProviderModelHealthViewModel(InfuseBaseModel):
    """Provider / Model health metrics panel."""
    provider: str
    model: str
    latency_ms: float = 0.0
    availability_percent: float = 100.0
    error_rate_percent: float = 0.0
    status: str = "HEALTHY"


class ExecutionTimelineEventViewModel(InfuseBaseModel):
    """Single event item rendered in the Execution Timeline."""
    event_id: str
    timestamp: datetime = Field(default_factory=utc_now)
    time_offset: str = "+00:00"
    event_type: EventType
    title: str
    description: str
    is_state_change: bool = False
    is_governor_decision: bool = False
    badge_label: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ExecutionHistoryItemViewModel(InfuseBaseModel):
    """Row item in the Execution History table."""
    execution_id: str
    agent_name: str
    task_preview: str
    provider: str
    model: str
    status: str
    state: ExecutionState
    total_tokens: int
    cost_usd: float
    runtime_formatted: str
    created_at: datetime = Field(default_factory=utc_now)


class GovernancePolicyViewModel(InfuseBaseModel):
    """ViewModel for Governance / Settings screen (Policy Form)."""
    policy: GovernancePolicy
    guardrail_strictness_index: str = "99.98% Strict"
    is_editing: bool = False
    available_actions: List[GovernorAction] = Field(
        default_factory=lambda: [
            GovernorAction.OPTIMIZE,
            GovernorAction.SWITCH,
            GovernorAction.THROTTLE,
            GovernorAction.STOP,
            GovernorAction.CONTINUE,
        ]
    )
