"""Interface definitions for Block 20 Execution State Engine."""

from abc import ABC, abstractmethod
from typing import List, Optional

from infuse.contracts.policy import GovernancePolicy
from infuse.contracts.state import ExecutionStateSnapshot
from infuse.economics.models import ExecutionEconomicSummary
from infuse.events.interfaces import IEventBus
from infuse.health.models import ExecutionHealthSummary
from infuse.observer.models import ExecutionTokenSummary
from infuse.state.models import ObservationBundle
from infuse.tools.models import ExecutionToolSummary
from infuse.web.models import ExecutionWebSummary


class IExecutionStateEngine(ABC):
    """Abstract interface for normalized observation aggregation and deterministic state derivation."""

    @abstractmethod
    def derive_state(
        self,
        execution_id: str,
        token_summary: Optional[ExecutionTokenSummary] = None,
        economic_summary: Optional[ExecutionEconomicSummary] = None,
        health_summary: Optional[ExecutionHealthSummary] = None,
        tool_summary: Optional[ExecutionToolSummary] = None,
        web_summary: Optional[ExecutionWebSummary] = None,
        policy: Optional[GovernancePolicy] = None,
        context_metadata: Optional[dict] = None
    ) -> ExecutionStateSnapshot:
        """Derive the canonical ExecutionStateSnapshot from observation evidence and active policy."""
        pass

    @abstractmethod
    def update_bundle(self, bundle: ObservationBundle) -> ExecutionStateSnapshot:
        """Update observations for an execution and recompute the canonical state snapshot."""
        pass

    @abstractmethod
    def get_state(self, execution_id: str) -> Optional[ExecutionStateSnapshot]:
        """Retrieve the latest state snapshot for an execution."""
        pass

    @abstractmethod
    def get_history(self, execution_id: str) -> List[ExecutionStateSnapshot]:
        """Retrieve the full transition history snapshots for an execution."""
        pass

    @abstractmethod
    def list_states(self) -> List[ExecutionStateSnapshot]:
        """List current state snapshots for all active executions."""
        pass

    @abstractmethod
    def attach_to_bus(self, bus: IEventBus) -> None:
        """Attach to event bus for state change notifications."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all in-memory execution state snapshots and history."""
        pass
