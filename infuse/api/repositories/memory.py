"""In-memory repository implementations for deterministic testing and Block 05 API boundary."""

from typing import Dict, List, Optional

from infuse.api.repositories.interfaces import IExecutionRepository, IPolicyRepository
from infuse.contracts.events import ExecutionEvent, EventType, EventSource
from infuse.contracts.execution import (
    ExecutionResult,
    ExecutionStatus,
    ExecutionTelemetry,
    NormalizedResponse,
)
from infuse.contracts.governor import GovernorAction, GovernorDecision
from infuse.contracts.policy import GovernancePolicy
from infuse.contracts.state import ExecutionState


class InMemoryExecutionRepository(IExecutionRepository):
    """Deterministic in-memory implementation of IExecutionRepository."""

    def __init__(self, seed_defaults: bool = True) -> None:
        self._executions: Dict[str, ExecutionResult] = {}
        self._events: Dict[str, List[ExecutionEvent]] = {}
        if seed_defaults:
            self._seed_default_data()

    def _seed_default_data(self) -> None:
        default_exec = ExecutionResult(
            execution_id="exec_01J8K7A2",
            request_id="req_01J8K7A0",
            status=ExecutionStatus.RUNNING,
            response=NormalizedResponse(
                content="Authentication middleware refactored to use decoupled JWT validators.",
                role="assistant"
            ),
            execution=ExecutionTelemetry(
                provider="Anthropic",
                model="Claude Sonnet",
                input_tokens=42800,
                cached_tokens=18400,
                output_tokens=8280,
                total_tokens=69480,
                cost_usd=0.184,
                latency_ms=1240.0,
                requests_count=14,
                retries_count=0,
                tool_calls_count=11,
                web_requests_count=6,
                errors_count=0,
                state=ExecutionState.COST_PRESSURE,
                metadata={"agent_name": "OpenCode", "task_description": "Refactor authentication middleware to use decoupled JWT validators"}
            ),
            decision=GovernorDecision(
                action=GovernorAction.OPTIMIZE,
                reason="Cost velocity approaching budget pacing boundary.",
                reason_codes=["COST_LIMIT_WARNING"]
            )
        )
        self.save(default_exec)

        # Seed sample events
        sample_event = ExecutionEvent(
            event_id="evt_01",
            execution_id="exec_01J8K7A2",
            type=EventType.EXECUTION_STARTED,
            source=EventSource.AGENT,
            sequence=1,
            payload={"message": "Execution started by OpenCode"}
        )
        self.save_event(sample_event)

    def save(self, execution: ExecutionResult) -> None:
        self._executions[execution.execution_id] = execution

    def get_by_id(self, execution_id: str) -> Optional[ExecutionResult]:
        return self._executions.get(execution_id)

    def list_all(
        self,
        query: Optional[str] = None,
        state: Optional[str] = None,
        agent: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ExecutionResult]:
        results = list(self._executions.values())
        if query:
            q = query.lower()
            results = [
                e for e in results
                if q in e.execution_id.lower() or
                   (e.execution.metadata.get("task_description", "").lower().find(q) != -1) or
                   (e.execution.metadata.get("agent_name", "").lower().find(q) != -1)
            ]
        if state and state.upper() != "ALL":
            results = [e for e in results if e.execution.state == state or e.execution.state.value == state]
        if agent and agent.upper() != "ALL":
            results = [e for e in results if e.execution.metadata.get("agent_name") == agent]

        return results[offset:offset + limit]

    def count(
        self,
        query: Optional[str] = None,
        state: Optional[str] = None,
        agent: Optional[str] = None
    ) -> int:
        return len(self.list_all(query=query, state=state, agent=agent, limit=1000000, offset=0))

    def save_event(self, event: ExecutionEvent) -> None:
        if event.execution_id not in self._events:
            self._events[event.execution_id] = []
        self._events[event.execution_id].append(event)

    def get_events(self, execution_id: str) -> List[ExecutionEvent]:
        return self._events.get(execution_id, [])


class InMemoryPolicyRepository(IPolicyRepository):
    """Deterministic in-memory implementation of IPolicyRepository."""

    def __init__(self, seed_defaults: bool = True) -> None:
        self._policies: Dict[str, GovernancePolicy] = {}
        self._active_id: Optional[str] = None
        if seed_defaults:
            self._seed_default_data()

    def _seed_default_data(self) -> None:
        default_policy = GovernancePolicy(
            policy_id="pol_default",
            name="Default Execution Policy",
            version="1.0.0",
            is_active=True
        )
        self.save(default_policy)

    def get_active(self) -> Optional[GovernancePolicy]:
        if self._active_id and self._active_id in self._policies:
            return self._policies[self._active_id]
        for p in self._policies.values():
            if p.is_active:
                return p
        return None

    def get_by_id(self, policy_id: str) -> Optional[GovernancePolicy]:
        return self._policies.get(policy_id)

    def save(self, policy: GovernancePolicy) -> GovernancePolicy:
        self._policies[policy.policy_id] = policy
        if policy.is_active:
            self._active_id = policy.policy_id
        return policy

    def list_all(self) -> List[GovernancePolicy]:
        return list(self._policies.values())
