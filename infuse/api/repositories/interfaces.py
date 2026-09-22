"""Repository interfaces for execution, events, and policy persistence boundaries."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from infuse.contracts.events import ExecutionEvent
from infuse.contracts.execution import ExecutionResult
from infuse.contracts.policy import GovernancePolicy


class IExecutionRepository(ABC):
    """Abstract repository for storing and querying execution records and events."""

    @abstractmethod
    def save(self, execution: ExecutionResult) -> None:
        """Persist or update an execution result."""
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, execution_id: str) -> Optional[ExecutionResult]:
        """Retrieve an execution result by unique identifier."""
        raise NotImplementedError

    @abstractmethod
    def list_all(
        self,
        query: Optional[str] = None,
        state: Optional[str] = None,
        agent: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ExecutionResult]:
        """Query and filter execution summaries."""
        raise NotImplementedError

    @abstractmethod
    def count(
        self,
        query: Optional[str] = None,
        state: Optional[str] = None,
        agent: Optional[str] = None
    ) -> int:
        """Count execution records matching filter criteria."""
        raise NotImplementedError

    @abstractmethod
    def save_event(self, event: ExecutionEvent) -> None:
        """Persist an execution event."""
        raise NotImplementedError

    @abstractmethod
    def get_events(self, execution_id: str) -> List[ExecutionEvent]:
        """Retrieve all events associated with an execution ID."""
        raise NotImplementedError


class IPolicyRepository(ABC):
    """Abstract repository for storing and retrieving governance policies and revision history."""

    @abstractmethod
    def get_active(self) -> Optional[GovernancePolicy]:
        """Retrieve the currently active governance policy."""
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, policy_id: str) -> Optional[GovernancePolicy]:
        """Retrieve the latest revision of a governance policy by ID."""
        raise NotImplementedError

    @abstractmethod
    def get_revision(self, policy_id: str, version: str) -> Optional[GovernancePolicy]:
        """Retrieve a specific historical revision of a policy by ID and version."""
        raise NotImplementedError

    @abstractmethod
    def get_history(self, policy_id: str) -> List[GovernancePolicy]:
        """Retrieve all historical revisions for a policy in chronological order."""
        raise NotImplementedError

    @abstractmethod
    def save(self, policy: GovernancePolicy) -> GovernancePolicy:
        """Persist a policy revision."""
        raise NotImplementedError

    @abstractmethod
    def set_active(self, policy_id: str, version: Optional[str] = None) -> GovernancePolicy:
        """Designate a specific policy revision as active."""
        raise NotImplementedError

    @abstractmethod
    def list_all(self, include_historical: bool = False) -> List[GovernancePolicy]:
        """List policies, optionally including historical revisions."""
        raise NotImplementedError

