"""Adapter Capability Contract definitions.

Enables agents, providers, and integration interfaces to declare capabilities
without coupling the INFUSE core to specific branded implementations.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import Field

from infuse.contracts.common import InfuseBaseModel
from infuse.contracts.control import ControlCapability


class AdapterType(str, Enum):
    """Category of integration adapter."""
    AGENT = "AGENT"
    PROVIDER = "PROVIDER"
    CONTROL = "CONTROL"
    SDK = "SDK"
    MCP = "MCP"


class AgentCapability(InfuseBaseModel):
    """Capabilities declared by an autonomous agent adapter."""
    agent_name: str = Field(
        ...,
        description="Name of the agent runtime (e.g. opencode, claudecode, codex)."
    )
    supported_protocols: List[str] = Field(
        default_factory=list,
        description="Communication protocols supported (e.g. http, stdio, sse, ws)."
    )
    control_capabilities: ControlCapability = Field(
        default_factory=ControlCapability,
        description="Control operations the agent runtime can physically execute."
    )
    supports_streaming_events: bool = Field(
        default=True,
        description="Whether the agent emits real-time step and token events."
    )
    supports_tool_interception: bool = Field(
        default=False,
        description="Whether tool calls can be intercepted before execution."
    )
    supported_models: List[str] = Field(
        default_factory=list,
        description="Models natively supported or requested by this agent."
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Agent-specific capability extensions."
    )


class ProviderCapability(InfuseBaseModel):
    """Capabilities declared by an AI execution provider adapter."""
    provider_name: str = Field(
        ...,
        description="Provider identifier (e.g. openai, anthropic, gemini, deepseek, custom)."
    )
    supported_models: List[str] = Field(
        default_factory=list,
        description="List of model IDs accessible through this provider."
    )
    supports_streaming: bool = Field(
        default=True,
        description="Supports token streaming."
    )
    supports_tool_calling: bool = Field(
        default=True,
        description="Supports function / tool calling APIs."
    )
    supports_caching: bool = Field(
        default=False,
        description="Supports prompt / prefix caching."
    )
    supports_vision: bool = Field(
        default=False,
        description="Supports multimodal image inputs."
    )
    supports_structured_output: bool = Field(
        default=False,
        description="Supports JSON Schema structured outputs."
    )
    max_context_window: Optional[int] = Field(
        default=None,
        description="Maximum supported context window size."
    )
    rate_limits: Dict[str, Any] = Field(
        default_factory=dict,
        description="Provider-declared rate limits (RPM, TPM, RPD) if known."
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Provider-specific capability extensions."
    )


class AdapterRegistration(InfuseBaseModel):
    """Universal registration record for any adapter connecting to INFUSE."""
    adapter_id: str = Field(
        ...,
        description="Unique identifier for this adapter instance."
    )
    name: str = Field(
        ...,
        description="Human-readable adapter name."
    )
    version: str = Field(
        default="1.0.0",
        description="Adapter version."
    )
    adapter_type: AdapterType = Field(
        ...,
        description="Type of adapter."
    )
    agent_capability: Optional[AgentCapability] = Field(
        default=None,
        description="Populated if adapter_type == AGENT."
    )
    provider_capability: Optional[ProviderCapability] = Field(
        default=None,
        description="Populated if adapter_type == PROVIDER."
    )
    control_capability: Optional[ControlCapability] = Field(
        default=None,
        description="Populated if adapter_type == CONTROL."
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Registration metadata."
    )
