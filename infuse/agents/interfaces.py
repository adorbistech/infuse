"""Interface definitions for Block 23 Universal Agent Adapter."""

from abc import abstractmethod
from typing import Any, Dict, List, Optional

from infuse.contracts.capabilities import AgentCapability
from infuse.contracts.control import (
    ControlCapability,
    ControlOperation,
    ControlResult,
)
from infuse.contracts.governor import GovernorAction
from infuse.control.interfaces import IControlExecutor
from infuse.events.interfaces import IEventBus
from infuse.agents.models import (
    AgentErrorRecord,
    AgentExecutionSession,
    AgentIdentity,
    AgentStepRequest,
    AgentStepResponse,
)


class IUniversalAgentAdapter(IControlExecutor):
    """Universal interface for autonomous agent adapters connecting to INFUSE.

    Abstracts agent vendor specifics while exposing capability discovery,
    normalized step execution, execution attachment, and control operation execution.
    """

    @property
    @abstractmethod
    def identity(self) -> AgentIdentity:
        """Normalized identity of this agent adapter."""
        pass

    @property
    def executor_id(self) -> str:
        """Executor identifier implementing IControlExecutor."""
        return self.identity.agent_id

    @abstractmethod
    def get_agent_capability(self) -> AgentCapability:
        """Expose full agent capabilities."""
        pass

    def get_capability(self) -> ControlCapability:
        """Expose declared control capabilities implementing IControlExecutor."""
        return self.get_agent_capability().control_capabilities

    @abstractmethod
    def supports_cancel(self) -> bool:
        """Check whether the underlying agent supports graceful cancellation."""
        pass

    @abstractmethod
    def supports_throttle(self) -> bool:
        """Check whether the underlying agent supports rate/delay throttling."""
        pass

    @abstractmethod
    def supports_next_step_switch(self) -> bool:
        """Check whether the underlying agent supports switching provider/model at step boundaries."""
        pass

    @abstractmethod
    def supports_terminate(self) -> bool:
        """Check whether the underlying agent supports hard process termination."""
        pass

    @abstractmethod
    def supports_action(self, action: GovernorAction) -> bool:
        """Check whether a specific GovernorAction is physically supported by the agent."""
        pass

    @abstractmethod
    def attach_execution(
        self,
        execution_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AgentExecutionSession:
        """Attach a canonical execution run to this agent adapter."""
        pass

    @abstractmethod
    def detach_execution(self, execution_id: str) -> None:
        """Detach an execution run from this agent adapter."""
        pass

    @abstractmethod
    def get_session(self, execution_id: str) -> Optional[AgentExecutionSession]:
        """Retrieve the active execution session if attached."""
        pass

    @abstractmethod
    def execute_step(self, request: AgentStepRequest) -> AgentStepResponse:
        """Execute a single normalized agent step."""
        pass

    @abstractmethod
    def execute_control(self, operation: ControlOperation) -> ControlResult:
        """Execute a physical control command (implementing IControlExecutor)."""
        pass

    @abstractmethod
    def normalize_error(self, raw_error: Any, execution_id: Optional[str] = None) -> AgentErrorRecord:
        """Normalize an arbitrary agent runtime error into a standard AgentErrorRecord."""
        pass

    @abstractmethod
    def attach_to_bus(self, bus: IEventBus) -> None:
        """Attach to event bus for publishing agent execution events."""
        pass
