"""Execution Context Service implementation."""

from typing import List, Optional

from infuse.context.builder import ExecutionContextBuilder
from infuse.context.interfaces import IExecutionContextRepository, IExecutionContextService
from infuse.context.models import ExecutionContextRecord
from infuse.context.repository import InMemoryExecutionContextRepository
from infuse.contracts.execution import ExecutionRequest


class ExecutionContextService(IExecutionContextService):
    """Default service implementation for Execution Context boundary."""

    def __init__(self, repository: Optional[IExecutionContextRepository] = None) -> None:
        self.repository = repository or InMemoryExecutionContextRepository()

    def create_context(
        self,
        request: ExecutionRequest,
        execution_id: Optional[str] = None,
        parent_execution_id: Optional[str] = None
    ) -> ExecutionContextRecord:
        """Construct, validate, normalize, and persist an ExecutionContextRecord from an ExecutionRequest."""
        builder = ExecutionContextBuilder.from_execution_request(
            request=request,
            execution_id=execution_id,
            parent_execution_id=parent_execution_id
        )
        context_record = builder.build()
        return self.repository.save(context_record)

    def get_context(self, execution_id: str) -> Optional[ExecutionContextRecord]:
        """Retrieve an ExecutionContextRecord by execution_id."""
        return self.repository.get_by_id(execution_id)

    def list_contexts(
        self,
        session_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ExecutionContextRecord]:
        """List ExecutionContextRecords matching optional filters."""
        return self.repository.list_all(
            session_id=session_id,
            workflow_id=workflow_id,
            agent_id=agent_id,
            limit=limit,
            offset=offset
        )
