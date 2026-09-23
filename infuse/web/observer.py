"""Thread-safe, Deterministic In-Memory Web Activity Observer for Block 19."""

import threading
from typing import Dict, List, Optional, Set

from infuse.contracts.common import utc_now
from infuse.contracts.events import EventType, ExecutionEvent
from infuse.events.interfaces import IEventBus
from infuse.web.interfaces import IWebActivityObserver
from infuse.web.models import (
    ExecutionWebSummary,
    WebActivityRecord,
    WebActivityStatus,
    WebObservationCompleteness,
)


class WebActivityObserver(IWebActivityObserver):
    """Passive observation and deterministic aggregation engine for web activity.

    Consumes canonical WebRequest and WebResponse events to correlate web operations,
    capture URLs, HTTP methods, status codes, payload sizes, durations, and success/failure facts,
    producing normalized summaries without making network requests, executing crawls,
    enforcing policies, or modifying lifecycle state.
    """

    WEB_EVENT_TYPES = [
        EventType.WEB_REQUEST,
        EventType.WEB_RESPONSE,
    ]

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._summaries: Dict[str, ExecutionWebSummary] = {}
        self._activities: Dict[str, Dict[str, WebActivityRecord]] = {}
        self._seen_event_ids: Dict[str, Set[str]] = {}
        self._subscription_ids: List[str] = []

    def _get_or_create_summary(self, execution_id: str) -> ExecutionWebSummary:
        if execution_id not in self._summaries:
            self._summaries[execution_id] = ExecutionWebSummary(
                execution_id=execution_id,
                completeness=WebObservationCompleteness.UNKNOWN
            )
            self._activities[execution_id] = {}
            self._seen_event_ids[execution_id] = set()
        return self._summaries[execution_id]

    def _recalculate_summary(self, execution_id: str) -> ExecutionWebSummary:
        summary = self._summaries[execution_id]
        act_map = self._activities[execution_id]

        activities = list(act_map.values())
        total_requests = len(activities)
        completed_requests = sum(
            1 for a in activities if a.status in (WebActivityStatus.COMPLETED, WebActivityStatus.FAILED)
        )
        successful_requests = sum(1 for a in activities if a.success is True)
        failed_requests = sum(
            1 for a in activities if a.status == WebActivityStatus.FAILED or a.success is False
        )
        incomplete_requests = sum(1 for a in activities if a.status == WebActivityStatus.REQUESTED)

        unique_targets = sorted(list({a.url for a in activities if a.url}))

        durations = [a.duration_ms for a in activities if a.duration_ms is not None and a.duration_ms >= 0]
        total_duration = sum(durations)
        avg_duration = (total_duration / len(durations)) if durations else None

        bytes_list = [a.bytes_transferred for a in activities if a.bytes_transferred is not None and a.bytes_transferred >= 0]
        total_bytes = sum(bytes_list)

        if total_requests > 0 and incomplete_requests == 0:
            completeness = WebObservationCompleteness.COMPLETE
        elif total_requests > 0:
            completeness = WebObservationCompleteness.PARTIAL
        else:
            completeness = WebObservationCompleteness.UNKNOWN

        summary.total_requests = total_requests
        summary.completed_requests = completed_requests
        summary.successful_requests = successful_requests
        summary.failed_requests = failed_requests
        summary.incomplete_requests = incomplete_requests
        summary.unique_targets = unique_targets
        summary.total_duration_ms = total_duration
        summary.avg_duration_ms = avg_duration
        summary.total_bytes_transferred = total_bytes
        summary.activities = activities
        summary.completeness = completeness

        return summary

    def handle_event(self, event: ExecutionEvent) -> Optional[ExecutionWebSummary]:
        """Process a canonical web event and update web observation state deterministically."""
        if not event or not event.execution_id:
            return None

        if event.type not in self.WEB_EVENT_TYPES:
            return None

        with self._lock:
            summary = self._get_or_create_summary(event.execution_id)
            seen_ids = self._seen_event_ids[event.execution_id]

            # Idempotency check: do not double-count duplicate events
            if event.event_id in seen_ids:
                return summary.model_copy(deep=True)
            seen_ids.add(event.event_id)

            summary.events_count += 1
            if event.sequence > summary.last_sequence:
                summary.last_sequence = event.sequence

            payload = event.payload or {}
            event_type = event.type
            now = event.timestamp or utc_now()

            url = payload.get("url") or "unknown_target"
            method = payload.get("method") or "GET"
            request_id = payload.get("request_id") or payload.get("correlation_id")
            status_code = payload.get("status_code")
            bytes_transferred = payload.get("bytes_transferred")
            duration_ms = payload.get("duration_ms")
            success = payload.get("success")
            error = payload.get("error")

            act_map = self._activities[event.execution_id]

            if event_type == EventType.WEB_REQUEST:
                key = request_id or f"anon_req_{event.event_id}"
                if key in act_map:
                    # Out-of-order scenario: WebResponse arrived before WebRequest
                    rec = act_map[key]
                    if rec.requested_at is None:
                        rec.requested_at = now
                    if rec.request_event_id is None:
                        rec.request_event_id = event.event_id
                    if rec.url == "unknown_target" and url != "unknown_target":
                        rec.url = url
                    if rec.method == "GET" and method != "GET":
                        rec.method = method
                    # Calculate duration if unobserved and valid timestamps present
                    if rec.duration_ms is None and rec.responded_at and rec.requested_at:
                        diff = (rec.responded_at - rec.requested_at).total_seconds() * 1000.0
                        if diff >= 0:
                            rec.duration_ms = diff
                else:
                    rec = WebActivityRecord(
                        request_id=request_id,
                        execution_id=event.execution_id,
                        url=url,
                        method=method,
                        status=WebActivityStatus.REQUESTED,
                        status_code=None,
                        bytes_transferred=None,
                        success=None,
                        error=None,
                        duration_ms=None,
                        requested_at=now,
                        responded_at=None,
                        request_event_id=event.event_id,
                        response_event_id=None,
                        sequence=event.sequence
                    )
                    act_map[key] = rec

            elif event_type == EventType.WEB_RESPONSE:
                if request_id and request_id in act_map:
                    rec = act_map[request_id]
                elif request_id:
                    # Out-of-order: WebResponse arrived before WebRequest
                    rec = WebActivityRecord(
                        request_id=request_id,
                        execution_id=event.execution_id,
                        url=url,
                        method=method,
                        status=WebActivityStatus.COMPLETED,
                        sequence=event.sequence
                    )
                    act_map[request_id] = rec
                else:
                    # Fallback correlation: search for open request with matching URL
                    open_matches = [
                        r for r in act_map.values()
                        if r.status == WebActivityStatus.REQUESTED and (r.url == url or url == "unknown_target")
                    ]
                    if open_matches:
                        rec = open_matches[0]
                    else:
                        key = f"anon_resp_{event.event_id}"
                        rec = WebActivityRecord(
                            request_id=None,
                            execution_id=event.execution_id,
                            url=url,
                            method=method,
                            status=WebActivityStatus.COMPLETED,
                            sequence=event.sequence
                        )
                        act_map[key] = rec

                rec.response_event_id = event.event_id
                rec.responded_at = now
                if url != "unknown_target":
                    rec.url = url
                if method != "GET":
                    rec.method = method

                if status_code is not None:
                    try:
                        rec.status_code = int(status_code)
                    except (ValueError, TypeError):
                        rec.status_code = None

                if bytes_transferred is not None:
                    try:
                        b_val = int(bytes_transferred)
                        rec.bytes_transferred = b_val if b_val >= 0 else None
                    except (ValueError, TypeError):
                        rec.bytes_transferred = None

                # Determine success / failure outcome
                if error is not None:
                    rec.status = WebActivityStatus.FAILED
                    rec.success = False
                    rec.error = error
                elif success is not None:
                    rec.success = bool(success)
                    rec.status = WebActivityStatus.COMPLETED if rec.success else WebActivityStatus.FAILED
                elif rec.status_code is not None:
                    if 200 <= rec.status_code < 400:
                        rec.status = WebActivityStatus.COMPLETED
                        rec.success = True
                    else:
                        rec.status = WebActivityStatus.FAILED
                        rec.success = False
                        rec.error = f"HTTP status error: {rec.status_code}"
                else:
                    rec.status = WebActivityStatus.COMPLETED
                    rec.success = True

                # Determine duration
                if duration_ms is not None:
                    try:
                        d_val = float(duration_ms)
                        rec.duration_ms = d_val if d_val >= 0 else None
                    except (ValueError, TypeError):
                        rec.duration_ms = None
                elif rec.requested_at and rec.responded_at:
                    diff = (rec.responded_at - rec.requested_at).total_seconds() * 1000.0
                    rec.duration_ms = diff if diff >= 0 else None

            self._recalculate_summary(event.execution_id)
            return summary.model_copy(deep=True)

    def get_execution_summary(self, execution_id: str) -> Optional[ExecutionWebSummary]:
        """Retrieve aggregated web activity summary for a specific execution."""
        if not execution_id:
            return None
        with self._lock:
            summary = self._summaries.get(execution_id.strip())
            return summary.model_copy(deep=True) if summary else None

    def list_execution_summaries(self) -> List[ExecutionWebSummary]:
        """List all active execution web summaries."""
        with self._lock:
            return [s.model_copy(deep=True) for s in self._summaries.values()]

    def get_activity(self, execution_id: str, request_id: str) -> Optional[WebActivityRecord]:
        """Retrieve a specific web activity record by execution_id and request_id."""
        if not execution_id or not request_id:
            return None
        with self._lock:
            act_map = self._activities.get(execution_id.strip(), {})
            rec = act_map.get(request_id.strip())
            return rec.model_copy(deep=True) if rec else None

    def attach_to_bus(self, bus: IEventBus) -> List[str]:
        """Subscribe to WebRequest and WebResponse events on the Event Bus."""
        with self._lock:
            sub_ids = []
            for ev_type in self.WEB_EVENT_TYPES:
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
        """Clear all in-memory web observations and summaries."""
        with self._lock:
            self._summaries.clear()
            self._activities.clear()
            self._seen_event_ids.clear()
            self._subscription_ids.clear()
