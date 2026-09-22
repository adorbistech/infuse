"""Provider & Model Registry canonical models and declarations."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import Field

from infuse.contracts.common import InfuseBaseModel
from infuse.version import SCHEMA_VERSION


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class RegistryLifecycleStatus(str, Enum):
    """Lifecycle status for providers and models within the registry."""
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    DISABLED = "DISABLED"


class ModelModality(str, Enum):
    """Supported input/output modality formats."""
    TEXT = "TEXT"
    VISION = "VISION"
    AUDIO = "AUDIO"
    MULTIMODAL = "MULTIMODAL"


class ModelCapabilityDeclaration(InfuseBaseModel):
    """Descriptive capability declaration for a registered AI model."""
    supports_tools: bool = Field(
        default=False,
        description="Supports function / tool calling."
    )
    supports_vision: bool = Field(
        default=False,
        description="Supports multimodal image/vision inputs."
    )
    supports_structured_output: bool = Field(
        default=False,
        description="Supports JSON Schema / structured output constraints."
    )
    supports_streaming: bool = Field(
        default=True,
        description="Supports streaming token responses."
    )
    supports_caching: bool = Field(
        default=False,
        description="Supports prompt / context caching."
    )
    supports_reasoning: bool = Field(
        default=False,
        description="Supports extended internal reasoning / chain-of-thought."
    )
    modalities: List[ModelModality] = Field(
        default_factory=lambda: [ModelModality.TEXT],
        description="Supported modalities."
    )
    declared_capabilities: List[str] = Field(
        default_factory=list,
        description="Additional capability keywords (e.g. ['code', 'json', 'tools'])."
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Descriptive model capability extensions."
    )


class ProviderCapabilityDeclaration(InfuseBaseModel):
    """Descriptive capability declaration for a registered execution provider."""
    supports_streaming: bool = Field(
        default=True,
        description="Provider infrastructure supports streaming."
    )
    supports_tool_calling: bool = Field(
        default=True,
        description="Provider infrastructure supports tool calling."
    )
    supports_caching: bool = Field(
        default=False,
        description="Provider supports server-side context caching."
    )
    supports_vision: bool = Field(
        default=False,
        description="Provider supports vision payloads."
    )
    supports_structured_output: bool = Field(
        default=False,
        description="Provider supports structured outputs."
    )
    supported_protocols: List[str] = Field(
        default_factory=lambda: ["http"],
        description="Supported protocols (e.g. ['http', 'sse', 'grpc'])."
    )
    rate_limits: Dict[str, Any] = Field(
        default_factory=dict,
        description="Declared rate limit specifications (RPM, TPM) for informational metadata."
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Descriptive provider capability extensions."
    )


class ProviderRecord(InfuseBaseModel):
    """Canonical registry record representing an execution provider."""
    provider_id: str = Field(
        ...,
        description="Unique stable provider identifier (e.g. 'openai', 'anthropic', 'google')."
    )
    name: str = Field(
        ...,
        description="Human-readable provider display name."
    )
    description: Optional[str] = Field(
        default=None,
        description="Descriptive provider summary."
    )
    provider_type: str = Field(
        default="cloud",
        description="Provider category (e.g. 'cloud', 'local', 'gateway', 'custom')."
    )
    endpoint_reference: Optional[str] = Field(
        default=None,
        description="Reference endpoint metadata (no credentials or tokens)."
    )
    version: str = Field(
        default="1.0.0",
        description="Provider API / interface version."
    )
    capabilities: ProviderCapabilityDeclaration = Field(
        default_factory=ProviderCapabilityDeclaration,
        description="Declared provider capabilities."
    )
    status: RegistryLifecycleStatus = Field(
        default=RegistryLifecycleStatus.ACTIVE,
        description="Lifecycle status in the catalog."
    )
    created_at: str = Field(
        default_factory=_utc_now_iso,
        description="Registration timestamp in UTC ISO format."
    )
    updated_at: str = Field(
        default_factory=_utc_now_iso,
        description="Last update timestamp in UTC ISO format."
    )


class ModelRecord(InfuseBaseModel):
    """Canonical registry record representing a model under a provider."""
    model_id: str = Field(
        ...,
        description="Unique model identifier within the provider (e.g. 'claude-3-7-sonnet', 'gpt-4o')."
    )
    provider_id: str = Field(
        ...,
        description="Parent provider identifier referencing a valid ProviderRecord."
    )
    name: str = Field(
        ...,
        description="Human-readable model name."
    )
    family: Optional[str] = Field(
        default=None,
        description="Model family (e.g. 'claude-3', 'gpt-4', 'gemini-2')."
    )
    description: Optional[str] = Field(
        default=None,
        description="Descriptive model summary."
    )
    version: str = Field(
        default="1.0.0",
        description="Model release version or snapshot tag."
    )
    context_window: int = Field(
        default=128000,
        gt=0,
        description="Maximum input context window size in tokens."
    )
    max_output_tokens: int = Field(
        default=4096,
        gt=0,
        description="Maximum generation output limit in tokens."
    )
    capabilities: ModelCapabilityDeclaration = Field(
        default_factory=ModelCapabilityDeclaration,
        description="Declared model capabilities."
    )
    status: RegistryLifecycleStatus = Field(
        default=RegistryLifecycleStatus.ACTIVE,
        description="Lifecycle status in the catalog."
    )
    created_at: str = Field(
        default_factory=_utc_now_iso,
        description="Registration timestamp in UTC ISO format."
    )
    updated_at: str = Field(
        default_factory=_utc_now_iso,
        description="Last update timestamp in UTC ISO format."
    )


class RegistrySummary(InfuseBaseModel):
    """Summary overview of the provider and model registry catalog."""
    total_providers: int = Field(default=0, ge=0)
    active_providers: int = Field(default=0, ge=0)
    total_models: int = Field(default=0, ge=0)
    active_models: int = Field(default=0, ge=0)
    schema_version: str = Field(default=SCHEMA_VERSION)
