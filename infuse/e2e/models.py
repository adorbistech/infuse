from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import Field

from infuse.contracts.common import InfuseBaseModel, utc_now
from infuse.contracts.control import ControlOperation, ControlResult, ControlStatus
from infuse.contracts.events import ExecutionEvent
from infuse.contracts.execution import (
    ExecutionRequest,
    ExecutionResult,
)
from infuse.contracts.governor import GovernorAction, GovernorDecisionRecord
from infuse.contracts.policy import GovernancePolicy
from infuse.contracts.state import ExecutionState, ExecutionStateSnapshot
from infuse.version import SCHEMA_VERSION


class IntegrationScenario(InfuseBaseModel):
    """Declarative specification for an end-to-end integration test scenario."""
    scenario_id: str = Field(..., description="Unique scenario identifier.")
    name: str = Field(..., description="Human-readable scenario title.")
    description: str = Field(default="", description="Scenario description.")
    request: ExecutionRequest = Field(..., description="Input execution request.")
    policy: Optional[GovernancePolicy] = Field(default=None, description="Explicit test policy.")
    telemetry_events: List[ExecutionEvent] = Field(
        default_factory=list, description="Sequence of telemetry events to emit."
    )
    expected_final_state: Optional[ExecutionState] = Field(
        default=None, description="Expected derived execution state."
    )
    expected_governor_action: Optional[GovernorAction] = Field(
        default=None, description="Expected governor decision action."
    )
    expected_control_status: Optional[ControlStatus] = Field(
        default=None, description="Expected control dispatch status."
    )


class EndToEndExecutionAudit(InfuseBaseModel):
    """Comprehensive trace record auditing an entire end-to-end execution lifecycle."""
    execution_id: str = Field(..., description="Canonical execution identifier.")
    request_id: str = Field(..., description="Client request identifier.")
    started_at: datetime = Field(default_factory=utc_now)
    completed_at: Optional[datetime] = None
    
    # Path A: Execution & Routing
    workload_type: Optional[str] = None
    selected_provider: Optional[str] = None
    selected_model: Optional[str] = None
    agent_id: Optional[str] = None
    
    # Path B: Observation & Events
    events_recorded: List[ExecutionEvent] = Field(default_factory=list)
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    
    # Path C: State & Governance
    state_history: List[ExecutionStateSnapshot] = Field(default_factory=list)
    final_state: Optional[ExecutionState] = None
    governor_decisions: List[GovernorDecisionRecord] = Field(default_factory=list)
    control_results: List[ControlResult] = Field(default_factory=list)
    
    # Result
    result: Optional[ExecutionResult] = None
    success: bool = True
    error_message: Optional[str] = None
    schema_version: str = Field(default=SCHEMA_VERSION)


__all__ = [
    "IntegrationScenario",
    "EndToEndExecutionAudit",
]
