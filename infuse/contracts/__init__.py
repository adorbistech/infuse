"""INFUSE Architecture & Universal Contracts.

All external and internal subsystem interfaces in INFUSE are built upon these versioned,
language-neutral contract definitions.
"""

from infuse.contracts.common import InfuseBaseModel, utc_now
from infuse.contracts.governor import GovernorAction, GovernorDecision, GovernorDecisionRecord
from infuse.contracts.state import ExecutionState, ExecutionActionState, ExecutionStateSnapshot
from infuse.contracts.policy import (
    GovernancePolicy,
    BudgetControls,
    TokenControls,
    RequestControls,
    RuntimeControls,
    ProviderAccessControls,
    WebAccessControls,
    ToolAccessControls,
    RetryPolicy,
    AnomalyProtection,
    PolicyActionBindings,
)
from infuse.contracts.control import (
    ControlCapability,
    ControlOperation,
    ControlResult,
    ControlStatus,
)
from infuse.contracts.events import (
    EventType,
    EventSource,
    ExecutionEvent,
    TokenObservedPayload,
    ToolActivityPayload,
    WebActivityPayload,
    ProviderErrorPayload,
    StateChangedPayload,
    ControlActionIssuedPayload,
)
from infuse.contracts.execution import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    TaskContext,
    OperationRequest,
    ExecutionRequirements,
    ExecutionContext,
    NormalizedResponse,
    ExecutionTelemetry,
)
from infuse.contracts.capabilities import (
    AdapterType,
    AgentCapability,
    ProviderCapability,
    AdapterRegistration,
)
from infuse.contracts.frontend import (
    ExecutionSummaryViewModel,
    ExecutionMetricsViewModel,
    ExecutionStateViewModel,
    GovernorDecisionViewModel,
    ProviderModelHealthViewModel,
    ExecutionTimelineEventViewModel,
    ExecutionHistoryItemViewModel,
    GovernancePolicyViewModel,
)

__all__ = [
    # Base
    "InfuseBaseModel",
    "utc_now",
    # Governor
    "GovernorAction",
    "GovernorDecision",
    "GovernorDecisionRecord",
    # State
    "ExecutionState",
    "ExecutionActionState",
    "ExecutionStateSnapshot",
    # Policy
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
    # Control Boundary
    "ControlCapability",
    "ControlOperation",
    "ControlResult",
    "ControlStatus",
    # Events
    "EventType",
    "EventSource",
    "ExecutionEvent",
    "TokenObservedPayload",
    "ToolActivityPayload",
    "WebActivityPayload",
    "ProviderErrorPayload",
    "StateChangedPayload",
    "ControlActionIssuedPayload",
    # Universal Execution
    "ExecutionRequest",
    "ExecutionResult",
    "ExecutionStatus",
    "TaskContext",
    "OperationRequest",
    "ExecutionRequirements",
    "ExecutionContext",
    "NormalizedResponse",
    "ExecutionTelemetry",
    # Capabilities
    "AdapterType",
    "AgentCapability",
    "ProviderCapability",
    "AdapterRegistration",
    # Frontend ViewModels
    "ExecutionSummaryViewModel",
    "ExecutionMetricsViewModel",
    "ExecutionStateViewModel",
    "GovernorDecisionViewModel",
    "ProviderModelHealthViewModel",
    "ExecutionTimelineEventViewModel",
    "ExecutionHistoryItemViewModel",
    "GovernancePolicyViewModel",
]
