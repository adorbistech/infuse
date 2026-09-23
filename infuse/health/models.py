"""Normalized Data Models for Block 17 Health Engine."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import Field

from infuse.contracts.common import InfuseBaseModel, utc_now
from infuse.version import SCHEMA_VERSION


class ErrorCategory(str, Enum):
    """Categorical classification of observed provider and execution errors."""
    TIMEOUT = "TIMEOUT"
    RATE_LIMIT = "RATE_LIMIT"
    AUTHENTICATION = "AUTHENTICATION"
    UNAVAILABLE = "UNAVAILABLE"
    INVALID_REQUEST = "INVALID_REQUEST"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    EXECUTION_ERROR = "EXECUTION_ERROR"
    UNKNOWN = "UNKNOWN"


class HealthCompleteness(str, Enum):
    """Completeness state of health observation for an execution."""
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"


class ObservedErrorRecord(InfuseBaseModel):
    """Normalized record of an observed provider or execution error."""
    event_id: str = Field(..., description="Source event identifier.")
    execution_id: str = Field(..., description="Associated execution identifier.")
    provider_id: Optional[str] = Field(default=None, description="Associated provider identifier.")
    model_id: Optional[str] = Field(default=None, description="Associated model identifier.")
    error_category: ErrorCategory = Field(
        default=ErrorCategory.UNKNOWN,
        description="Normalized category of the error."
    )
    error_type: str = Field(default="UNKNOWN", description="Original error type string.")
    error_code: Optional[str] = Field(default=None, description="Provider error code if reported.")
    message: str = Field(default="", description="Error description message.")
    is_retryable: bool = Field(default=False, description="Whether error was declared retryable.")
    http_status: Optional[int] = Field(default=None, description="HTTP status code if applicable.")
    observed_at: datetime = Field(
        default_factory=utc_now,
        description="Observation timestamp in UTC."
    )


class ObservedRetryRecord(InfuseBaseModel):
    """Normalized record of an observed retry attempt."""
    event_id: str = Field(..., description="Source event identifier.")
    execution_id: str = Field(..., description="Associated execution identifier.")
    provider_id: Optional[str] = Field(default=None, description="Target provider identifier.")
    model_id: Optional[str] = Field(default=None, description="Target model identifier.")
    attempt_number: Optional[int] = Field(default=None, ge=1, description="Retry attempt number.")
    reason: Optional[str] = Field(default=None, description="Reason for the retry.")
    observed_at: datetime = Field(
        default_factory=utc_now,
        description="Observation timestamp in UTC."
    )


class ExecutionHealthSummary(InfuseBaseModel):
    """Execution-level health summary aggregating observed lifecycle and error signals."""
    execution_id: str = Field(..., description="Execution identifier.")
    provider_id: Optional[str] = Field(default=None, description="Executing provider ID.")
    model_id: Optional[str] = Field(default=None, description="Executing model ID.")
    status: Optional[str] = Field(default=None, description="Execution status ('STARTED', 'COMPLETED', 'FAILED').")
    is_success: Optional[bool] = Field(
        default=None,
        description="True if completed successfully, False if failed, None if in progress."
    )
    latency_ms: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Execution round-trip latency in milliseconds. None if unobserved."
    )
    errors: List[ObservedErrorRecord] = Field(
        default_factory=list,
        description="Chronological record of observed errors."
    )
    retries: List[ObservedRetryRecord] = Field(
        default_factory=list,
        description="Chronological record of observed retries."
    )
    completeness: HealthCompleteness = Field(
        default=HealthCompleteness.UNKNOWN,
        description="Completeness state of health observation."
    )
    is_finalized: bool = Field(
        default=False,
        description="True if execution has reached a terminal outcome."
    )
    events_count: int = Field(default=0, ge=0, description="Number of observed events.")
    last_sequence: int = Field(default=0, ge=0, description="Highest observed event sequence.")
    started_at: Optional[datetime] = Field(default=None, description="Execution start timestamp.")
    completed_at: Optional[datetime] = Field(default=None, description="Execution completion/failure timestamp.")
    schema_version: str = Field(default=SCHEMA_VERSION, description="Schema version.")


class ProviderHealthAggregate(InfuseBaseModel):
    """Deterministic health aggregation across executions for a provider."""
    provider_id: str = Field(..., description="Provider identifier.")
    total_executions: int = Field(default=0, ge=0, description="Total executions observed.")
    successful_executions: int = Field(default=0, ge=0, description="Successful executions.")
    failed_executions: int = Field(default=0, ge=0, description="Failed executions.")
    provider_error_count: int = Field(default=0, ge=0, description="Total provider errors observed.")
    retry_count: int = Field(default=0, ge=0, description="Total retry events observed.")
    total_latency_ms: float = Field(default=0.0, ge=0.0, description="Cumulative latency in ms.")
    min_latency_ms: Optional[float] = Field(default=None, ge=0.0, description="Minimum latency observed.")
    max_latency_ms: Optional[float] = Field(default=None, ge=0.0, description="Maximum latency observed.")
    avg_latency_ms: Optional[float] = Field(default=None, ge=0.0, description="Average latency in ms.")
    error_counts_by_category: Dict[str, int] = Field(
        default_factory=dict,
        description="Error counts broken down by ErrorCategory."
    )
    last_observed_at: Optional[datetime] = Field(default=None, description="Last event observation timestamp.")


class ModelHealthAggregate(InfuseBaseModel):
    """Deterministic health aggregation across executions for a specific model."""
    provider_id: str = Field(..., description="Parent provider identifier.")
    model_id: str = Field(..., description="Model identifier.")
    total_executions: int = Field(default=0, ge=0, description="Total executions observed.")
    successful_executions: int = Field(default=0, ge=0, description="Successful executions.")
    failed_executions: int = Field(default=0, ge=0, description="Failed executions.")
    provider_error_count: int = Field(default=0, ge=0, description="Total provider errors observed.")
    retry_count: int = Field(default=0, ge=0, description="Total retry events observed.")
    total_latency_ms: float = Field(default=0.0, ge=0.0, description="Cumulative latency in ms.")
    min_latency_ms: Optional[float] = Field(default=None, ge=0.0, description="Minimum latency observed.")
    max_latency_ms: Optional[float] = Field(default=None, ge=0.0, description="Maximum latency observed.")
    avg_latency_ms: Optional[float] = Field(default=None, ge=0.0, description="Average latency in ms.")
    error_counts_by_category: Dict[str, int] = Field(
        default_factory=dict,
        description="Error counts broken down by ErrorCategory."
    )
    last_observed_at: Optional[datetime] = Field(default=None, description="Last event observation timestamp.")


__all__ = [
    "ErrorCategory",
    "HealthCompleteness",
    "ObservedErrorRecord",
    "ObservedRetryRecord",
    "ExecutionHealthSummary",
    "ProviderHealthAggregate",
    "ModelHealthAggregate",
]
