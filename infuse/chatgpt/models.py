"""Data transfer models and schemas for the INFUSE ChatGPT App."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from infuse.contracts.execution import ExecutionState
from infuse.contracts.governor import GovernorAction


class ToolCategory(str, Enum):
    """Classification of tool operational boundary."""
    READ = "READ"
    ANALYZE = "ANALYZE"
    EXECUTE = "EXECUTE"
    CONTROL = "CONTROL"


# --- Tool Input Models ---

class ExecuteTaskInput(BaseModel):
    """Input payload for executing a task via INFUSE."""
    task_description: str = Field(
        ...,
        description="High-level description of the task for the autonomous agent to perform.",
        min_length=1,
        max_length=4000,
    )
    prompt: Optional[str] = Field(
        default=None,
        description="Optional detailed prompt or instructions for the agent execution.",
        max_length=16000,
    )
    workload_hint: Optional[str] = Field(
        default="general",
        description="Hint for workload classifier (e.g. coding, reasoning, fast, general, research).",
    )
    preferred_provider: Optional[str] = Field(
        default=None,
        description="Preferred model provider (e.g. Anthropic, OpenAI, Gemini, DeepSeek).",
    )
    preferred_model: Optional[str] = Field(
        default=None,
        description="Specific model identifier if requested (e.g. claude-3-5-sonnet, gpt-4o).",
    )
    temperature: Optional[float] = Field(
        default=0.2,
        ge=0.0,
        le=2.0,
        description="Model sampling temperature.",
    )


class GetExecutionInput(BaseModel):
    """Input for retrieving execution summary."""
    execution_id: str = Field(
        ...,
        description="The unique INFUSE execution identifier (e.g. exec_12345678).",
        min_length=1,
        max_length=128,
    )


class ListExecutionsInput(BaseModel):
    """Input for querying and filtering execution history."""
    query: Optional[str] = Field(
        default=None,
        description="Optional search keyword to filter executions by description or task ID.",
    )
    state: Optional[str] = Field(
        default=None,
        description="Filter executions by canonical state (NORMAL, COST_PRESSURE, RUNAWAY, QUALITY_DEGRADED, PROVIDER_CONSTRAINED).",
    )
    agent: Optional[str] = Field(
        default=None,
        description="Filter executions by agent name (e.g. Claude Code, OpenCode, Codex).",
    )
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of execution records to return.",
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Pagination offset.",
    )


class GetPolicyInput(BaseModel):
    """Input for retrieving a governance policy."""
    policy_id: Optional[str] = Field(
        default=None,
        description="Policy ID (e.g. pol_default). If omitted, returns the currently active policy.",
    )


class ControlExecutionInput(BaseModel):
    """Input for requesting governed execution control."""
    execution_id: str = Field(
        ...,
        description="The unique INFUSE execution identifier to regulate.",
    )
    action: GovernorAction = Field(
        ...,
        description="Governed control action to dispatch (STOP, THROTTLE, SWITCH, CONTINUE).",
    )
    reason: Optional[str] = Field(
        default="User-initiated control request via ChatGPT",
        description="Human-readable justification for the control dispatch.",
    )
    delay_ms: Optional[int] = Field(
        default=None,
        ge=0,
        le=60000,
        description="Pacing delay in milliseconds if action is THROTTLE.",
    )
    target_model: Optional[str] = Field(
        default=None,
        description="Target model identifier if action is SWITCH.",
    )


# --- Tool Response Models ---

class ToolResponseEnvelope(BaseModel):
    """Standardized response envelope returned to ChatGPT for all tool operations."""
    success: bool = Field(..., description="Indicates whether the operation succeeded")
    tool_name: str = Field(..., description="Name of the invoked tool")
    category: ToolCategory = Field(..., description="Category classification of the tool")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Structured output payload")
    error: Optional[str] = Field(default=None, description="Sanitized error description if failed")
    error_code: Optional[str] = Field(default=None, description="Standardized error code")
    ui_card: Optional[Dict[str, Any]] = Field(default=None, description="Optional presentation card for ChatGPT rendering")
