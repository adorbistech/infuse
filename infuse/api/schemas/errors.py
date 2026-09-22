"""Normalized API Error Schema definition."""

from typing import Any, Dict, Optional
from pydantic import Field

from infuse.contracts.common import InfuseBaseModel
from infuse.version import SCHEMA_VERSION


class ApiErrorResponse(InfuseBaseModel):
    """Canonical normalized error representation returned by all API endpoints."""
    code: str = Field(
        ...,
        description="Machine-readable error category code (e.g. VALIDATION_ERROR, NOT_FOUND)."
    )
    message: str = Field(
        ...,
        description="Human-readable explanation of the error."
    )
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Structured error details or validation violations."
    )
    correlation_id: Optional[str] = Field(
        default=None,
        description="Unique correlation/request ID for request tracing."
    )
    schema_version: str = Field(
        default=SCHEMA_VERSION,
        description="Schema contract version."
    )
