"""Deterministic Router domain models and route decision contracts."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4
from pydantic import Field

from infuse.contracts.common import InfuseBaseModel
from infuse.version import SCHEMA_VERSION


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _generate_route_id() -> str:
    return f"route_{uuid4().hex[:12]}"


class RoutingStrategy(str, Enum):
    """Canonical routing strategy objectives."""
    BALANCED = "balanced"
    PREFERENCE = "preference"
    WORKLOAD_FIT = "workload_fit"
    LOW_LATENCY = "low_latency"
    COST_EFFICIENT = "cost_efficient"


class RouteTarget(InfuseBaseModel):
    """Execution target selected by the router."""
    provider_id: str = Field(..., description="Provider identifier.")
    model_id: str = Field(..., description="Model identifier.")
    context_window: int = Field(..., gt=0, description="Declared context window limit.")
    max_output_tokens: int = Field(..., gt=0, description="Declared max output tokens.")
    declared_capabilities: List[str] = Field(
        default_factory=list,
        description="Declared capabilities."
    )
    supported_modalities: List[str] = Field(
        default_factory=list,
        description="Supported modality formats."
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Target metadata."
    )


class RoutingEvidence(InfuseBaseModel):
    """Structured evidence ledger explaining the route decision."""
    candidates_evaluated_count: int = Field(..., ge=0, description="Number of compatible candidates evaluated.")
    strategy_used: RoutingStrategy = Field(..., description="Strategy applied for selection.")
    preference_matched: bool = Field(default=False, description="Whether explicit preference rule determined selection.")
    selection_reason: str = Field(..., description="Deterministic explanation for selected target.")
    candidate_pool: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Compatible candidate targets considered [(provider_id, model_id)]."
    )
    tie_breaker_applied: bool = Field(default=False, description="Whether tie-breaking rule was needed.")
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional structured evaluation metrics."
    )


class RouteDecision(InfuseBaseModel):
    """Canonical route decision produced by the Router for downstream adapter dispatch."""
    route_id: str = Field(default_factory=_generate_route_id, description="Unique route decision ID.")
    execution_id: str = Field(..., description="Associated execution identifier.")
    selected_target: RouteTarget = Field(..., description="Primary execution target chosen by router.")
    fallback_targets: List[RouteTarget] = Field(
        default_factory=list,
        description="Ordered list of alternative compatible targets for fallback."
    )
    strategy_used: RoutingStrategy = Field(..., description="Routing strategy applied.")
    evidence: RoutingEvidence = Field(..., description="Structured decision evidence.")
    timestamp: str = Field(default_factory=_utc_now_iso, description="UTC ISO decision timestamp.")
    schema_version: str = Field(default=SCHEMA_VERSION, description="Schema version.")
