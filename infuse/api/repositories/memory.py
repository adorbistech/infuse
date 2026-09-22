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
    """Deterministic in-memory implementation of IPolicyRepository supporting revision history and immutability."""

    def __init__(self, seed_defaults: bool = True) -> None:
        self._policies: Dict[str, GovernancePolicy] = {}
        self._revisions: Dict[str, List[GovernancePolicy]] = {}
        self._active_key: Optional[tuple[str, str]] = None
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
        if self._active_key:
            pid, ver = self._active_key
            for rev in self._revisions.get(pid, []):
                if rev.version == ver and rev.is_active:
                    return rev.model_copy(deep=True)

        for p in self._policies.values():
            if p.is_active:
                return p.model_copy(deep=True)
        return None

    def get_by_id(self, policy_id: str) -> Optional[GovernancePolicy]:
        policy = self._policies.get(policy_id)
        if policy:
            return policy.model_copy(deep=True)
        return None

    def get_revision(self, policy_id: str, version: str) -> Optional[GovernancePolicy]:
        for rev in self._revisions.get(policy_id, []):
            if rev.version == version:
                return rev.model_copy(deep=True)
        return None

    def get_history(self, policy_id: str) -> List[GovernancePolicy]:
        return [rev.model_copy(deep=True) for rev in self._revisions.get(policy_id, [])]

    def save(self, policy: GovernancePolicy) -> GovernancePolicy:
        # Clone to preserve immutable snapshot
        snapshot = policy.model_copy(deep=True)
        pid = snapshot.policy_id

        if pid not in self._revisions:
            self._revisions[pid] = []

        # If revision with this version already exists, replace it; otherwise append
        existing_idx = None
        for i, rev in enumerate(self._revisions[pid]):
            if rev.version == snapshot.version:
                existing_idx = i
                break

        if existing_idx is not None:
            self._revisions[pid][existing_idx] = snapshot
        else:
            self._revisions[pid].append(snapshot)

        self._policies[pid] = snapshot

        if snapshot.is_active:
            self._active_key = (pid, snapshot.version)
            # Deactivate all other policies and revisions
            for p_id, rev_list in self._revisions.items():
                for rev in rev_list:
                    if p_id != pid or rev.version != snapshot.version:
                        rev.is_active = False
            for p_id in self._policies:
                if p_id != pid:
                    self._policies[p_id].is_active = False

        return snapshot.model_copy(deep=True)

    def set_active(self, policy_id: str, version: Optional[str] = None) -> GovernancePolicy:
        revisions = self._revisions.get(policy_id, [])
        if not revisions:
            raise KeyError(f"Policy '{policy_id}' not found.")

        target: Optional[GovernancePolicy] = None
        if version:
            for rev in revisions:
                if rev.version == version:
                    target = rev
                    break
            if not target:
                raise KeyError(f"Policy '{policy_id}' version '{version}' not found.")
        else:
            target = self._policies.get(policy_id) or revisions[-1]

        target.is_active = True
        self._active_key = (policy_id, target.version)
        self._policies[policy_id] = target

        # Deactivate all other revisions
        for p_id, rev_list in self._revisions.items():
            for rev in rev_list:
                if p_id != policy_id or rev.version != target.version:
                    rev.is_active = False
        for p_id in self._policies:
            if p_id != policy_id:
                self._policies[p_id].is_active = False

        return target.model_copy(deep=True)

    def list_all(self, include_historical: bool = False) -> List[GovernancePolicy]:
        if include_historical:
            all_revs: List[GovernancePolicy] = []
            for rev_list in self._revisions.values():
                all_revs.extend([r.model_copy(deep=True) for r in rev_list])
            return all_revs
        return [p.model_copy(deep=True) for p in self._policies.values()]

