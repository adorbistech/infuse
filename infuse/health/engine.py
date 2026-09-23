"""Thread-safe, Deterministic In-Memory Health Engine for Block 17."""

import threading
from typing import Dict, List, Optional, Set, Tuple

from infuse.contracts.common import utc_now
from infuse.contracts.events import EventType, ExecutionEvent
from infuse.events.interfaces import IEventBus
from infuse.health.classifier import classify_error_category
from infuse.health.interfaces import IHealthEngine
from infuse.health.models import (
    ErrorCategory,
    ExecutionHealthSummary,
    HealthCompleteness,
    ModelHealthAggregate,
    ObservedErrorRecord,
    ObservedRetryRecord,
    ProviderHealthAggregate,
)


class HealthEngine(IHealthEngine):
    """Passive observation and deterministic aggregation engine for execution and provider health.

    Consumes canonical execution events to produce normalized health facts without
    performing active probing, routing, retries, governor actions, or lifecycle mutations.
    """

    HEALTH_EVENT_TYPES = [
        EventType.EXECUTION_STARTED,
        EventType.EXECUTION_COMPLETED,
        EventType.EXECUTION_FAILED,
        EventType.PROVIDER_ERROR,
        EventType.RETRY_STARTED,
        EventType.STATE_CHANGED,
    ]

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._executions: Dict[str, ExecutionHealthSummary] = {}
        self._seen_event_ids: Dict[str, Set[str]] = {}
        self._provider_aggregates: Dict[str, ProviderHealthAggregate] = {}
        self._model_aggregates: Dict[Tuple[str, str], ModelHealthAggregate] = {}
        self._subscription_ids: List[str] = []

    def _get_or_create_execution(self, execution_id: str) -> ExecutionHealthSummary:
        if execution_id not in self._executions:
            self._executions[execution_id] = ExecutionHealthSummary(
                execution_id=execution_id,
                completeness=HealthCompleteness.UNKNOWN
            )
            self._seen_event_ids[execution_id] = set()
        return self._executions[execution_id]

    def _get_or_create_provider_aggregate(self, provider_id: str) -> ProviderHealthAggregate:
        key = provider_id.strip().lower()
        if key not in self._provider_aggregates:
            self._provider_aggregates[key] = ProviderHealthAggregate(provider_id=key)
        return self._provider_aggregates[key]

    def _get_or_create_model_aggregate(self, provider_id: str, model_id: str) -> ModelHealthAggregate:
        pkey = provider_id.strip().lower()
        mkey = model_id.strip().lower()
        key = (pkey, mkey)
        if key not in self._model_aggregates:
            self._model_aggregates[key] = ModelHealthAggregate(provider_id=pkey, model_id=mkey)
        return self._model_aggregates[key]

    def _update_latency_stats(
        self,
        agg: ProviderHealthAggregate | ModelHealthAggregate,
        latency_ms: float
    ) -> None:
        agg.total_latency_ms += latency_ms
        if agg.min_latency_ms is None or latency_ms < agg.min_latency_ms:
            agg.min_latency_ms = latency_ms
        if agg.max_latency_ms is None or latency_ms > agg.max_latency_ms:
            agg.max_latency_ms = latency_ms
        if agg.successful_executions + agg.failed_executions > 0:
            agg.avg_latency_ms = agg.total_latency_ms / (agg.successful_executions + agg.failed_executions)

    def handle_event(self, event: ExecutionEvent) -> Optional[ExecutionHealthSummary]:
        """Process a canonical execution event and update health state deterministically."""
        if not event or not event.execution_id:
            return None

        with self._lock:
            summary = self._get_or_create_execution(event.execution_id)
            seen_ids = self._seen_event_ids[event.execution_id]

            # Idempotency check: do not double-count replayed events
            if event.event_id in seen_ids:
                return summary.model_copy(deep=True)
            seen_ids.add(event.event_id)

            summary.events_count += 1
            if event.sequence > summary.last_sequence:
                summary.last_sequence = event.sequence

            payload = event.payload or {}
            event_type = event.type
            now = event.timestamp or utc_now()

            provider_id = payload.get("provider_id") or payload.get("provider")
            if provider_id and not summary.provider_id:
                summary.provider_id = provider_id

            model_id = payload.get("model_id") or payload.get("model")
            if model_id and not summary.model_id:
                summary.model_id = model_id

            if event_type == EventType.EXECUTION_STARTED:
                if not summary.is_finalized:
                    summary.status = "STARTED"
                if summary.started_at is None:
                    summary.started_at = now
                if summary.provider_id and summary.completeness == HealthCompleteness.UNKNOWN:
                    summary.completeness = HealthCompleteness.PARTIAL

            elif event_type == EventType.EXECUTION_COMPLETED:
                summary.status = "COMPLETED"
                summary.is_success = True
                summary.is_finalized = True
                summary.completed_at = now

                duration_ms = payload.get("duration_ms")
                if duration_ms is not None:
                    summary.latency_ms = float(duration_ms)

                if summary.latency_ms is not None and summary.provider_id:
                    summary.completeness = HealthCompleteness.COMPLETE
                elif summary.provider_id:
                    summary.completeness = HealthCompleteness.PARTIAL

                # Update aggregates
                if summary.provider_id:
                    p_agg = self._get_or_create_provider_aggregate(summary.provider_id)
                    p_agg.total_executions += 1
                    p_agg.successful_executions += 1
                    p_agg.last_observed_at = now
                    if summary.latency_ms is not None:
                        self._update_latency_stats(p_agg, summary.latency_ms)

                    if summary.model_id:
                        m_agg = self._get_or_create_model_aggregate(summary.provider_id, summary.model_id)
                        m_agg.total_executions += 1
                        m_agg.successful_executions += 1
                        m_agg.last_observed_at = now
                        if summary.latency_ms is not None:
                            self._update_latency_stats(m_agg, summary.latency_ms)

            elif event_type == EventType.EXECUTION_FAILED:
                summary.status = "FAILED"
                summary.is_success = False
                summary.is_finalized = True
                summary.completed_at = now

                duration_ms = payload.get("duration_ms")
                if duration_ms is not None:
                    summary.latency_ms = float(duration_ms)

                if summary.latency_ms is not None and summary.provider_id:
                    summary.completeness = HealthCompleteness.COMPLETE
                elif summary.provider_id:
                    summary.completeness = HealthCompleteness.PARTIAL

                # Capture error details from failure event if present
                error_type = payload.get("error_type", "EXECUTION_ERROR")
                error_msg = payload.get("error_message") or payload.get("message", "Execution failed")
                http_status = payload.get("http_status")
                is_retryable = bool(payload.get("is_retryable", False))
                cat = classify_error_category(
                    error_type=error_type,
                    message=error_msg,
                    http_status=http_status
                )

                error_rec = ObservedErrorRecord(
                    event_id=event.event_id,
                    execution_id=event.execution_id,
                    provider_id=summary.provider_id,
                    model_id=summary.model_id,
                    error_category=cat,
                    error_type=error_type,
                    message=error_msg,
                    is_retryable=is_retryable,
                    http_status=http_status,
                    observed_at=now
                )
                summary.errors.append(error_rec)

                # Update aggregates
                if summary.provider_id:
                    p_agg = self._get_or_create_provider_aggregate(summary.provider_id)
                    p_agg.total_executions += 1
                    p_agg.failed_executions += 1
                    p_agg.last_observed_at = now
                    p_agg.error_counts_by_category[cat.value] = p_agg.error_counts_by_category.get(cat.value, 0) + 1
                    if summary.latency_ms is not None:
                        self._update_latency_stats(p_agg, summary.latency_ms)

                    if summary.model_id:
                        m_agg = self._get_or_create_model_aggregate(summary.provider_id, summary.model_id)
                        m_agg.total_executions += 1
                        m_agg.failed_executions += 1
                        m_agg.last_observed_at = now
                        m_agg.error_counts_by_category[cat.value] = m_agg.error_counts_by_category.get(cat.value, 0) + 1
                        if summary.latency_ms is not None:
                            self._update_latency_stats(m_agg, summary.latency_ms)

            elif event_type == EventType.PROVIDER_ERROR:
                err_provider = payload.get("provider") or payload.get("provider_id") or summary.provider_id
                err_model = payload.get("model") or payload.get("model_id") or summary.model_id
                err_type = payload.get("error_type", "PROVIDER_ERROR")
                err_code = payload.get("error_code")
                err_msg = payload.get("message", "")
                is_retryable = bool(payload.get("is_retryable", False))
                http_status = payload.get("http_status")

                cat = classify_error_category(
                    error_type=err_type,
                    error_code=err_code,
                    message=err_msg,
                    http_status=http_status
                )

                error_rec = ObservedErrorRecord(
                    event_id=event.event_id,
                    execution_id=event.execution_id,
                    provider_id=err_provider,
                    model_id=err_model,
                    error_category=cat,
                    error_type=err_type,
                    error_code=err_code,
                    message=err_msg,
                    is_retryable=is_retryable,
                    http_status=http_status,
                    observed_at=now
                )
                summary.errors.append(error_rec)

                # Update aggregates
                if err_provider:
                    p_agg = self._get_or_create_provider_aggregate(err_provider)
                    p_agg.provider_error_count += 1
                    p_agg.error_counts_by_category[cat.value] = p_agg.error_counts_by_category.get(cat.value, 0) + 1
                    p_agg.last_observed_at = now

                    if err_model:
                        m_agg = self._get_or_create_model_aggregate(err_provider, err_model)
                        m_agg.provider_error_count += 1
                        m_agg.error_counts_by_category[cat.value] = m_agg.error_counts_by_category.get(cat.value, 0) + 1
                        m_agg.last_observed_at = now

            elif event_type == EventType.RETRY_STARTED:
                retry_provider = payload.get("provider") or payload.get("provider_id") or summary.provider_id
                retry_model = payload.get("model") or payload.get("model_id") or summary.model_id
                attempt = payload.get("attempt") or payload.get("attempt_number")
                reason = payload.get("reason")

                retry_rec = ObservedRetryRecord(
                    event_id=event.event_id,
                    execution_id=event.execution_id,
                    provider_id=retry_provider,
                    model_id=retry_model,
                    attempt_number=int(attempt) if attempt is not None else None,
                    reason=reason,
                    observed_at=now
                )
                summary.retries.append(retry_rec)

                # Update aggregates
                if retry_provider:
                    p_agg = self._get_or_create_provider_aggregate(retry_provider)
                    p_agg.retry_count += 1
                    p_agg.last_observed_at = now

                    if retry_model:
                        m_agg = self._get_or_create_model_aggregate(retry_provider, retry_model)
                        m_agg.retry_count += 1
                        m_agg.last_observed_at = now

            elif event_type == EventType.STATE_CHANGED:
                new_state = payload.get("new_state")
                if new_state and not summary.is_finalized:
                    summary.status = str(new_state)

            return summary.model_copy(deep=True)

    def get_execution_health(self, execution_id: str) -> Optional[ExecutionHealthSummary]:
        """Retrieve health summary for a specific execution."""
        if not execution_id:
            return None
        with self._lock:
            res = self._executions.get(execution_id.strip())
            return res.model_copy(deep=True) if res else None

    def list_execution_health(self) -> List[ExecutionHealthSummary]:
        """List all active execution health summaries."""
        with self._lock:
            return [s.model_copy(deep=True) for s in self._executions.values()]

    def get_provider_aggregate(self, provider_id: str) -> Optional[ProviderHealthAggregate]:
        """Retrieve aggregate health metrics for a provider."""
        if not provider_id:
            return None
        key = provider_id.strip().lower()
        with self._lock:
            agg = self._provider_aggregates.get(key)
            return agg.model_copy(deep=True) if agg else None

    def list_provider_aggregates(self) -> List[ProviderHealthAggregate]:
        """List aggregate health metrics for all observed providers."""
        with self._lock:
            return [a.model_copy(deep=True) for a in self._provider_aggregates.values()]

    def get_model_aggregate(self, provider_id: str, model_id: str) -> Optional[ModelHealthAggregate]:
        """Retrieve aggregate health metrics for a specific model under a provider."""
        if not provider_id or not model_id:
            return None
        key = (provider_id.strip().lower(), model_id.strip().lower())
        with self._lock:
            agg = self._model_aggregates.get(key)
            return agg.model_copy(deep=True) if agg else None

    def list_model_aggregates(self) -> List[ModelHealthAggregate]:
        """List aggregate health metrics for all observed models."""
        with self._lock:
            return [a.model_copy(deep=True) for a in self._model_aggregates.values()]

    def attach_to_bus(self, bus: IEventBus) -> List[str]:
        """Subscribe to relevant canonical events on the Event Bus."""
        with self._lock:
            sub_ids = []
            for ev_type in self.HEALTH_EVENT_TYPES:
                sid = bus.subscribe(handler=self.handle_event, event_type=ev_type)
                sub_ids.append(sid)
            self._subscription_ids.extend(sub_ids)
            return list(sub_ids)

    def detach_from_bus(self, bus: IEventBus) -> None:
        """Unsubscribe from the Event Bus."""
        with self._lock:
            for sid in self._subscription_ids:
                try:
                    bus.unsubscribe(sid)
                except Exception:
                    pass
            self._subscription_ids.clear()

    def clear(self) -> None:
        """Clear all in-memory health observations and aggregates."""
        with self._lock:
            self._executions.clear()
            self._seen_event_ids.clear()
            self._provider_aggregates.clear()
            self._model_aggregates.clear()
            self._subscription_ids.clear()
