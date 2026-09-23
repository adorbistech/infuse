"""Canonical Event Models for Block 14 Event Bus.

Re-exports and reinforces frozen Block 00 Event Contract without modifications.
"""

from typing import Any, Dict, List, Optional
from pydantic import Field

from infuse.contracts.common import InfuseBaseModel
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


class ExecutionStartedPayload(InfuseBaseModel):
    """Standard payload structure for ExecutionStarted lifecycle events."""
    request_id: str = Field(..., description="Request identifier.")
    task_id: str = Field(..., description="Task identifier.")
    provider_id: Optional[str] = Field(default=None, description="Selected provider identifier.")
    model_id: Optional[str] = Field(default=None, description="Selected model identifier.")
    session_id: Optional[str] = Field(default=None, description="Session identifier.")
    workflow_id: Optional[str] = Field(default=None, description="Workflow identifier.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata dictionary.")


class ExecutionCompletedPayload(InfuseBaseModel):
    """Standard payload structure for ExecutionCompleted lifecycle events."""
    request_id: str = Field(..., description="Request identifier.")
    task_id: str = Field(..., description="Task identifier.")
    provider_id: Optional[str] = Field(default=None, description="Executing provider identifier.")
    model_id: Optional[str] = Field(default=None, description="Executing model identifier.")
    duration_ms: float = Field(default=0.0, ge=0.0, description="Round-trip latency in milliseconds.")
    input_tokens: int = Field(default=0, ge=0, description="Input tokens used.")
    output_tokens: int = Field(default=0, ge=0, description="Output tokens generated.")
    total_tokens: int = Field(default=0, ge=0, description="Total tokens consumed.")
    status: str = Field(default="COMPLETED", description="Execution status.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata dictionary.")


class ExecutionFailedPayload(InfuseBaseModel):
    """Standard payload structure for ExecutionFailed lifecycle events."""
    request_id: str = Field(..., description="Request identifier.")
    task_id: str = Field(..., description="Task identifier.")
    provider_id: Optional[str] = Field(default=None, description="Attempted provider identifier.")
    model_id: Optional[str] = Field(default=None, description="Attempted model identifier.")
    error_type: str = Field(..., description="Normalized error category or class.")
    error_message: str = Field(..., description="Error message description.")
    is_retryable: bool = Field(default=False, description="Whether the error was flagged retryable.")
    http_status: Optional[int] = Field(default=None, description="HTTP status code if applicable.")
    duration_ms: float = Field(default=0.0, ge=0.0, description="Duration before failure in ms.")
    status: str = Field(default="FAILED", description="Execution status.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata dictionary.")


__all__ = [
    "EventType",
    "EventSource",
    "ExecutionEvent",
    "TokenObservedPayload",
    "ToolActivityPayload",
    "WebActivityPayload",
    "ProviderErrorPayload",
    "StateChangedPayload",
    "ControlActionIssuedPayload",
    "ExecutionStartedPayload",
    "ExecutionCompletedPayload",
    "ExecutionFailedPayload",
]
