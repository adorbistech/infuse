"""In-memory Execution Context repository implementation."""

from typing import Dict, List, Optional

from infuse.context.interfaces import IExecutionContextRepository
from infuse.context.models import ExecutionContextRecord


class InMemoryExecutionContextRepository(IExecutionContextRepository):
    """Deterministic in-memory implementation of IExecutionContextRepository."""

    def __init__(self) -> None:
        self._contexts: Dict[str, ExecutionContextRecord] = {}
        self._by_request_id: Dict[str, str] = {}

    def save(self, context: ExecutionContextRecord) -> ExecutionContextRecord:
        snapshot = context.model_copy(deep=True)
        self._contexts[snapshot.execution_id] = snapshot
        self._by_request_id[snapshot.request_id] = snapshot.execution_id
        return snapshot.model_copy(deep=True)

    def get_by_id(self, execution_id: str) -> Optional[ExecutionContextRecord]:
        ctx = self._contexts.get(execution_id)
        if ctx:
            return ctx.model_copy(deep=True)
        return None

    def get_by_request_id(self, request_id: str) -> Optional[ExecutionContextRecord]:
        exec_id = self._by_request_id.get(request_id)
        if exec_id and exec_id in self._contexts:
            return self._contexts[exec_id].model_copy(deep=True)
        return None

    def list_all(
        self,
        session_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ExecutionContextRecord]:
        results = list(self._contexts.values())
        if session_id:
            results = [c for c in results if c.runtime.session_id == session_id]
        if workflow_id:
            results = [c for c in results if c.runtime.workflow_id == workflow_id]
        if agent_id:
            results = [c for c in results if c.agent.agent_id == agent_id]

        paginated = results[offset:offset + limit]
        return [c.model_copy(deep=True) for c in paginated]

    def count(
        self,
        session_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        agent_id: Optional[str] = None
    ) -> int:
        return len(self.list_all(
            session_id=session_id,
            workflow_id=workflow_id,
            agent_id=agent_id,
            limit=1000000,
            offset=0
        ))
