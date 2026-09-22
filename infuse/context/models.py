"""Execution Context model definitions.

Represents the canonical contextual identity and descriptive metadata
surrounding an INFUSE execution without making routing, governance, or execution decisions.
"""

from typing import Any, Dict, List, Optional
from pydantic import Field

from infuse.contracts.common import InfuseBaseModel
from infuse.version import SCHEMA_VERSION


class TaskContextInfo(InfuseBaseModel):
    """Descriptive task context."""
    task_id: str = Field(
        ...,
        description="Unique task identifier."
    )
    description: Optional[str] = Field(
        default=None,
        description="Human-readable description or goal of the task."
    )
    workload_hint: Optional[str] = Field(
        default=None,
        description="Caller-provided workload hint (e.g. coding, research, chat)."
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Categorical tags for filtering and descriptive indexing."
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional task metadata."
    )


class AgentContextInfo(InfuseBaseModel):
    """Descriptive autonomous agent and client identity."""
    agent_id: Optional[str] = Field(
        default=None,
        description="Identifier of the executing autonomous agent."
    )
    agent_name: Optional[str] = Field(
        default=None,
        description="Human-readable agent name or archetype."
    )
    agent_type: Optional[str] = Field(
        default=None,
        description="Category of the agent (e.g. assistant, code-generator, researcher)."
    )
    client_version: Optional[str] = Field(
        default=None,
        description="Client SDK/CLI/MCP version string."
    )
    runtime_version: Optional[str] = Field(
        default=None,
        description="Underlying runtime environment version."
    )
    execution_mode: Optional[str] = Field(
        default=None,
        description="Execution mode (e.g. autonomous, human_in_the_loop, batch)."
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Agent-specific descriptive metadata."
    )


class RuntimeContextInfo(InfuseBaseModel):
    """Descriptive runtime environment and workflow context."""
    session_id: Optional[str] = Field(
        default=None,
        description="User or workflow session grouping multiple executions."
    )
    workflow_id: Optional[str] = Field(
        default=None,
        description="Workflow or pipeline identifier."
    )
    step_index: int = Field(
        default=0,
        description="Current step index within a multi-step agent trajectory."
    )
    isolation_pool: Optional[str] = Field(
        default=None,
        description="Routing or execution isolation pool (e.g. standard, high-security)."
    )
    environment: Optional[str] = Field(
        default=None,
        description="Operating environment name (e.g. production, staging, development)."
    )
    region: Optional[str] = Field(
        default=None,
        description="Geographic or datacenter region."
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Runtime descriptive metadata."
    )


class ConstraintContextInfo(InfuseBaseModel):
    """Descriptive execution constraints and requested capabilities demanded by the caller."""
    requested_capabilities: List[str] = Field(
        default_factory=list,
        description="Requested capability identifiers (e.g. tools, web, vision, structured_output)."
    )
    min_context_tokens: Optional[int] = Field(
        default=None,
        description="Minimum context window size required by the caller."
    )
    max_latency_ms: Optional[float] = Field(
        default=None,
        description="Latency threshold requested by the caller."
    )
    supports_tools: bool = Field(
        default=False,
        description="Whether function/tool calling is requested."
    )
    supports_vision: bool = Field(
        default=False,
        description="Whether multimodal vision input is requested."
    )
    supports_structured_output: bool = Field(
        default=False,
        description="Whether JSON schema structured output is requested."
    )
    preferred_providers: List[str] = Field(
        default_factory=list,
        description="Ranked list of preferred providers specified by caller."
    )
    excluded_providers: List[str] = Field(
        default_factory=list,
        description="Providers excluded by caller."
    )
    preferred_models: List[str] = Field(
        default_factory=list,
        description="Ranked list of preferred models specified by caller."
    )
    excluded_models: List[str] = Field(
        default_factory=list,
        description="Models excluded by caller."
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Constraint metadata."
    )


class PolicyContextInfo(InfuseBaseModel):
    """Descriptive policy reference identifying which governance policy applies."""
    policy_id: Optional[str] = Field(
        default="pol_default",
        description="Identifier of the associated governance policy envelope."
    )
    policy_version: Optional[str] = Field(
        default=None,
        description="Specific revision of the governance policy if pinned."
    )
    has_inline_policy: bool = Field(
        default=False,
        description="Whether an inline policy override was provided in the request."
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Policy reference metadata."
    )


class OperationContextInfo(InfuseBaseModel):
    """Descriptive summary of the operational payload."""
    message_count: int = Field(
        default=0,
        ge=0,
        description="Number of messages in the request history."
    )
    has_tools: bool = Field(
        default=False,
        description="Whether tools are supplied in the request."
    )
    tool_count: int = Field(
        default=0,
        ge=0,
        description="Count of tools supplied in the request."
    )
    parameter_keys: List[str] = Field(
        default_factory=list,
        description="Names of model parameter overrides supplied (e.g. temperature, max_tokens)."
    )
    has_raw_payload: bool = Field(
        default=False,
        description="Whether raw payload was attached."
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Operation metadata."
    )


class ExecutionContextRecord(InfuseBaseModel):
    """Canonical Execution Context envelope capturing all contextual dimensions of an execution."""
    execution_id: str = Field(
        ...,
        description="Unique execution identifier."
    )
    request_id: str = Field(
        ...,
        description="Unique caller-generated or gateway-generated request ID."
    )
    parent_execution_id: Optional[str] = Field(
        default=None,
        description="Identifier of parent execution if this execution is a sub-task."
    )
    created_at: str = Field(
        ...,
        description="ISO-8601 creation timestamp."
    )
    task: TaskContextInfo = Field(
        ...,
        description="Descriptive task context."
    )
    agent: AgentContextInfo = Field(
        default_factory=AgentContextInfo,
        description="Descriptive agent and client context."
    )
    runtime: RuntimeContextInfo = Field(
        default_factory=RuntimeContextInfo,
        description="Descriptive runtime environment context."
    )
    constraints: ConstraintContextInfo = Field(
        default_factory=ConstraintContextInfo,
        description="Descriptive requested capabilities and constraints."
    )
    policy: PolicyContextInfo = Field(
        default_factory=PolicyContextInfo,
        description="Descriptive governance policy reference."
    )
    operation: OperationContextInfo = Field(
        default_factory=OperationContextInfo,
        description="Descriptive operation payload summary."
    )
    schema_version: str = Field(
        default=SCHEMA_VERSION,
        description="Schema contract version."
    )
    extensions: Dict[str, Any] = Field(
        default_factory=dict,
        description="Non-standard context extensions."
    )
