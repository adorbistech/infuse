"""Thread-safe, Deterministic Governor Engine for Block 21."""

import threading
from typing import Dict, List, Optional

from infuse.contracts.common import utc_now
from infuse.contracts.events import EventSource, EventType, ExecutionEvent
from infuse.contracts.governor import GovernorAction, GovernorDecision, GovernorDecisionRecord
from infuse.contracts.policy import GovernancePolicy, PolicyActionBindings
from infuse.contracts.state import ExecutionState, ExecutionStateSnapshot
from infuse.events.interfaces import IEventBus
from infuse.governor.interfaces import IGovernorEngine


class GovernorEngine(IGovernorEngine):
    """Deterministic control decision authority.

    Consumes Effective Policy (Block 06) and Canonical Execution State (Block 20)
    to produce explainable, auditable Governor decisions without executing control actions,
    routing providers, performing retries, or mutating lifecycle states.
    """

    def __init__(self, event_bus: Optional[IEventBus] = None) -> None:
        self._lock = threading.RLock()
        self._bus = event_bus
        self._latest_decisions: Dict[str, GovernorDecisionRecord] = {}
        self._history: Dict[str, List[GovernorDecisionRecord]] = {}
        self._eval_counts: Dict[str, int] = {}

    def evaluate(
        self,
        execution_id: str,
        state_snapshot: ExecutionStateSnapshot,
        policy: Optional[GovernancePolicy] = None,
        additional_signals: Optional[dict] = None
    ) -> GovernorDecisionRecord:
        """Evaluate policy against execution state snapshot to produce an immutable GovernorDecisionRecord."""
        if not execution_id:
            raise ValueError("execution_id must not be empty.")
        if state_snapshot is None:
            raise ValueError("state_snapshot must not be None.")

        exec_id = execution_id.strip()
        now = utc_now()
        signals = {**state_snapshot.signals, **(additional_signals or {})}

        with self._lock:
            eval_seq = self._eval_counts.get(exec_id, 0) + 1
            self._eval_counts[exec_id] = eval_seq

            # 1. Resolve Effective Actions Envelope
            effective_policy = policy
            policy_actions = effective_policy.actions if effective_policy and effective_policy.actions else PolicyActionBindings()
            policy_id = effective_policy.policy_id if effective_policy else None
            policy_version = effective_policy.version if effective_policy else "default"

            # 2. Deterministic Action Evaluation
            state = state_snapshot.current_state
            reasons = list(state_snapshot.reason_codes)

            if state == ExecutionState.NORMAL:
                action = GovernorAction.CONTINUE
                triggering_field = None
                if not reasons:
                    reasons = ["NORMAL_EXECUTION"]
                message = "Execution is operating within normal policy boundaries."

            elif state == ExecutionState.COST_PRESSURE:
                if any(r.startswith("TOKEN") for r in reasons):
                    action = policy_actions.token_action
                    triggering_field = "actions.token_action"
                else:
                    action = policy_actions.budget_action
                    triggering_field = "actions.budget_action"
                action = GovernorAction(action) if not isinstance(action, GovernorAction) else action
                action_val = action.value if hasattr(action, "value") else str(action)
                message = f"Cost pressure observed. Applying bound policy action '{action_val}'."

            elif state == ExecutionState.RUNAWAY:
                if "EXECUTION_TIME_EXCEEDED" in reasons:
                    action = policy_actions.runtime_action
                    triggering_field = "actions.runtime_action"
                elif "MAX_REQUESTS_EXCEEDED" in reasons or "MAX_WEB_REQUESTS_EXCEEDED" in reasons:
                    action = policy_actions.request_action
                    triggering_field = "actions.request_action"
                else:
                    action = policy_actions.anomaly_action
                    triggering_field = "actions.anomaly_action"
                action = GovernorAction(action) if not isinstance(action, GovernorAction) else action
                action_val = action.value if hasattr(action, "value") else str(action)
                message = f"Runaway or anomaly condition observed. Applying bound policy action '{action_val}'."

            elif state == ExecutionState.PROVIDER_CONSTRAINED:
                action = policy_actions.provider_failure_action
                triggering_field = "actions.provider_failure_action"
                action = GovernorAction(action) if not isinstance(action, GovernorAction) else action
                action_val = action.value if hasattr(action, "value") else str(action)
                message = f"Provider constraint observed. Applying bound policy action '{action_val}'."

            elif state == ExecutionState.QUALITY_DEGRADED:
                action = policy_actions.provider_failure_action
                triggering_field = "actions.provider_failure_action"
                action = GovernorAction(action) if not isinstance(action, GovernorAction) else action
                action_val = action.value if hasattr(action, "value") else str(action)
                message = f"Quality degradation observed. Applying bound policy action '{action_val}'."

            else:
                action = GovernorAction.CONTINUE
                triggering_field = None
                reasons.append("UNKNOWN_STATE_CONTINUE_FALLBACK")
                message = "Unrecognized execution state. Continuing cautiously."

            decision_id = f"gov_dec_{exec_id}_{eval_seq}_{int(now.timestamp()*1000)}"

            audit_metadata = {
                "evaluation_sequence": eval_seq,
                "triggering_state": str(state.value if hasattr(state, "value") else state),
                "triggering_policy_field": triggering_field,
                "policy_version": policy_version,
                "has_explicit_policy": effective_policy is not None,
                "additional_signals_count": len(additional_signals or {}),
            }

            decision_record = GovernorDecisionRecord(
                decision_id=decision_id,
                execution_id=exec_id,
                action=action,
                reason_codes=reasons,
                message=message,
                evaluated_at=now,
                evaluated_state=str(state.value if hasattr(state, "value") else state),
                signals=signals,
                effective_policy_id=policy_id,
                metadata=audit_metadata
            )

            # Record caching and history
            self._latest_decisions[exec_id] = decision_record
            if exec_id not in self._history:
                self._history[exec_id] = [decision_record.model_copy(deep=True)]
            else:
                self._history[exec_id].append(decision_record.model_copy(deep=True))

            # Event publication
            if self._bus is not None:
                try:
                    payload_decision = GovernorDecision(
                        action=action,
                        reason_codes=reasons,
                        message=message,
                        metadata=audit_metadata
                    )
                    ev = ExecutionEvent(
                        event_id=f"gov_ev_{decision_id}",
                        execution_id=exec_id,
                        type=EventType.GOVERNOR_DECISION,
                        source=EventSource.GOVERNOR,
                        sequence=eval_seq,
                        timestamp=now,
                        payload=payload_decision.model_dump()
                    )
                    self._bus.publish(ev)
                except Exception:
                    pass

            return decision_record.model_copy(deep=True)

    def get_latest_decision(self, execution_id: str) -> Optional[GovernorDecisionRecord]:
        """Retrieve the latest decision record for an execution."""
        if not execution_id:
            return None
        with self._lock:
            rec = self._latest_decisions.get(execution_id.strip())
            return rec.model_copy(deep=True) if rec else None

    def get_decision_history(self, execution_id: str) -> List[GovernorDecisionRecord]:
        """Retrieve the complete chronological decision history for an execution."""
        if not execution_id:
            return []
        with self._lock:
            hist = self._history.get(execution_id.strip(), [])
            return [d.model_copy(deep=True) for d in hist]

    def list_decisions(self) -> List[GovernorDecisionRecord]:
        """List the latest decision records across all active executions."""
        with self._lock:
            return [d.model_copy(deep=True) for d in self._latest_decisions.values()]

    def attach_to_bus(self, bus: IEventBus) -> None:
        """Attach to event bus for publishing GovernorDecision events."""
        with self._lock:
            self._bus = bus

    def clear(self) -> None:
        """Clear all in-memory decision records and histories."""
        with self._lock:
            self._latest_decisions.clear()
            self._history.clear()
            self._eval_counts.clear()
