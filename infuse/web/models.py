"""Normalized Data Models for Block 19 Web Activity Observer."""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import Field

from infuse.contracts.common import InfuseBaseModel
from infuse.version import SCHEMA_VERSION


class WebActivityStatus(str, Enum):
    """Observable status of an individual web activity."""
    REQUESTED = "REQUESTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    INCOMPLETE = "INCOMPLETE"


class WebObservationCompleteness(str, Enum):
    """Completeness state of web activity observations for an execution."""
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"


class WebActivityRecord(InfuseBaseModel):
    """Normalized record of an individual web request and response lifecycle."""
    request_id: Optional[str] = Field(
        default=None,
        description="Web request identifier correlating request and response."
    )
    execution_id: str = Field(..., description="Associated execution identifier.")
    url: str = Field(..., description="Target URL of the web request.")
    method: str = Field(default="GET", description="HTTP method (e.g. GET, POST).")
    status: WebActivityStatus = Field(
        default=WebActivityStatus.REQUESTED,
        description="Observable web activity status."
    )
    status_code: Optional[int] = Field(
        default=None,
        description="HTTP response status code if observed."
    )
    bytes_transferred: Optional[int] = Field(
        default=None,
        ge=0,
        description="Observed payload bytes transferred."
    )
    success: Optional[bool] = Field(
        default=None,
        description="True if request succeeded, False if failed, None if unobserved."
    )
    error: Optional[str] = Field(
        default=None,
        description="Normalized error message if request failed."
    )
    duration_ms: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Web request round-trip duration in milliseconds. None if unobserved."
    )
    requested_at: Optional[datetime] = Field(
        default=None,
        description="UTC timestamp when WebRequest occurred."
    )
    responded_at: Optional[datetime] = Field(
        default=None,
        description="UTC timestamp when WebResponse occurred."
    )
    request_event_id: Optional[str] = Field(
        default=None,
        description="Source event_id for WebRequest."
    )
    response_event_id: Optional[str] = Field(
        default=None,
        description="Source event_id for WebResponse."
    )
    sequence: int = Field(
        default=0,
        ge=0,
        description="Event sequence number."
    )


class ExecutionWebSummary(InfuseBaseModel):
    """Execution-level aggregate web activity summary."""
    execution_id: str = Field(..., description="Associated execution identifier.")
    total_requests: int = Field(default=0, ge=0, description="Total web requests observed.")
    completed_requests: int = Field(default=0, ge=0, description="Total completed web requests.")
    successful_requests: int = Field(default=0, ge=0, description="Total successfully completed web requests.")
    failed_requests: int = Field(default=0, ge=0, description="Total failed web requests.")
    incomplete_requests: int = Field(
        default=0,
        ge=0,
        description="Total web requests without a matched response event."
    )
    unique_targets: List[str] = Field(
        default_factory=list,
        description="Sorted list of distinct URLs observed."
    )
    total_duration_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Cumulative observed duration in milliseconds across completed requests."
    )
    avg_duration_ms: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Average duration in milliseconds across requests with valid observed duration."
    )
    total_bytes_transferred: int = Field(
        default=0,
        ge=0,
        description="Total bytes transferred across all observed responses."
    )
    activities: List[WebActivityRecord] = Field(
        default_factory=list,
        description="Chronological list of all observed web activity records."
    )
    completeness: WebObservationCompleteness = Field(
        default=WebObservationCompleteness.UNKNOWN,
        description="Overall web observation completeness state."
    )
    events_count: int = Field(default=0, ge=0, description="Total web events processed.")
    last_sequence: int = Field(default=0, ge=0, description="Highest observed event sequence.")
    schema_version: str = Field(default=SCHEMA_VERSION, description="Schema version.")


__all__ = [
    "WebActivityStatus",
    "WebObservationCompleteness",
    "WebActivityRecord",
    "ExecutionWebSummary",
]
