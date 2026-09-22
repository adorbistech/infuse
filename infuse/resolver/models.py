"""Capability Resolver models and contracts."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import Field

from infuse.contracts.common import InfuseBaseModel
from infuse.version import SCHEMA_VERSION


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class MismatchReason(str, Enum):
    """Canonical taxonomy of capability compatibility mismatch reasons."""
    MISSING_REQUIRED_CAPABILITY = "missing_required_capability"
    CONTEXT_WINDOW_INSUFFICIENT = "context_window_insufficient"
    MAX_OUTPUT_TOKENS_INSUFFICIENT = "max_output_tokens_insufficient"
    EXCLUDED_PROVIDER = "excluded_provider"
    EXCLUDED_MODEL = "excluded_model"
    UNSUPPORTED_MODALITY = "unsupported_modality"
    ADMINISTRATIVELY_INELIGIBLE = "administratively_ineligible"
    PROVIDER_INELIGIBLE = "provider_ineligible"


class ResolvedRequirements(InfuseBaseModel):
    """Consolidated workload requirements to be matched against registry targets."""
    requires_tools: bool = Field(
        default=False,
        description="Whether tool/function calling is mandatory."
    )
    requires_vision: bool = Field(
        default=False,
        description="Whether multimodal vision support is mandatory."
    )
    requires_structured_output: bool = Field(
        default=False,
        description="Whether structured JSON output support is mandatory."
    )
    requires_web: bool = Field(
        default=False,
        description="Whether web access capability is required."
    )
    requires_streaming: bool = Field(
        default=False,
        description="Whether streaming response is required."
    )
    min_context_tokens: int = Field(
        default=0,
        ge=0,
        description="Minimum input context window capacity required in tokens."
    )
    max_output_tokens_demanded: Optional[int] = Field(
        default=None,
        ge=0,
        description="Minimum output token capacity required if constrained."
    )
    excluded_providers: List[str] = Field(
        default_factory=list,
        description="Providers explicitly excluded from compatibility."
    )
    excluded_models: List[str] = Field(
        default_factory=list,
        description="Models explicitly excluded from compatibility."
    )
    preferred_providers: List[str] = Field(
        default_factory=list,
        description="Informational preferred providers (retained for Router; not used for resolver filtering/ranking)."
    )
    preferred_models: List[str] = Field(
        default_factory=list,
        description="Informational preferred models (retained for Router; not used for resolver filtering/ranking)."
    )
    custom_capabilities: List[str] = Field(
        default_factory=list,
        description="Explicit custom capability keywords required."
    )


class CandidateTarget(InfuseBaseModel):
    """Execution target verified to satisfy all declared workload requirements."""
    provider_id: str = Field(..., description="Provider identifier.")
    model_id: str = Field(..., description="Model identifier.")
    context_window: int = Field(..., gt=0, description="Declared context window limit.")
    max_output_tokens: int = Field(..., gt=0, description="Declared max generation tokens.")
    declared_capabilities: List[str] = Field(
        default_factory=list,
        description="Declared capability tags."
    )
    supported_modalities: List[str] = Field(
        default_factory=list,
        description="Supported input/output modality formats."
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Target metadata for downstream Router inspection."
    )


class IncompatibleTarget(InfuseBaseModel):
    """Execution target rejected during resolution with explicit reasons."""
    provider_id: str = Field(..., description="Provider identifier.")
    model_id: str = Field(..., description="Model identifier.")
    mismatch_reasons: List[str] = Field(
        default_factory=list,
        description="Explicit mismatch reason codes."
    )
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured mismatch context (e.g. required vs available)."
    )


class CapabilityResolutionResult(InfuseBaseModel):
    """Deterministic result of evaluating workload requirements against registered targets."""
    requirements: ResolvedRequirements = Field(
        ...,
        description="Consolidated requirements used for evaluation."
    )
    compatible_targets: List[CandidateTarget] = Field(
        default_factory=list,
        description="Set of registered targets that satisfy all required capabilities."
    )
    incompatible_targets: List[IncompatibleTarget] = Field(
        default_factory=list,
        description="Set of evaluated targets that failed one or more requirements."
    )
    total_evaluated: int = Field(default=0, ge=0, description="Total candidate models evaluated.")
    total_compatible: int = Field(default=0, ge=0, description="Total compatible targets found.")
    resolution_timestamp: str = Field(
        default_factory=_utc_now_iso,
        description="UTC ISO resolution timestamp."
    )
    schema_version: str = Field(default=SCHEMA_VERSION, description="Schema version.")
