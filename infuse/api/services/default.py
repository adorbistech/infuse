"""Default service implementations for Block 05 Universal HTTP API transport boundary."""

import uuid
from typing import Any, Dict, List, Optional

from infuse.api.errors import NotFoundError
from infuse.api.repositories.interfaces import IExecutionRepository, IPolicyRepository
from infuse.api.repositories.memory import InMemoryExecutionRepository, InMemoryPolicyRepository
from infuse.api.services.interfaces import (
    IExecutionService,
    IEventService,
    IPolicyService,
)
from infuse.contracts.events import ExecutionEvent
from infuse.contracts.execution import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    ExecutionTelemetry,
    NormalizedResponse,
)
from infuse.contracts.governor import GovernorAction, GovernorDecision
from infuse.contracts.policy import GovernancePolicy
from infuse.contracts.state import ExecutionState
from infuse.version import SCHEMA_VERSION


class DefaultExecutionService(IExecutionService):
    """Default execution service demonstrating the API boundary without implementing autonomous execution engine."""

    def __init__(self, repository: Optional[IExecutionRepository] = None) -> None:
        self.repository = repository or InMemoryExecutionRepository()

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        execution_id = f"exec_{uuid.uuid4().hex[:8]}"
        
        # Build deterministic response for Block 05 transport verification
        result = ExecutionResult(
            execution_id=execution_id,
            request_id=request.request_id,
            status=ExecutionStatus.COMPLETED,
            response=NormalizedResponse(
                content="Operation successfully received by INFUSE API transport boundary.",
                role="assistant"
            ),
            execution=ExecutionTelemetry(
                provider=request.requirements.preferred_providers[0] if request.requirements.preferred_providers else "DefaultProvider",
                model=request.requirements.preferred_models[0] if request.requirements.preferred_models else "DefaultModel",
                input_tokens=0,
                cached_tokens=0,
                output_tokens=0,
                total_tokens=0,
                cost_usd=0.0,
                latency_ms=10.0,
                requests_count=1,
                state=ExecutionState.NORMAL,
                metadata={
                    "agent_name": request.execution_context.agent_id or "AnonymousAgent",
                    "task_description": request.task.description or "Execution Task"
                }
            ),
            decision=GovernorDecision(
                action=GovernorAction.CONTINUE,
                reason="Initial execution within policy bounds."
            ),
            schema_version=SCHEMA_VERSION
        )
        self.repository.save(result)
        return result

    def get_execution(self, execution_id: str) -> Optional[ExecutionResult]:
        return self.repository.get_by_id(execution_id)

    def list_executions(
        self,
        query: Optional[str] = None,
        state: Optional[str] = None,
        agent: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        items = self.repository.list_all(query=query, state=state, agent=agent, limit=limit, offset=offset)
        total = self.repository.count(query=query, state=state, agent=agent)
        return {
            "executions": [item.model_dump() for item in items],
            "total": total,
            "limit": limit,
            "offset": offset,
            "schema_version": SCHEMA_VERSION
        }


class DefaultEventService(IEventService):
    """Default event ingestion service."""

    def __init__(self, repository: Optional[IExecutionRepository] = None) -> None:
        self.repository = repository or InMemoryExecutionRepository()

    def ingest_event(self, execution_id: str, event: ExecutionEvent) -> str:
        # Validate that target execution exists
        execution = self.repository.get_by_id(execution_id)
        if not execution:
            raise NotFoundError(f"Execution with ID '{execution_id}' does not exist.")

        # Ensure event execution_id matches route path parameter
        if event.execution_id != execution_id:
            event = event.model_copy(update={"execution_id": execution_id})

        self.repository.save_event(event)
        return event.event_id

    def get_events(self, execution_id: str) -> List[ExecutionEvent]:
        execution = self.repository.get_by_id(execution_id)
        if not execution:
            raise NotFoundError(f"Execution with ID '{execution_id}' does not exist.")
        return self.repository.get_events(execution_id)


class DefaultPolicyService(IPolicyService):
    """Default governance policy service."""

    def __init__(self, repository: Optional[IPolicyRepository] = None) -> None:
        self.repository = repository or InMemoryPolicyRepository()

    def get_active_policy(self) -> Optional[GovernancePolicy]:
        return self.repository.get_active()

    def get_policy(self, policy_id: str) -> Optional[GovernancePolicy]:
        return self.repository.get_by_id(policy_id)

    def list_policies(self) -> List[GovernancePolicy]:
        return self.repository.list_all()

    def update_policy(self, policy_id: str, policy: GovernancePolicy) -> GovernancePolicy:
        if policy.policy_id != policy_id:
            policy = policy.model_copy(update={"policy_id": policy_id})
        return self.repository.save(policy)
