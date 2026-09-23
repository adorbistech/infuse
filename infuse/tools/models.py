"""Normalized Data Models for Block 18 Tool Activity Observer."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import Field

from infuse.contracts.common import InfuseBaseModel, utc_now
from infuse.version import SCHEMA_VERSION


class ToolInvocationStatus(str, Enum):
    """Observable status of an individual tool invocation."""
    CALLED = "CALLED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


class ToolObservationCompleteness(str, Enum):
    """Completeness state of tool activity observations for an execution."""
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"


class ToolInvocationRecord(InfuseBaseModel):
    """Normalized record of an individual tool invocation."""
    call_id: Optional[str] = Field(
        default=None,
        description="Tool call identifier correlating invocation and completion."
    )
    execution_id: str = Field(..., description="Associated execution identifier.")
    tool_name: str = Field(..., description="Canonical tool identifier/name.")
    status: ToolInvocationStatus = Field(
        default=ToolInvocationStatus.CALLED,
        description="Observable invocation status."
    )
    arguments: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Tool input arguments payload if captured."
    )
    success: Optional[bool] = Field(
        default=None,
        description="True if tool succeeded, False if failed, None if completion unobserved."
    )
    error: Optional[str] = Field(
        default=None,
        description="Normalized error message if tool failed."
    )
    duration_ms: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Tool execution duration in milliseconds. None if unobserved."
    )
    started_at: Optional[datetime] = Field(
        default=None,
        description="UTC timestamp when ToolCalled occurred."
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        description="UTC timestamp when ToolCompleted occurred."
    )
    call_event_id: Optional[str] = Field(
        default=None,
        description="Source event_id for ToolCalled."
    )
    completion_event_id: Optional[str] = Field(
        default=None,
        description="Source event_id for ToolCompleted."
    )
    sequence: int = Field(
        default=0,
        ge=0,
        description="Event sequence number."
    )


class ExecutionToolSummary(InfuseBaseModel):
    """Execution-level aggregate tool activity summary."""
    execution_id: str = Field(..., description="Associated execution identifier.")
    total_calls: int = Field(default=0, ge=0, description="Total tool call events observed.")
    completed_calls: int = Field(default=0, ge=0, description="Total completed tool calls.")
    successful_calls: int = Field(default=0, ge=0, description="Total successfully completed tool calls.")
    failed_calls: int = Field(default=0, ge=0, description="Total failed tool calls.")
    incomplete_calls: int = Field(
        default=0,
        ge=0,
        description="Total tool calls without a matched completion event."
    )
    unique_tools: List[str] = Field(
        default_factory=list,
        description="Sorted list of distinct tool names observed."
    )
    total_duration_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Cumulative observed duration in milliseconds across completed tools."
    )
    avg_duration_ms: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Average duration in milliseconds across tools with observed duration."
    )
    invocations: List[ToolInvocationRecord] = Field(
        default_factory=list,
        description="Chronological list of all observed tool invocation records."
    )
    completeness: ToolObservationCompleteness = Field(
        default=ToolObservationCompleteness.UNKNOWN,
        description="Overall tool observation completeness state."
    )
    events_count: int = Field(default=0, ge=0, description="Total tool events processed.")
    last_sequence: int = Field(default=0, ge=0, description="Highest observed event sequence.")
    schema_version: str = Field(default=SCHEMA_VERSION, description="Schema version.")


__all__ = [
    "ToolInvocationStatus",
    "ToolObservationCompleteness",
    "ToolInvocationRecord",
    "ExecutionToolSummary",
]
