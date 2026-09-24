"""Models and Contract Re-exports for Block 23 Universal Agent Adapter."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import Field

from infuse.contracts.capabilities import (
    AdapterRegistration,
    AdapterType,
    AgentCapability,
)
from infuse.contracts.common import InfuseBaseModel, utc_now
from infuse.contracts.control import (
    ControlCapability,
    ControlOperation,
    ControlResult,
    ControlStatus,
)
from infuse.contracts.governor import GovernorAction


class AgentIdentity(InfuseBaseModel):
    """Normalized identity of an autonomous agent adapter."""
    agent_id: str = Field(..., description="Unique adapter instance identifier.")
    agent_name: str = Field(..., description="Canonical agent name (e.g. opencode, claudecode, codex, reference).")
    version: str = Field(default="1.0.0", description="Agent adapter semantic version.")
    runtime_type: str = Field(default="universal", description="Runtime substrate category.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional agent metadata.")


class AgentStepRequest(InfuseBaseModel):
    """Normalized step execution request sent to an agent."""
    execution_id: str = Field(..., description="Canonical execution identifier.")
    step_index: int = Field(default=0, ge=0, description="Step index in agent execution loop.")
    prompt: Optional[str] = Field(default=None, description="Current step prompt or instruction.")
    messages: List[Dict[str, Any]] = Field(default_factory=list, description="Conversation history or trajectory.")
    tools: Optional[List[Dict[str, Any]]] = Field(default=None, description="Available tool definitions.")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Agent parameters.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Step-level contextual metadata.")


class AgentStepResponse(InfuseBaseModel):
    """Normalized step execution response returned from an agent."""
    execution_id: str = Field(..., description="Canonical execution identifier.")
    step_index: int = Field(default=0, ge=0, description="Completed step index.")
    content: Optional[str] = Field(default=None, description="Agent generated text output.")
    tool_calls: Optional[List[Dict[str, Any]]] = Field(default=None, description="Requested tool invocations.")
    finish_reason: Optional[str] = Field(default=None, description="Step termination reason (e.g. tool_calls, complete, stop).")
    raw_output: Optional[Dict[str, Any]] = Field(default=None, description="Underlying raw output if available.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Step execution telemetry and metadata.")


class AgentErrorRecord(InfuseBaseModel):
    """Normalized error record produced by an agent adapter."""
    error_code: str = Field(..., description="Categorical error code.")
    message: str = Field(..., description="Human-readable error explanation.")
    details: Dict[str, Any] = Field(default_factory=dict, description="Error context details.")
    timestamp: datetime = Field(default_factory=utc_now, description="Timestamp of error occurrence.")


class AgentExecutionSession(InfuseBaseModel):
    """Session tracking record for an execution attached to an agent adapter."""
    execution_id: str = Field(..., description="Canonical execution identifier.")
    agent_id: str = Field(..., description="Attached agent adapter identifier.")
    attached_at: datetime = Field(default_factory=utc_now, description="Attachment timestamp.")
    step_count: int = Field(default=0, ge=0, description="Total steps executed in this session.")
    is_active: bool = Field(default=True, description="Whether the session is currently active.")
    control_history: List[ControlOperation] = Field(default_factory=list, description="History of received control operations.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Session metadata.")


__all__ = [
    "AdapterRegistration",
    "AdapterType",
    "AgentCapability",
    "ControlCapability",
    "ControlOperation",
    "ControlResult",
    "ControlStatus",
    "GovernorAction",
    "AgentIdentity",
    "AgentStepRequest",
    "AgentStepResponse",
    "AgentErrorRecord",
    "AgentExecutionSession",
]
