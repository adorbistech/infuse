"""Common schema utilities and base contract models for INFUSE.

All INFUSE contracts derive from InfuseBaseModel to ensure:
1. Schema versioning tracking
2. Extensibility via preserved extra fields (no data loss during additive evolution)
3. Strict typing and validation
4. Language-neutral JSON serialization
"""

from datetime import datetime, timezone
from typing import Any, Dict
from pydantic import BaseModel, ConfigDict, Field

from infuse.version import SCHEMA_VERSION


def utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)


class InfuseBaseModel(BaseModel):
    """Base model for all INFUSE contracts.
    
    Permits extra fields to enable additive contract evolution without breaking older consumers.
    """
    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
    )

    schema_version: str = Field(
        default=SCHEMA_VERSION,
        description="Semantic version of the contract schema."
    )
    extensions: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extension bag for custom/future domain metadata."
    )
