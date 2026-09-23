"""Normalized Data Models and Re-exports for Block 21 Governor Engine."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import Field

from infuse.contracts.common import InfuseBaseModel, utc_now
from infuse.contracts.governor import GovernorAction, GovernorDecision, GovernorDecisionRecord
from infuse.contracts.policy import GovernancePolicy
from infuse.contracts.state import ExecutionStateSnapshot
from infuse.version import SCHEMA_VERSION


class EvaluationContext(InfuseBaseModel):
    """Contextual evidence provided to the Governor during a decision evaluation."""
    execution_id: str = Field(..., description="Target execution identifier.")
    state_snapshot: ExecutionStateSnapshot = Field(..., description="Canonical state snapshot from Block 20.")
    policy: Optional[GovernancePolicy] = Field(default=None, description="Active governance policy from Block 06.")
    additional_signals: Dict[str, Any] = Field(default_factory=dict, description="Additional external signals or metadata.")
    evaluated_at: datetime = Field(default_factory=utc_now, description="Evaluation timestamp.")


__all__ = [
    "GovernorAction",
    "GovernorDecision",
    "GovernorDecisionRecord",
    "EvaluationContext",
]
