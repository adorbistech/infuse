"""Data Models and Contract Re-exports for Block 22 Execution Control Boundary."""

from typing import Any, Dict, List, Optional
from pydantic import Field

from infuse.contracts.common import InfuseBaseModel, utc_now
from infuse.contracts.control import (
    ControlCapability,
    ControlOperation,
    ControlResult,
    ControlStatus,
)
from infuse.contracts.governor import GovernorAction


class ControlAuditRecord(InfuseBaseModel):
    """Immutable audit entry of a control dispatch and its result."""
    execution_id: str = Field(..., description="Target execution identifier.")
    operation: ControlOperation = Field(..., description="The dispatched control operation.")
    result: ControlResult = Field(..., description="The outcome of the control operation.")
    is_supported: bool = Field(..., description="Whether the requested control capability was supported.")
    target_executor: Optional[str] = Field(default=None, description="Identifier of the executing control adapter.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional audit metadata.")


__all__ = [
    "ControlCapability",
    "ControlOperation",
    "ControlResult",
    "ControlStatus",
    "ControlAuditRecord",
    "GovernorAction",
]
