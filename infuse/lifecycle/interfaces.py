"""Abstract interfaces for INFUSE Execution Lifecycle management."""

from abc import ABC, abstractmethod
from typing import List, Optional

from infuse.contracts.execution import ExecutionRequest, ExecutionResult
from infuse.lifecycle.models import ExecutionLifecycleRecord, LifecycleState


class IExecutionLifecycleRepository(ABC):
    """Storage repository interface for execution lifecycle records."""

    @abstractmethod
    def save(self, record: ExecutionLifecycleRecord) -> ExecutionLifecycleRecord:
        """Persist or update an execution lifecycle record."""
        pass

    @abstractmethod
    def get(self, execution_id: str) -> Optional[ExecutionLifecycleRecord]:
        """Retrieve an execution lifecycle record by execution_id."""
        pass

    @abstractmethod
    def exists(self, execution_id: str) -> bool:
        """Check if an execution record exists."""
        pass

    @abstractmethod
    def list_executions(
        self,
        state: Optional[LifecycleState] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ExecutionLifecycleRecord]:
        """List execution lifecycle records with optional state filtering and pagination."""
        pass

    @abstractmethod
    def update_state(
        self,
        execution_id: str,
        new_state: LifecycleState,
        reason: Optional[str] = None
    ) -> ExecutionLifecycleRecord:
        """Transition an execution to a new lifecycle state."""
        pass


class IExecutionLifecycleService(ABC):
    """Authoritative execution lifecycle service interface coordinating execution flow."""

    @abstractmethod
    def create_execution(
        self,
        request: ExecutionRequest,
        execution_id: Optional[str] = None
    ) -> ExecutionLifecycleRecord:
        """Initialize an execution lifecycle record from an execution request."""
        pass

    @abstractmethod
    def execute(
        self,
        request: ExecutionRequest,
        execution_id: Optional[str] = None
    ) -> ExecutionResult:
        """Orchestrate full execution pipeline and return normalized ExecutionResult."""
        pass

    @abstractmethod
    def get_execution(self, execution_id: str) -> Optional[ExecutionLifecycleRecord]:
        """Retrieve execution lifecycle record by execution_id."""
        pass

    @abstractmethod
    def list_executions(
        self,
        state: Optional[LifecycleState] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ExecutionLifecycleRecord]:
        """List execution lifecycle records."""
        pass

    @abstractmethod
    def cancel_execution(
        self,
        execution_id: str,
        reason: Optional[str] = None
    ) -> ExecutionLifecycleRecord:
        """Cancel an active or pending execution."""
        pass
