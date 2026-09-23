"""Deterministic In-Memory Token Observer Implementation for Block 15."""

import threading
from typing import Dict, List, Optional, Set

from infuse.contracts.events import EventType, ExecutionEvent
from infuse.events.interfaces import IEventBus
from infuse.observer.errors import TokenObservationError
from infuse.observer.interfaces import ITokenObserver
from infuse.observer.models import (
    ExecutionTokenSummary,
    TokenObservationRecord,
    TokenObservationSource,
)


class TokenObserver(ITokenObserver):
    """Deterministic, thread-safe observer for execution-level token usage facts.

    Listens to canonical execution events and maintains normalized token summaries
    without performing pricing, routing, governance, or lifecycle mutation.
    """

    RELEVANT_EVENT_TYPES = [
        EventType.EXECUTION_STARTED,
        EventType.TOKEN_OBSERVED,
        EventType.USAGE_UPDATED,
        EventType.EXECUTION_COMPLETED,
        EventType.EXECUTION_FAILED,
    ]

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._summaries: Dict[str, ExecutionTokenSummary] = {}
        self._seen_events: Dict[str, Set[str]] = {}
        self._bus_subscriptions: Dict[IEventBus, List[str]] = {}

    def handle_event(self, event: ExecutionEvent) -> None:
        """Process an incoming execution event and update token summary."""
        if not event or not event.execution_id or not event.execution_id.strip():
            return

        eid = event.execution_id.strip()
        ev_id = event.event_id.strip()

        with self._lock:
            # 1. Deduplication / Idempotency Check
            if eid not in self._seen_events:
                self._seen_events[eid] = set()

            if ev_id in self._seen_events[eid]:
                # Duplicate identical event received - idempotent ignore
                return
            self._seen_events[eid].add(ev_id)

            # 2. Get or initialize summary record
            if eid not in self._summaries:
                self._summaries[eid] = ExecutionTokenSummary(
                    execution_id=eid,
                    first_observed_at=event.timestamp,
                    last_observed_at=event.timestamp
                )

            summary = self._summaries[eid]
            summary.events_count += 1
            summary.last_sequence = max(summary.last_sequence, event.sequence)
            summary.last_observed_at = event.timestamp
            if not summary.first_observed_at:
                summary.first_observed_at = event.timestamp

            payload = event.payload if isinstance(event.payload, dict) else {}

            # 3. Route event to specialized normalization
            if event.type == EventType.EXECUTION_STARTED:
                self._process_execution_started(summary, event, payload)
            elif event.type == EventType.TOKEN_OBSERVED:
                self._process_token_observed(summary, event, payload)
            elif event.type == EventType.USAGE_UPDATED:
                self._process_usage_updated(summary, event, payload)
            elif event.type == EventType.EXECUTION_COMPLETED:
                self._process_execution_completed(summary, event, payload)
            elif event.type == EventType.EXECUTION_FAILED:
                self._process_execution_failed(summary, event, payload)

    def _process_execution_started(
        self,
        summary: ExecutionTokenSummary,
        event: ExecutionEvent,
        payload: Dict
    ) -> None:
        """Record initial target metadata from execution start."""
        if not summary.provider_id and payload.get("provider_id"):
            summary.provider_id = payload["provider_id"]
        if not summary.model_id and payload.get("model_id"):
            summary.model_id = payload["model_id"]

    def _process_token_observed(
        self,
        summary: ExecutionTokenSummary,
        event: ExecutionEvent,
        payload: Dict
    ) -> None:
        """Process explicit TokenObserved event (streaming estimate or provider usage)."""
        inp = payload.get("input_tokens")
        out = payload.get("output_tokens")
        cached = payload.get("cached_tokens")
        total = payload.get("total_tokens")
        is_auth = payload.get("is_authoritative", False)
        provider = payload.get("provider") or payload.get("provider_id")
        model = payload.get("model") or payload.get("model_id")

        # Derive total if components exist but total is absent or 0
        derived_total = total
        if (derived_total is None or derived_total == 0) and (inp is not None or out is not None):
            derived_total = (inp or 0) + (out or 0)

        source = (
            TokenObservationSource.PROVIDER_USAGE
            if is_auth
            else TokenObservationSource.STREAM_ESTIMATE
        )

        record = TokenObservationRecord(
            event_id=event.event_id,
            sequence=event.sequence,
            timestamp=event.timestamp,
            event_type=event.type,
            input_tokens=inp,
            output_tokens=out,
            cached_tokens=cached,
            total_tokens=derived_total,
            is_authoritative=is_auth,
            source=source,
            provider_id=provider or summary.provider_id,
            model_id=model or summary.model_id,
            metadata=payload.get("metadata", {})
        )
        summary.history.append(record)

        # Update summary if new event is authoritative or summary is not yet authoritative
        # (Preserve authoritative summary over non-authoritative stream estimates)
        should_update = is_auth or not summary.is_authoritative or event.sequence >= summary.last_sequence
        if should_update:
            if inp is not None:
                summary.input_tokens = inp
            if out is not None:
                summary.output_tokens = out
            if cached is not None:
                summary.cached_tokens = cached
            if derived_total is not None:
                summary.total_tokens = derived_total

            if is_auth:
                summary.is_authoritative = True
                summary.source = TokenObservationSource.PROVIDER_USAGE
            elif not summary.is_authoritative:
                summary.is_authoritative = False
                summary.source = TokenObservationSource.STREAM_ESTIMATE

            if provider:
                summary.provider_id = provider
            if model:
                summary.model_id = model

    def _process_usage_updated(
        self,
        summary: ExecutionTokenSummary,
        event: ExecutionEvent,
        payload: Dict
    ) -> None:
        """Process aggregate UsageUpdated event."""
        inp = payload.get("input_tokens")
        out = payload.get("output_tokens")
        cached = payload.get("cached_tokens")
        total = payload.get("total_tokens")
        is_auth = payload.get("is_authoritative", True)
        provider = payload.get("provider") or payload.get("provider_id")
        model = payload.get("model") or payload.get("model_id")

        derived_total = total
        if (derived_total is None or derived_total == 0) and (inp is not None or out is not None):
            derived_total = (inp or 0) + (out or 0)

        record = TokenObservationRecord(
            event_id=event.event_id,
            sequence=event.sequence,
            timestamp=event.timestamp,
            event_type=event.type,
            input_tokens=inp,
            output_tokens=out,
            cached_tokens=cached,
            total_tokens=derived_total,
            is_authoritative=is_auth,
            source=TokenObservationSource.LIFECYCLE_EVENT,
            provider_id=provider or summary.provider_id,
            model_id=model or summary.model_id,
            metadata=payload.get("metadata", {})
        )
        summary.history.append(record)

        if inp is not None:
            summary.input_tokens = inp
        if out is not None:
            summary.output_tokens = out
        if cached is not None:
            summary.cached_tokens = cached
        if derived_total is not None:
            summary.total_tokens = derived_total
        if is_auth:
            summary.is_authoritative = True
            summary.source = TokenObservationSource.LIFECYCLE_EVENT
        if provider:
            summary.provider_id = provider
        if model:
            summary.model_id = model

    def _process_execution_completed(
        self,
        summary: ExecutionTokenSummary,
        event: ExecutionEvent,
        payload: Dict
    ) -> None:
        """Finalize observation with ExecutionCompleted data."""
        inp = payload.get("input_tokens")
        out = payload.get("output_tokens")
        cached = payload.get("cached_tokens")
        total = payload.get("total_tokens")
        provider = payload.get("provider_id") or payload.get("provider")
        model = payload.get("model_id") or payload.get("model")

        derived_total = total
        if (derived_total is None or derived_total == 0) and (inp is not None or out is not None):
            derived_total = (inp or 0) + (out or 0)

        record = TokenObservationRecord(
            event_id=event.event_id,
            sequence=event.sequence,
            timestamp=event.timestamp,
            event_type=event.type,
            input_tokens=inp,
            output_tokens=out,
            cached_tokens=cached,
            total_tokens=derived_total,
            is_authoritative=True,
            source=TokenObservationSource.LIFECYCLE_EVENT,
            provider_id=provider or summary.provider_id,
            model_id=model or summary.model_id,
            metadata=payload.get("metadata", {})
        )
        summary.history.append(record)

        summary.is_finalized = True
        summary.final_status = payload.get("status", "COMPLETED")
        summary.is_authoritative = True
        summary.source = TokenObservationSource.LIFECYCLE_EVENT

        if inp is not None:
            summary.input_tokens = inp
        if out is not None:
            summary.output_tokens = out
        if cached is not None:
            summary.cached_tokens = cached
        if derived_total is not None:
            summary.total_tokens = derived_total
        if provider:
            summary.provider_id = provider
        if model:
            summary.model_id = model

    def _process_execution_failed(
        self,
        summary: ExecutionTokenSummary,
        event: ExecutionEvent,
        payload: Dict
    ) -> None:
        """Finalize observation with ExecutionFailed status without fabricating missing tokens."""
        provider = payload.get("provider_id") or payload.get("provider")
        model = payload.get("model_id") or payload.get("model")

        record = TokenObservationRecord(
            event_id=event.event_id,
            sequence=event.sequence,
            timestamp=event.timestamp,
            event_type=event.type,
            input_tokens=summary.input_tokens,
            output_tokens=summary.output_tokens,
            cached_tokens=summary.cached_tokens,
            total_tokens=summary.total_tokens,
            is_authoritative=summary.is_authoritative,
            source=summary.source,
            provider_id=provider or summary.provider_id,
            model_id=model or summary.model_id,
            metadata=payload.get("metadata", {})
        )
        summary.history.append(record)

        summary.is_finalized = True
        summary.final_status = payload.get("status", "FAILED")
        if provider and not summary.provider_id:
            summary.provider_id = provider
        if model and not summary.model_id:
            summary.model_id = model

    def get_observation(self, execution_id: str) -> Optional[ExecutionTokenSummary]:
        """Retrieve a deep copy of the normalized token observation summary for execution ID."""
        if not execution_id:
            return None
        with self._lock:
            rec = self._summaries.get(execution_id.strip())
            return rec.model_copy(deep=True) if rec else None

    def list_observations(self) -> List[ExecutionTokenSummary]:
        """List deep copies of all normalized execution token summaries."""
        with self._lock:
            return [s.model_copy(deep=True) for s in self._summaries.values()]

    def is_finalized(self, execution_id: str) -> bool:
        """Check whether the execution observation has concluded."""
        if not execution_id:
            return False
        with self._lock:
            rec = self._summaries.get(execution_id.strip())
            return rec.is_finalized if rec else False

    def attach_to_bus(self, bus: IEventBus) -> List[str]:
        """Subscribe observer to all relevant token & lifecycle event types on the event bus."""
        if not bus:
            return []
        sub_tokens = []
        with self._lock:
            for ev_type in self.RELEVANT_EVENT_TYPES:
                tok = bus.subscribe(self.handle_event, event_type=ev_type)
                sub_tokens.append(tok)
            self._bus_subscriptions[bus] = sub_tokens
        return sub_tokens

    def detach_from_bus(self, bus: IEventBus) -> None:
        """Unsubscribe observer from the provided Event Bus."""
        if not bus:
            return
        with self._lock:
            tokens = self._bus_subscriptions.pop(bus, [])
            for tok in tokens:
                bus.unsubscribe(tok)

    def clear(self) -> None:
        """Clear all in-memory observation state."""
        with self._lock:
            self._summaries.clear()
            self._seen_events.clear()
