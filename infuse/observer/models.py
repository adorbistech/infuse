"""Normalized Data Models for Block 15 Token Observer."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import Field

from infuse.contracts.common import InfuseBaseModel, utc_now
from infuse.contracts.events import EventSource, EventType, ExecutionEvent
from infuse.version import SCHEMA_VERSION


class TokenObservationSource(str, Enum):
    """Categorical source and authority classification of token usage observations."""
    PROVIDER_USAGE = "PROVIDER_USAGE"
    STREAM_ESTIMATE = "STREAM_ESTIMATE"
    LIFECYCLE_EVENT = "LIFECYCLE_EVENT"
    DERIVED = "DERIVED"
    UNSPECIFIED = "UNSPECIFIED"


class TokenObservationRecord(InfuseBaseModel):
    """Point-in-time token observation entry recorded from a single execution event."""
    event_id: str = Field(..., description="ID of the triggering event.")
    sequence: int = Field(default=0, ge=0, description="Sequence number of the triggering event.")
    timestamp: datetime = Field(default_factory=utc_now, description="UTC observation timestamp.")
    event_type: EventType = Field(..., description="Categorical event type.")
    input_tokens: Optional[int] = Field(default=None, ge=0, description="Observed input/prompt tokens.")
    output_tokens: Optional[int] = Field(default=None, ge=0, description="Observed output/completion tokens.")
    cached_tokens: Optional[int] = Field(default=None, ge=0, description="Observed cached prompt tokens.")
    total_tokens: Optional[int] = Field(default=None, ge=0, description="Observed total tokens.")
    is_authoritative: bool = Field(
        default=False,
        description="True if provided directly by provider/lifecycle; False if estimated or stream-inferred."
    )
    source: TokenObservationSource = Field(
        default=TokenObservationSource.UNSPECIFIED,
        description="Source classification of this observation."
    )
    provider_id: Optional[str] = Field(default=None, description="Observed provider identifier.")
    model_id: Optional[str] = Field(default=None, description="Observed model identifier.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata dictionary.")


class ExecutionTokenSummary(InfuseBaseModel):
    """Normalized, aggregated execution-level token observation view."""
    execution_id: str = Field(..., description="Unique execution run identifier.")
    input_tokens: Optional[int] = Field(default=None, ge=0, description="Normalized input/prompt tokens.")
    output_tokens: Optional[int] = Field(default=None, ge=0, description="Normalized output/completion tokens.")
    cached_tokens: Optional[int] = Field(default=None, ge=0, description="Normalized cached tokens.")
    total_tokens: Optional[int] = Field(default=None, ge=0, description="Normalized total tokens.")
    is_authoritative: bool = Field(
        default=False,
        description="True if the active summary was produced by authoritative provider/lifecycle data."
    )
    source: TokenObservationSource = Field(
        default=TokenObservationSource.UNSPECIFIED,
        description="Authority/source of current summary."
    )
    provider_id: Optional[str] = Field(default=None, description="Active execution provider ID.")
    model_id: Optional[str] = Field(default=None, description="Active execution model ID.")
    events_count: int = Field(default=0, ge=0, description="Total number of distinct events aggregated.")
    last_sequence: int = Field(default=0, ge=0, description="Highest event sequence number observed.")
    first_observed_at: Optional[datetime] = Field(default=None, description="Timestamp of first observed event.")
    last_observed_at: Optional[datetime] = Field(default=None, description="Timestamp of latest observed event.")
    is_finalized: bool = Field(
        default=False,
        description="True if execution has concluded (via ExecutionCompleted or ExecutionFailed)."
    )
    final_status: Optional[str] = Field(
        default=None,
        description="Terminal execution status (e.g. COMPLETED, FAILED)."
    )
    history: List[TokenObservationRecord] = Field(
        default_factory=list,
        description="Ordered point-in-time observation audit trail."
    )
    schema_version: str = Field(
        default=SCHEMA_VERSION,
        description="Contract schema version."
    )


__all__ = [
    "TokenObservationSource",
    "TokenObservationRecord",
    "ExecutionTokenSummary",
]
