"""Service interfaces decoupling HTTP transport routes from core engine implementations."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from infuse.contracts.events import ExecutionEvent
from infuse.contracts.execution import ExecutionRequest, ExecutionResult
from infuse.contracts.policy import GovernancePolicy


class IExecutionService(ABC):
    """Abstract service boundary for execution dispatch and query."""

    @abstractmethod
    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """Process an execution request."""
        raise NotImplementedError

    @abstractmethod
    def get_execution(self, execution_id: str) -> Optional[ExecutionResult]:
        """Retrieve execution telemetry and result by ID."""
        raise NotImplementedError

    @abstractmethod
    def list_executions(
        self,
        query: Optional[str] = None,
        state: Optional[str] = None,
        agent: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """List and filter execution summaries."""
        raise NotImplementedError


class IEventService(ABC):
    """Abstract service boundary for execution event ingestion and retrieval."""

    @abstractmethod
    def ingest_event(self, execution_id: str, event: ExecutionEvent) -> str:
        """Validate and ingest an execution event. Returns event_id."""
        raise NotImplementedError

    @abstractmethod
    def get_events(self, execution_id: str) -> List[ExecutionEvent]:
        """Retrieve events associated with an execution run."""
        raise NotImplementedError


class IPolicyService(ABC):
    """Abstract service boundary for governance policy management."""

    @abstractmethod
    def get_active_policy(self) -> Optional[GovernancePolicy]:
        """Retrieve currently active governance policy."""
        raise NotImplementedError

    @abstractmethod
    def get_policy(self, policy_id: str) -> Optional[GovernancePolicy]:
        """Retrieve governance policy by ID."""
        raise NotImplementedError

    @abstractmethod
    def list_policies(self) -> List[GovernancePolicy]:
        """List all policy revisions."""
        raise NotImplementedError

    @abstractmethod
    def update_policy(self, policy_id: str, policy: GovernancePolicy) -> GovernancePolicy:
        """Create or update a governance policy."""
        raise NotImplementedError
