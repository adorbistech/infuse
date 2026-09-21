"""Universal Execution Contract definitions.

Defines the normalized request and result envelopes exchanged between callers and INFUSE.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import Field

from infuse.contracts.common import InfuseBaseModel
from infuse.contracts.governor import GovernorDecision
from infuse.contracts.policy import GovernancePolicy
from infuse.contracts.state import ExecutionState


class ExecutionStatus(str, Enum):
    """Lifecycle status of an execution."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    STOPPED = "STOPPED"
    THROTTLED = "THROTTLED"
    TIMED_OUT = "TIMED_OUT"


class TaskContext(InfuseBaseModel):
    """Semantic context for the agent's task."""
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
        description="Hint for workload classification (e.g. coding, research, fast-chat)."
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Categorical tags for filtering and policies."
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional task metadata."
    )


class OperationRequest(InfuseBaseModel):
    """The underlying operation payload requested from the AI infrastructure."""
    messages: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Conversation history or prompts in normalized format."
    )
    tools: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Tool/function definitions available to the agent."
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Model parameters (e.g. temperature, max_tokens, stop sequences)."
    )
    raw_payload: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Original caller payload for lossless forwarding where appropriate."
    )


class ExecutionRequirements(InfuseBaseModel):
    """Hard and soft constraints demanded for this execution."""
    min_context_tokens: Optional[int] = Field(
        default=None,
        description="Minimum context window size required."
    )
    supports_tools: bool = Field(
        default=False,
        description="Whether function/tool calling is strictly required."
    )
    supports_vision: bool = Field(
        default=False,
        description="Whether multi-modal image input is required."
    )
    supports_structured_output: bool = Field(
        default=False,
        description="Whether JSON Schema structured output is required."
    )
    max_latency_ms: Optional[float] = Field(
        default=None,
        description="Latency threshold requirement."
    )
    preferred_providers: List[str] = Field(
        default_factory=list,
        description="Ranked list of preferred providers."
    )
    excluded_providers: List[str] = Field(
        default_factory=list,
        description="Providers that must not be used."
    )
    preferred_models: List[str] = Field(
        default_factory=list,
        description="Ranked list of preferred models."
    )
    excluded_models: List[str] = Field(
        default_factory=list,
        description="Models that must not be used."
    )


class ExecutionContext(InfuseBaseModel):
    """Runtime execution environment context."""
    session_id: Optional[str] = Field(
        default=None,
        description="User or workflow session grouping multiple tasks."
    )
    workflow_id: Optional[str] = Field(
        default=None,
        description="Workflow or pipeline identifier."
    )
    step_index: int = Field(
        default=0,
        ge=0,
        description="Current step index within a multi-step agent trajectory."
    )
    isolation_pool: Optional[str] = Field(
        default=None,
        description="Routing or execution isolation pool (e.g. eu-sandbox, high-security)."
    )
    agent_id: Optional[str] = Field(
        default=None,
        description="Identifier of the executing autonomous agent."
    )
    client_version: Optional[str] = Field(
        default=None,
        description="Client SDK/CLI/MCP version string."
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Contextual runtime metadata."
    )


class ExecutionRequest(InfuseBaseModel):
    """Canonical normalized execution request received by INFUSE."""
    request_id: str = Field(
        ...,
        description="Unique caller-generated or gateway-generated request ID."
    )
    task: TaskContext = Field(
        ...,
        description="Task context and objectives."
    )
    request: OperationRequest = Field(
        ...,
        description="Operational payload (messages, tools, params)."
    )
    requirements: ExecutionRequirements = Field(
        default_factory=ExecutionRequirements,
        description="Hard and soft capability constraints."
    )
    policy: Optional[GovernancePolicy] = Field(
        default=None,
        description="Inline governance policy or override. If None, default/tenant policy applies."
    )
    execution_context: ExecutionContext = Field(
        default_factory=ExecutionContext,
        description="Runtime context metadata."
    )


class NormalizedResponse(InfuseBaseModel):
    """Normalized response returned from model execution."""
    content: Optional[str] = Field(
        default=None,
        description="Generated text content."
    )
    role: str = Field(
        default="assistant",
        description="Message role."
    )
    tool_calls: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Requested tool invocations from the model."
    )
    finish_reason: Optional[str] = Field(
        default=None,
        description="Reason generation terminated (e.g. stop, length, tool_calls)."
    )
    raw_response: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Underlying raw provider response object for non-standard metadata."
    )


class ExecutionTelemetry(InfuseBaseModel):
    """Comprehensive telemetry recorded across the execution lifecycle."""
    provider: Optional[str] = Field(
        default=None,
        description="Selected AI execution provider."
    )
    model: Optional[str] = Field(
        default=None,
        description="Selected model identifier."
    )
    input_tokens: int = Field(default=0, ge=0)
    cached_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    cost_usd: float = Field(default=0.0, ge=0.0)
    latency_ms: float = Field(default=0.0, ge=0.0)
    requests_count: int = Field(default=1, ge=0)
    retries_count: int = Field(default=0, ge=0)
    tool_calls_count: int = Field(default=0, ge=0)
    web_requests_count: int = Field(default=0, ge=0)
    errors_count: int = Field(default=0, ge=0)
    state: ExecutionState = Field(
        default=ExecutionState.NORMAL,
        description="Final or current execution state."
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Provider-specific or custom telemetry extensions."
    )


class ExecutionResult(InfuseBaseModel):
    """Canonical normalized execution result returned by INFUSE."""
    execution_id: str = Field(
        ...,
        description="Unique execution run identifier."
    )
    request_id: str = Field(
        ...,
        description="Corresponding request ID."
    )
    status: ExecutionStatus = Field(
        default=ExecutionStatus.COMPLETED,
        description="Overall lifecycle outcome."
    )
    response: Optional[NormalizedResponse] = Field(
        default=None,
        description="Model output payload if successful."
    )
    execution: ExecutionTelemetry = Field(
        default_factory=ExecutionTelemetry,
        description="Measured execution metrics, token counts, and cost."
    )
    decision: GovernorDecision = Field(
        default_factory=GovernorDecision,
        description="Governor decision governing the next step or termination."
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error details if execution failed."
    )
