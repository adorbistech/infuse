"""Interface definitions for Block 22 Execution Control Boundary."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from infuse.contracts.control import (
    ControlCapability,
    ControlOperation,
    ControlResult,
)
from infuse.contracts.governor import GovernorAction
from infuse.control.models import ControlAuditRecord
from infuse.events.interfaces import IEventBus


class IControlExecutor(ABC):
    """Abstract interface for a physical control mechanism (e.g. agent adapter, process supervisor)."""

    @property
    @abstractmethod
    def executor_id(self) -> str:
        """Identifier of this control executor."""
        pass

    @abstractmethod
    def get_capability(self) -> ControlCapability:
        """Declare capabilities supported by this executor."""
        pass

    @abstractmethod
    def execute_control(self, operation: ControlOperation) -> ControlResult:
        """Physically execute the requested control operation."""
        pass


class IExecutionControlBoundary(ABC):
    """Abstract interface for the Execution Control Boundary."""

    @abstractmethod
    def register_capability(self, execution_id: str, capability: ControlCapability) -> None:
        """Register declared capabilities for a given execution run."""
        pass

    @abstractmethod
    def register_executor(self, execution_id: str, executor: IControlExecutor) -> None:
        """Register a physical control executor for a given execution run."""
        pass

    @abstractmethod
    def get_capability(self, execution_id: str) -> Optional[ControlCapability]:
        """Retrieve declared capabilities for an execution."""
        pass

    @abstractmethod
    def supports_cancel(self, execution_id: str) -> bool:
        """Check whether the target execution supports cancellation."""
        pass

    @abstractmethod
    def supports_throttle(self, execution_id: str) -> bool:
        """Check whether the target execution supports rate/delay throttling."""
        pass

    @abstractmethod
    def supports_next_step_switch(self, execution_id: str) -> bool:
        """Check whether the target execution supports next-step model/provider switching."""
        pass

    @abstractmethod
    def supports_terminate(self, execution_id: str) -> bool:
        """Check whether the target execution supports process termination."""
        pass

    @abstractmethod
    def supports_action(self, execution_id: str, action: GovernorAction) -> bool:
        """Check whether a specific GovernorAction can be physically handled."""
        pass

    @abstractmethod
    def dispatch_control(
        self,
        execution_id: str,
        action: GovernorAction,
        params: Optional[Dict[str, Any]] = None,
        operation_id: Optional[str] = None
    ) -> ControlResult:
        """Validate capability and dispatch a Governor decision to the physical control layer."""
        pass

    @abstractmethod
    def get_latest_result(self, execution_id: str) -> Optional[ControlResult]:
        """Retrieve the most recent control result for an execution."""
        pass

    @abstractmethod
    def get_control_history(self, execution_id: str) -> List[ControlAuditRecord]:
        """Retrieve all control operations and outcomes for an execution in chronological order."""
        pass

    @abstractmethod
    def attach_to_bus(self, bus: IEventBus) -> None:
        """Attach to event bus for publishing ControlActionIssued events."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all in-memory capabilities, executors, and history."""
        pass
