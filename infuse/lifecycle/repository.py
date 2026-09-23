"""In-memory thread-safe implementation of IExecutionLifecycleRepository."""

import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

from infuse.lifecycle.errors import (
    ExecutionNotFoundError,
    InvalidStateTransitionError,
)
from infuse.lifecycle.interfaces import IExecutionLifecycleRepository
from infuse.lifecycle.models import (
    ExecutionLifecycleRecord,
    LifecycleState,
    LifecycleTransition,
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# Valid lifecycle state transitions map
VALID_TRANSITIONS: Dict[LifecycleState, Set[LifecycleState]] = {
    LifecycleState.CREATED: {
        LifecycleState.INITIALIZING,
        LifecycleState.CANCELLED,
        LifecycleState.FAILED,
    },
    LifecycleState.INITIALIZING: {
        LifecycleState.ROUTED,
        LifecycleState.RUNNING,
        LifecycleState.CANCELLED,
        LifecycleState.FAILED,
    },
    LifecycleState.ROUTED: {
        LifecycleState.RUNNING,
        LifecycleState.CANCELLED,
        LifecycleState.FAILED,
    },
    LifecycleState.RUNNING: {
        LifecycleState.COMPLETED,
        LifecycleState.FAILED,
        LifecycleState.CANCELLED,
        LifecycleState.TERMINATED,
    },
    LifecycleState.COMPLETED: set(),
    LifecycleState.FAILED: set(),
    LifecycleState.CANCELLED: set(),
    LifecycleState.TERMINATED: set(),
}


class InMemoryExecutionLifecycleRepository(IExecutionLifecycleRepository):
    """Thread-safe, persistence-agnostic in-memory storage for execution lifecycle records."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._records: Dict[str, ExecutionLifecycleRecord] = {}

    def save(self, record: ExecutionLifecycleRecord) -> ExecutionLifecycleRecord:
        """Persist or update an execution lifecycle record."""
        with self._lock:
            eid = record.execution_id.strip()
            self._records[eid] = record.model_copy(deep=True)
            return record.model_copy(deep=True)

    def get(self, execution_id: str) -> Optional[ExecutionLifecycleRecord]:
        """Retrieve an execution lifecycle record by execution_id."""
        with self._lock:
            eid = execution_id.strip()
            rec = self._records.get(eid)
            return rec.model_copy(deep=True) if rec else None

    def exists(self, execution_id: str) -> bool:
        """Check if an execution record exists."""
        with self._lock:
            return execution_id.strip() in self._records

    def list_executions(
        self,
        state: Optional[LifecycleState] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ExecutionLifecycleRecord]:
        """List execution records with optional filtering and pagination."""
        with self._lock:
            results = [
                rec.model_copy(deep=True)
                for rec in self._records.values()
                if state is None or rec.state == state
            ]
            # Deterministic sorting by created_at descending, then execution_id
            results.sort(key=lambda r: (r.created_at, r.execution_id), reverse=True)
            return results[offset : offset + limit]

    def update_state(
        self,
        execution_id: str,
        new_state: LifecycleState,
        reason: Optional[str] = None
    ) -> ExecutionLifecycleRecord:
        """Validate and apply a lifecycle state transition."""
        with self._lock:
            eid = execution_id.strip()
            rec = self._records.get(eid)
            if not rec:
                raise ExecutionNotFoundError(eid)

            curr_state = rec.state if isinstance(rec.state, LifecycleState) else LifecycleState(rec.state)
            target_state = new_state if isinstance(new_state, LifecycleState) else LifecycleState(new_state)

            if curr_state != target_state:
                allowed = VALID_TRANSITIONS.get(curr_state, set())
                if target_state not in allowed:
                    raise InvalidStateTransitionError(
                        execution_id=eid,
                        from_state=curr_state.value if hasattr(curr_state, "value") else str(curr_state),
                        to_state=target_state.value if hasattr(target_state, "value") else str(target_state)
                    )

                # Record transition
                transition = LifecycleTransition(
                    execution_id=eid,
                    from_state=curr_state,
                    to_state=target_state,
                    timestamp=_utc_now_iso(),
                    reason=reason
                )
                rec.transitions.append(transition)
                rec.state = target_state

                # Update timestamp markers
                if target_state == LifecycleState.RUNNING and not rec.started_at:
                    rec.started_at = transition.timestamp
                elif target_state in (LifecycleState.COMPLETED, LifecycleState.FAILED, LifecycleState.CANCELLED, LifecycleState.TERMINATED):
                    rec.completed_at = transition.timestamp

            self._records[eid] = rec
            return rec.model_copy(deep=True)
