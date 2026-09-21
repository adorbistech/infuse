"""Execution Event contract definitions.

Execution events form the immutable observation backbone of INFUSE.
Events are published to the Event Bus and fanned out to observers without tight coupling.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import Field

from infuse.contracts.common import InfuseBaseModel, utc_now
from infuse.contracts.governor import GovernorAction, GovernorDecision
from infuse.contracts.state import ExecutionState


class EventType(str, Enum):
    """Canonical event taxonomy for INFUSE execution observation."""
    EXECUTION_STARTED = "ExecutionStarted"
    EXECUTION_COMPLETED = "ExecutionCompleted"
    EXECUTION_FAILED = "ExecutionFailed"
    TOKEN_OBSERVED = "TokenObserved"
    USAGE_UPDATED = "UsageUpdated"
    TOOL_CALLED = "ToolCalled"
    TOOL_COMPLETED = "ToolCompleted"
    WEB_REQUEST = "WebRequest"
    WEB_RESPONSE = "WebResponse"
    RETRY_STARTED = "RetryStarted"
    PROVIDER_ERROR = "ProviderError"
    STATE_CHANGED = "StateChanged"
    GOVERNOR_DECISION = "GovernorDecision"
    CONTROL_ACTION_ISSUED = "ControlActionIssued"


class EventSource(str, Enum):
    """Originator of the execution event."""
    AGENT = "AGENT"
    PROVIDER = "PROVIDER"
    RUNTIME = "RUNTIME"
    GOVERNOR = "GOVERNOR"
    OBSERVER = "OBSERVER"
    SYSTEM = "SYSTEM"


class TokenObservedPayload(InfuseBaseModel):
    """Payload for TokenObserved events during streaming or step completion."""
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    cached_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    is_authoritative: bool = Field(
        default=False,
        description="True if returned directly by provider usage payload; False if stream-estimated."
    )
    provider: Optional[str] = None
    model: Optional[str] = None


class ToolActivityPayload(InfuseBaseModel):
    """Payload for ToolCalled and ToolCompleted events."""
    tool_name: str
    call_id: Optional[str] = None
    arguments: Optional[Dict[str, Any]] = None
    success: Optional[bool] = None
    duration_ms: Optional[float] = None
    error: Optional[str] = None


class WebActivityPayload(InfuseBaseModel):
    """Payload for WebRequest and WebResponse events."""
    url: str
    method: str = "GET"
    status_code: Optional[int] = None
    bytes_transferred: Optional[int] = None
    duration_ms: Optional[float] = None


class ProviderErrorPayload(InfuseBaseModel):
    """Payload for ProviderError events."""
    provider: str
    model: Optional[str] = None
    error_code: Optional[str] = None
    error_type: str
    message: str
    is_retryable: bool = False
    http_status: Optional[int] = None


class StateChangedPayload(InfuseBaseModel):
    """Payload for StateChanged events."""
    previous_state: Optional[ExecutionState] = None
    new_state: ExecutionState
    reason_codes: List[str] = Field(default_factory=list)
    signals: Dict[str, Any] = Field(default_factory=dict)


class ControlActionIssuedPayload(InfuseBaseModel):
    """Payload for ControlActionIssued events."""
    action: GovernorAction
    operation_id: str
    params: Dict[str, Any] = Field(default_factory=dict)
    target_boundary: str


class ExecutionEvent(InfuseBaseModel):
    """Canonical immutable event envelope."""
    event_id: str = Field(
        ...,
        description="Unique identifier for this specific event."
    )
    execution_id: str = Field(
        ...,
        description="Execution run with which this event is associated."
    )
    timestamp: datetime = Field(
        default_factory=utc_now,
        description="UTC timestamp when the event occurred."
    )
    type: EventType = Field(
        ...,
        description="Categorical event type."
    )
    source: EventSource = Field(
        default=EventSource.SYSTEM,
        description="Subsystem that generated the event."
    )
    sequence: int = Field(
        ...,
        ge=0,
        description="Monotonically increasing sequence number within this execution."
    )
    payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="Typed or structured event payload."
    )
