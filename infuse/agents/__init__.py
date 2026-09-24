"""INFUSE Universal Agent Adapter Layer (Block 23)."""

from infuse.contracts.capabilities import (
    AdapterRegistration,
    AdapterType,
    AgentCapability,
)
from infuse.contracts.control import (
    ControlCapability,
    ControlOperation,
    ControlResult,
    ControlStatus,
)
from infuse.contracts.governor import GovernorAction
from infuse.agents.errors import (
    AgentAdapterError,
    AgentControlError,
    AgentExecutionError,
    AgentUnavailableError,
    UnsupportedAgentOperationError,
)
from infuse.agents.interfaces import IUniversalAgentAdapter
from infuse.agents.models import (
    AgentErrorRecord,
    AgentExecutionSession,
    AgentIdentity,
    AgentStepRequest,
    AgentStepResponse,
)
from infuse.agents.reference import ReferenceUniversalAgentAdapter
from infuse.agents.claude import ClaudeCodeAdapter
from infuse.agents.opencode import OpenCodeAdapter
from infuse.agents.codex import CodexAdapter

__all__ = [
    "AdapterRegistration",
    "AdapterType",
    "AgentCapability",
    "ControlCapability",
    "ControlOperation",
    "ControlResult",
    "ControlStatus",
    "GovernorAction",
    "AgentAdapterError",
    "AgentControlError",
    "AgentExecutionError",
    "AgentUnavailableError",
    "UnsupportedAgentOperationError",
    "IUniversalAgentAdapter",
    "AgentIdentity",
    "AgentStepRequest",
    "AgentStepResponse",
    "AgentErrorRecord",
    "AgentExecutionSession",
    "ReferenceUniversalAgentAdapter",
    "ClaudeCodeAdapter",
    "OpenCodeAdapter",
    "CodexAdapter",
]
