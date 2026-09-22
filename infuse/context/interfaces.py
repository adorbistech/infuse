"""Execution Context interface definitions."""

from abc import ABC, abstractmethod
from typing import List, Optional

from infuse.context.models import ExecutionContextRecord
from infuse.contracts.execution import ExecutionRequest


class IExecutionContextRepository(ABC):
    """Abstract repository for persisting and querying execution context snapshots."""

    @abstractmethod
    def save(self, context: ExecutionContextRecord) -> ExecutionContextRecord:
        """Persist an execution context snapshot."""
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, execution_id: str) -> Optional[ExecutionContextRecord]:
        """Retrieve execution context by execution_id."""
        raise NotImplementedError

    @abstractmethod
    def get_by_request_id(self, request_id: str) -> Optional[ExecutionContextRecord]:
        """Retrieve execution context by request_id."""
        raise NotImplementedError

    @abstractmethod
    def list_all(
        self,
        session_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ExecutionContextRecord]:
        """List execution contexts matching optional filtering dimensions."""
        raise NotImplementedError

    @abstractmethod
    def count(
        self,
        session_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        agent_id: Optional[str] = None
    ) -> int:
        """Count execution contexts matching optional filtering dimensions."""
        raise NotImplementedError


class IExecutionContextService(ABC):
    """Abstract service boundary for managing execution contexts."""

    @abstractmethod
    def create_context(
        self,
        request: ExecutionRequest,
        execution_id: Optional[str] = None,
        parent_execution_id: Optional[str] = None
    ) -> ExecutionContextRecord:
        """Validate, normalize, build, and persist an execution context from an ExecutionRequest."""
        raise NotImplementedError

    @abstractmethod
    def get_context(self, execution_id: str) -> Optional[ExecutionContextRecord]:
        """Retrieve an execution context by execution_id."""
        raise NotImplementedError

    @abstractmethod
    def list_contexts(
        self,
        session_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ExecutionContextRecord]:
        """List execution contexts."""
        raise NotImplementedError
