"""Execution Lifecycle domain models and state tracking contracts."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import Field

from infuse.classifier.models import WorkloadClassification
from infuse.context.models import ExecutionContextRecord
from infuse.contracts.common import InfuseBaseModel
from infuse.contracts.execution import ExecutionResult
from infuse.providers.models import ProviderErrorRecord
from infuse.resolver.models import CapabilityResolutionResult
from infuse.router.models import RouteDecision, RouteTarget
from infuse.version import SCHEMA_VERSION


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class LifecycleState(str, Enum):
    """Authoritative lifecycle phase of an execution run."""
    CREATED = "CREATED"
    INITIALIZING = "INITIALIZING"
    ROUTED = "ROUTED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TERMINATED = "TERMINATED"


class LifecycleTransition(InfuseBaseModel):
    """Immutable record of an execution lifecycle transition."""
    execution_id: str = Field(..., description="Target execution identifier.")
    from_state: LifecycleState = Field(..., description="Previous lifecycle state.")
    to_state: LifecycleState = Field(..., description="New lifecycle state.")
    timestamp: str = Field(default_factory=_utc_now_iso, description="UTC ISO transition timestamp.")
    reason: Optional[str] = Field(default=None, description="Optional explanation for transition.")


class ExecutionLifecycleRecord(InfuseBaseModel):
    """Comprehensive lifecycle state envelope for an active or completed execution run."""
    execution_id: str = Field(..., description="Unique stable execution identifier.")
    request_id: str = Field(..., description="Originating request identifier.")
    task_id: str = Field(..., description="Task context identifier.")
    state: LifecycleState = Field(
        default=LifecycleState.CREATED,
        description="Current authoritative lifecycle state."
    )
    context: Optional[ExecutionContextRecord] = Field(
        default=None,
        description="Associated canonical ExecutionContextRecord (Block 07)."
    )
    classification: Optional[WorkloadClassification] = Field(
        default=None,
        description="Associated workload classification (Block 08)."
    )
    resolution: Optional[CapabilityResolutionResult] = Field(
        default=None,
        description="Associated capability resolution result (Block 10)."
    )
    route_decision: Optional[RouteDecision] = Field(
        default=None,
        description="Associated routing decision (Block 11)."
    )
    target: Optional[RouteTarget] = Field(
        default=None,
        description="Selected target for provider adapter execution (Block 12)."
    )
    result: Optional[ExecutionResult] = Field(
        default=None,
        description="Normalized universal execution result if completed or failed."
    )
    error: Optional[ProviderErrorRecord] = Field(
        default=None,
        description="Normalized provider error details if execution failed."
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Summary error message if execution failed."
    )
    cancellation_reason: Optional[str] = Field(
        default=None,
        description="Reason if execution was cancelled or terminated."
    )
    created_at: str = Field(
        default_factory=_utc_now_iso,
        description="Creation timestamp in UTC ISO format."
    )
    started_at: Optional[str] = Field(
        default=None,
        description="Execution invocation start timestamp in UTC ISO format."
    )
    completed_at: Optional[str] = Field(
        default=None,
        description="Execution termination / completion timestamp in UTC ISO format."
    )
    duration_ms: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Total round-trip lifecycle duration in milliseconds."
    )
    transitions: List[LifecycleTransition] = Field(
        default_factory=list,
        description="Ordered audit log of lifecycle phase transitions."
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional execution lifecycle metadata."
    )
    schema_version: str = Field(
        default=SCHEMA_VERSION,
        description="Schema contract version."
    )
