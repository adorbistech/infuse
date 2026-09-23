"""Thread-safe, Deterministic Execution State Engine for Block 20."""

import threading
from typing import Dict, List, Optional
from datetime import datetime

from infuse.contracts.common import utc_now
from infuse.contracts.events import EventSource, EventType, ExecutionEvent, StateChangedPayload
from infuse.contracts.policy import GovernancePolicy
from infuse.contracts.state import ExecutionState, ExecutionStateSnapshot
from infuse.economics.models import ExecutionEconomicSummary
from infuse.events.interfaces import IEventBus
from infuse.health.models import ErrorCategory, ExecutionHealthSummary
from infuse.observer.models import ExecutionTokenSummary
from infuse.state.interfaces import IExecutionStateEngine
from infuse.state.models import (
    ExecutionStateRecord,
    ObservationBundle,
    StateSeverity,
)
from infuse.tools.models import ExecutionToolSummary
from infuse.web.models import ExecutionWebSummary


class ExecutionStateEngine(IExecutionStateEngine):
    """Deterministic state-derivation and transition authority.

    Consumes normalized observations across Token, Economics, Health, Tool, and Web domains,
    evaluating them against active Governance Policy bounds to produce canonical ExecutionStateSnapshots
    without making Governor control decisions, routing, throttling, retrying, or modifying lifecycle state.
    """

    def __init__(self, event_bus: Optional[IEventBus] = None) -> None:
        self._lock = threading.RLock()
        self._bus = event_bus
        self._bundles: Dict[str, ObservationBundle] = {}
        self._records: Dict[str, ExecutionStateRecord] = {}
        self._history: Dict[str, List[ExecutionStateSnapshot]] = {}

    def derive_state(
        self,
        execution_id: str,
        token_summary: Optional[ExecutionTokenSummary] = None,
        economic_summary: Optional[ExecutionEconomicSummary] = None,
        health_summary: Optional[ExecutionHealthSummary] = None,
        tool_summary: Optional[ExecutionToolSummary] = None,
        web_summary: Optional[ExecutionWebSummary] = None,
        policy: Optional[GovernancePolicy] = None,
        context_metadata: Optional[dict] = None
    ) -> ExecutionStateSnapshot:
        """Derive the canonical ExecutionStateSnapshot from observation evidence and active policy."""
        if not execution_id:
            raise ValueError("execution_id must not be empty.")

        with self._lock:
            bundle = ObservationBundle(
                execution_id=execution_id.strip(),
                token_summary=token_summary,
                economic_summary=economic_summary,
                health_summary=health_summary,
                tool_summary=tool_summary,
                web_summary=web_summary,
                policy=policy,
                context_metadata=context_metadata or {},
                updated_at=utc_now()
            )
            return self.update_bundle(bundle)

    def update_bundle(self, bundle: ObservationBundle) -> ExecutionStateSnapshot:
        """Update observations for an execution and recompute the canonical state snapshot."""
        if not bundle or not bundle.execution_id:
            raise ValueError("ObservationBundle must contain a valid execution_id.")

        execution_id = bundle.execution_id.strip()

        with self._lock:
            self._bundles[execution_id] = bundle
            now = utc_now()

            # Collect active signals and candidate states
            signals: Dict[str, object] = {}
            triggered_states: List[tuple[StateSeverity, ExecutionState, str]] = []

            # 1. Evaluate RUNAWAY Evidence
            if bundle.tool_summary and bundle.policy and bundle.policy.tool_controls:
                tc = bundle.policy.tool_controls
                if tc.max_tool_calls_per_task is not None and bundle.tool_summary.total_calls >= tc.max_tool_calls_per_task:
                    triggered_states.append((StateSeverity.RUNAWAY, ExecutionState.RUNAWAY, "MAX_TOOL_CALLS_EXCEEDED"))
                    signals["max_tool_calls_exceeded"] = True
                    signals["tool_calls"] = bundle.tool_summary.total_calls

                if tc.max_consecutive_tool_failures is not None and bundle.tool_summary.failed_calls >= tc.max_consecutive_tool_failures:
                    triggered_states.append((StateSeverity.RUNAWAY, ExecutionState.RUNAWAY, "CONSECUTIVE_TOOL_FAILURES_EXCEEDED"))
                    signals["consecutive_tool_failures_exceeded"] = True

            if bundle.web_summary and bundle.policy and bundle.policy.web_controls:
                wc = bundle.policy.web_controls
                if wc.max_web_requests_per_task is not None and bundle.web_summary.total_requests >= wc.max_web_requests_per_task:
                    triggered_states.append((StateSeverity.RUNAWAY, ExecutionState.RUNAWAY, "MAX_WEB_REQUESTS_EXCEEDED"))
                    signals["max_web_requests_exceeded"] = True
                    signals["web_requests"] = bundle.web_summary.total_requests

            if bundle.health_summary and bundle.policy and bundle.policy.runtime_controls:
                rc = bundle.policy.runtime_controls
                if rc.max_execution_time_seconds is not None and bundle.health_summary.latency_ms is not None:
                    latency_sec = bundle.health_summary.latency_ms / 1000.0
                    if latency_sec >= rc.max_execution_time_seconds:
                        triggered_states.append((StateSeverity.RUNAWAY, ExecutionState.RUNAWAY, "EXECUTION_TIME_EXCEEDED"))
                        signals["execution_time_exceeded"] = True
                        signals["latency_seconds"] = latency_sec

            if bundle.policy and bundle.policy.anomaly_protection:
                ap = bundle.policy.anomaly_protection
                if ap.repetitive_loop_threshold is not None:
                    loop_count = bundle.context_metadata.get("repetitive_loops", 0)
                    if loop_count >= ap.repetitive_loop_threshold:
                        triggered_states.append((StateSeverity.RUNAWAY, ExecutionState.RUNAWAY, "REPETITIVE_LOOP_DETECTED"))
                        signals["repetitive_loop_detected"] = True

            # 2. Evaluate PROVIDER_CONSTRAINED Evidence
            if bundle.health_summary and bundle.health_summary.errors:
                for err in bundle.health_summary.errors:
                    if err.error_category == ErrorCategory.RATE_LIMIT or err.http_status == 429:
                        triggered_states.append((StateSeverity.PROVIDER_CONSTRAINED, ExecutionState.PROVIDER_CONSTRAINED, "PROVIDER_RATE_LIMIT"))
                        signals["provider_rate_limited"] = True
                    elif err.error_category == ErrorCategory.UNAVAILABLE or err.http_status == 503:
                        triggered_states.append((StateSeverity.PROVIDER_CONSTRAINED, ExecutionState.PROVIDER_CONSTRAINED, "PROVIDER_UNAVAILABLE"))
                        signals["provider_unavailable"] = True
                    elif err.error_category == ErrorCategory.AUTHENTICATION or err.http_status in (401, 403):
                        triggered_states.append((StateSeverity.PROVIDER_CONSTRAINED, ExecutionState.PROVIDER_CONSTRAINED, "PROVIDER_AUTH_FAILURE"))
                        signals["provider_auth_failure"] = True
                    elif err.error_category == ErrorCategory.TIMEOUT or err.http_status == 504:
                        triggered_states.append((StateSeverity.PROVIDER_CONSTRAINED, ExecutionState.PROVIDER_CONSTRAINED, "PROVIDER_TIMEOUT"))
                        signals["provider_timeout"] = True
                    elif err.error_category == ErrorCategory.PROVIDER_ERROR:
                        triggered_states.append((StateSeverity.PROVIDER_CONSTRAINED, ExecutionState.PROVIDER_CONSTRAINED, "PROVIDER_ERROR"))
                        signals["provider_error"] = True

            # 3. Evaluate QUALITY_DEGRADED Evidence
            if bundle.health_summary:
                if bundle.health_summary.is_success is False or bundle.health_summary.status == "FAILED":
                    # If not already flagged by provider outage category
                    has_provider_outage = any(st == ExecutionState.PROVIDER_CONSTRAINED for _, st, _ in triggered_states)
                    if not has_provider_outage:
                        triggered_states.append((StateSeverity.QUALITY_DEGRADED, ExecutionState.QUALITY_DEGRADED, "EXECUTION_FAILURE"))
                        signals["execution_failed"] = True

            if bundle.tool_summary:
                if bundle.tool_summary.failed_calls > 0 and bundle.tool_summary.successful_calls == 0 and bundle.tool_summary.total_calls > 0:
                    triggered_states.append((StateSeverity.QUALITY_DEGRADED, ExecutionState.QUALITY_DEGRADED, "ALL_TOOL_CALLS_FAILED"))
                    signals["all_tools_failed"] = True

            if bundle.web_summary:
                if bundle.web_summary.failed_requests > 0 and bundle.web_summary.successful_requests == 0 and bundle.web_summary.total_requests > 0:
                    triggered_states.append((StateSeverity.QUALITY_DEGRADED, ExecutionState.QUALITY_DEGRADED, "ALL_WEB_REQUESTS_FAILED"))
                    signals["all_web_failed"] = True

            # 4. Evaluate COST_PRESSURE Evidence
            if bundle.economic_summary and bundle.policy and bundle.policy.budget_controls:
                bc = bundle.policy.budget_controls
                if bc.max_cost_per_task is not None and bundle.economic_summary.total_cost is not None:
                    cost_val = float(bundle.economic_summary.total_cost)
                    max_cost = float(bc.max_cost_per_task)
                    signals["total_cost"] = cost_val
                    signals["max_cost"] = max_cost
                    if cost_val >= max_cost:
                        triggered_states.append((StateSeverity.COST_PRESSURE, ExecutionState.COST_PRESSURE, "BUDGET_EXCEEDED"))
                        signals["budget_exceeded"] = True
                    elif cost_val >= (0.8 * max_cost):
                        triggered_states.append((StateSeverity.COST_PRESSURE, ExecutionState.COST_PRESSURE, "COST_PRESSURE_HIGH"))
                        signals["cost_pressure_high"] = True

            if bundle.token_summary and bundle.policy and bundle.policy.token_controls:
                tc = bundle.policy.token_controls
                if tc.max_total_tokens is not None and bundle.token_summary.total_tokens is not None:
                    tok_val = bundle.token_summary.total_tokens
                    max_tok = tc.max_total_tokens
                    signals["total_tokens"] = tok_val
                    signals["max_total_tokens"] = max_tok
                    if tok_val >= max_tok:
                        triggered_states.append((StateSeverity.COST_PRESSURE, ExecutionState.COST_PRESSURE, "TOKEN_CEILING_EXCEEDED"))
                        signals["token_ceiling_exceeded"] = True
                    elif tok_val >= int(0.8 * max_tok):
                        triggered_states.append((StateSeverity.COST_PRESSURE, ExecutionState.COST_PRESSURE, "TOKEN_PRESSURE_HIGH"))
                        signals["token_pressure_high"] = True

            # 5. Baseline NORMAL
            if not triggered_states:
                triggered_states.append((StateSeverity.NORMAL, ExecutionState.NORMAL, "NORMAL_EXECUTION"))
                signals["normal"] = True

            # Deterministic Precedence Resolution
            highest = max(triggered_states, key=lambda x: x[0].value)
            canonical_state = highest[1]
            active_reasons = list(dict.fromkeys([code for _, st, code in triggered_states if st == canonical_state]))

            # Retrieve prior record
            prior_record = self._records.get(execution_id)
            if prior_record:
                prev_state = prior_record.snapshot.current_state
                if prev_state != canonical_state:
                    entered_at = now
                    transitions_count = prior_record.transitions_count + 1
                    is_transition = True
                else:
                    entered_at = prior_record.snapshot.entered_at
                    transitions_count = prior_record.transitions_count
                    is_transition = False
                derivation_count = prior_record.derivation_count + 1
            else:
                prev_state = None
                entered_at = now
                transitions_count = 0
                derivation_count = 1
                is_transition = False

            snapshot = ExecutionStateSnapshot(
                execution_id=execution_id,
                current_state=canonical_state,
                previous_state=prev_state,
                entered_at=entered_at,
                reason_codes=active_reasons,
                signals=signals,
                transition_metadata={
                    "derivation_count": derivation_count,
                    "transitions_count": transitions_count,
                    "all_signals_count": len(triggered_states),
                }
            )

            record = ExecutionStateRecord(
                snapshot=snapshot,
                bundle=bundle,
                transitions_count=transitions_count,
                derivation_count=derivation_count
            )
            self._records[execution_id] = record

            # History tracking
            if execution_id not in self._history:
                self._history[execution_id] = [snapshot.model_copy(deep=True)]
            elif is_transition:
                self._history[execution_id].append(snapshot.model_copy(deep=True))

            # Event publication if state changed
            if is_transition and self._bus is not None:
                try:
                    ev = ExecutionEvent(
                        event_id=f"state_chg_{execution_id}_{transitions_count}_{int(now.timestamp()*1000)}",
                        execution_id=execution_id,
                        type=EventType.STATE_CHANGED,
                        source=EventSource.SYSTEM,
                        sequence=derivation_count,
                        timestamp=now,
                        payload=StateChangedPayload(
                            previous_state=prev_state,
                            new_state=canonical_state,
                            reason_codes=active_reasons,
                            signals=signals
                        ).model_dump()
                    )
                    self._bus.publish(ev)
                except Exception:
                    pass

            return snapshot.model_copy(deep=True)

    def get_state(self, execution_id: str) -> Optional[ExecutionStateSnapshot]:
        """Retrieve the latest state snapshot for an execution."""
        if not execution_id:
            return None
        with self._lock:
            rec = self._records.get(execution_id.strip())
            return rec.snapshot.model_copy(deep=True) if rec else None

    def get_history(self, execution_id: str) -> List[ExecutionStateSnapshot]:
        """Retrieve the full transition history snapshots for an execution."""
        if not execution_id:
            return []
        with self._lock:
            hist = self._history.get(execution_id.strip(), [])
            return [s.model_copy(deep=True) for s in hist]

    def list_states(self) -> List[ExecutionStateSnapshot]:
        """List current state snapshots for all active executions."""
        with self._lock:
            return [r.snapshot.model_copy(deep=True) for r in self._records.values()]

    def attach_to_bus(self, bus: IEventBus) -> None:
        """Attach to event bus for state change notifications."""
        with self._lock:
            self._bus = bus

    def clear(self) -> None:
        """Clear all in-memory execution state snapshots and history."""
        with self._lock:
            self._bundles.clear()
            self._records.clear()
            self._history.clear()
