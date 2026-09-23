"""Interface definitions for Block 21 Governor Engine."""

from abc import ABC, abstractmethod
from typing import List, Optional

from infuse.contracts.governor import GovernorDecision, GovernorDecisionRecord
from infuse.contracts.policy import GovernancePolicy
from infuse.contracts.state import ExecutionStateSnapshot
from infuse.events.interfaces import IEventBus


class IGovernorEngine(ABC):
    """Abstract interface for policy and state evaluation producing canonical Governor decisions."""

    @abstractmethod
    def evaluate(
        self,
        execution_id: str,
        state_snapshot: ExecutionStateSnapshot,
        policy: Optional[GovernancePolicy] = None,
        additional_signals: Optional[dict] = None
    ) -> GovernorDecisionRecord:
        """Evaluate policy against execution state snapshot to produce an immutable GovernorDecisionRecord."""
        pass

    @abstractmethod
    def get_latest_decision(self, execution_id: str) -> Optional[GovernorDecisionRecord]:
        """Retrieve the latest decision record for an execution."""
        pass

    @abstractmethod
    def get_decision_history(self, execution_id: str) -> List[GovernorDecisionRecord]:
        """Retrieve the complete chronological decision history for an execution."""
        pass

    @abstractmethod
    def list_decisions(self) -> List[GovernorDecisionRecord]:
        """List the latest decision records across all active executions."""
        pass

    @abstractmethod
    def attach_to_bus(self, bus: IEventBus) -> None:
        """Attach to event bus for publishing GovernorDecision events."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all in-memory decision records and histories."""
        pass
