"""Thread-safe, Deterministic In-Memory Tool Activity Observer for Block 18."""

import threading
from typing import Dict, List, Optional, Set

from infuse.contracts.common import utc_now
from infuse.contracts.events import EventType, ExecutionEvent
from infuse.events.interfaces import IEventBus
from infuse.tools.interfaces import IToolActivityObserver
from infuse.tools.models import (
    ExecutionToolSummary,
    ToolInvocationRecord,
    ToolInvocationStatus,
    ToolObservationCompleteness,
)


class ToolActivityObserver(IToolActivityObserver):
    """Passive observation and deterministic aggregation engine for tool activity.

    Consumes canonical ToolCalled and ToolCompleted events to correlate tool invocations,
    capture durations and success/error facts, and produce normalized summaries without
    authorizing, executing, retrying, or modifying any tools.
    """

    TOOL_EVENT_TYPES = [
        EventType.TOOL_CALLED,
        EventType.TOOL_COMPLETED,
    ]

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._summaries: Dict[str, ExecutionToolSummary] = {}
        self._invocations: Dict[str, Dict[str, ToolInvocationRecord]] = {}
        self._seen_event_ids: Dict[str, Set[str]] = {}
        self._subscription_ids: List[str] = []

    def _get_or_create_summary(self, execution_id: str) -> ExecutionToolSummary:
        if execution_id not in self._summaries:
            self._summaries[execution_id] = ExecutionToolSummary(
                execution_id=execution_id,
                completeness=ToolObservationCompleteness.UNKNOWN
            )
            self._invocations[execution_id] = {}
            self._seen_event_ids[execution_id] = set()
        return self._summaries[execution_id]

    def _recalculate_summary(self, execution_id: str) -> ExecutionToolSummary:
        summary = self._summaries[execution_id]
        inv_map = self._invocations[execution_id]

        invocations = list(inv_map.values())
        total_calls = len(invocations)
        completed_calls = sum(1 for inv in invocations if inv.status == ToolInvocationStatus.COMPLETED)
        successful_calls = sum(1 for inv in invocations if inv.success is True)
        failed_calls = sum(1 for inv in invocations if inv.status == ToolInvocationStatus.FAILED or inv.success is False)
        incomplete_calls = sum(1 for inv in invocations if inv.status == ToolInvocationStatus.CALLED)

        unique_tools = sorted(list({inv.tool_name for inv in invocations if inv.tool_name}))

        durations = [inv.duration_ms for inv in invocations if inv.duration_ms is not None and inv.duration_ms >= 0]
        total_duration = sum(durations)
        avg_duration = (total_duration / len(durations)) if durations else None

        if total_calls > 0 and incomplete_calls == 0:
            completeness = ToolObservationCompleteness.COMPLETE
        elif total_calls > 0:
            completeness = ToolObservationCompleteness.PARTIAL
        else:
            completeness = ToolObservationCompleteness.UNKNOWN

        summary.total_calls = total_calls
        summary.completed_calls = completed_calls
        summary.successful_calls = successful_calls
        summary.failed_calls = failed_calls
        summary.incomplete_calls = incomplete_calls
        summary.unique_tools = unique_tools
        summary.total_duration_ms = total_duration
        summary.avg_duration_ms = avg_duration
        summary.invocations = invocations
        summary.completeness = completeness

        return summary

    def handle_event(self, event: ExecutionEvent) -> Optional[ExecutionToolSummary]:
        """Process a canonical tool event and update tool observation state deterministically."""
        if not event or not event.execution_id:
            return None

        if event.type not in self.TOOL_EVENT_TYPES:
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

            tool_name = payload.get("tool_name") or "unknown_tool"
            call_id = payload.get("call_id")
            arguments = payload.get("arguments")
            success = payload.get("success")
            duration_ms = payload.get("duration_ms")
            error = payload.get("error")

            # Determine key for invocation map
            inv_map = self._invocations[event.execution_id]

            if event_type == EventType.TOOL_CALLED:
                key = call_id or f"anon_call_{event.event_id}"
                if key in inv_map:
                    # Out-of-order scenario: ToolCompleted arrived before ToolCalled
                    rec = inv_map[key]
                    if rec.started_at is None:
                        rec.started_at = now
                    if arguments is not None and rec.arguments is None:
                        rec.arguments = arguments
                    if rec.call_event_id is None:
                        rec.call_event_id = event.event_id
                    if rec.tool_name == "unknown_tool" and tool_name != "unknown_tool":
                        rec.tool_name = tool_name
                    # Compute duration if unobserved and timestamps are present
                    if rec.duration_ms is None and rec.completed_at and rec.started_at:
                        diff = (rec.completed_at - rec.started_at).total_seconds() * 1000.0
                        if diff >= 0:
                            rec.duration_ms = diff
                else:
                    rec = ToolInvocationRecord(
                        call_id=call_id,
                        execution_id=event.execution_id,
                        tool_name=tool_name,
                        status=ToolInvocationStatus.CALLED,
                        arguments=arguments,
                        success=None,
                        error=None,
                        duration_ms=None,
                        started_at=now,
                        completed_at=None,
                        call_event_id=event.event_id,
                        completion_event_id=None,
                        sequence=event.sequence
                    )
                    inv_map[key] = rec

            elif event_type == EventType.TOOL_COMPLETED:
                if call_id and call_id in inv_map:
                    rec = inv_map[call_id]
                elif call_id:
                    # Out-of-order: ToolCompleted arrived before ToolCalled
                    rec = ToolInvocationRecord(
                        call_id=call_id,
                        execution_id=event.execution_id,
                        tool_name=tool_name,
                        status=ToolInvocationStatus.COMPLETED,
                        sequence=event.sequence
                    )
                    inv_map[call_id] = rec
                else:
                    # Uncorrelated ToolCompleted without call_id: look for open matching call
                    open_matches = [
                        r for r in inv_map.values()
                        if r.status == ToolInvocationStatus.CALLED and (r.tool_name == tool_name or tool_name == "unknown_tool")
                    ]
                    if open_matches:
                        rec = open_matches[0]
                    else:
                        key = f"anon_comp_{event.event_id}"
                        rec = ToolInvocationRecord(
                            call_id=None,
                            execution_id=event.execution_id,
                            tool_name=tool_name,
                            status=ToolInvocationStatus.COMPLETED,
                            sequence=event.sequence
                        )
                        inv_map[key] = rec

                rec.completion_event_id = event.event_id
                rec.completed_at = now
                if tool_name != "unknown_tool":
                    rec.tool_name = tool_name

                # Determine outcome status
                if error is not None or success is False:
                    rec.status = ToolInvocationStatus.FAILED
                    rec.success = False
                    rec.error = error or "Tool execution failed"
                else:
                    rec.status = ToolInvocationStatus.COMPLETED
                    rec.success = True
                    rec.error = None

                # Determine duration
                if duration_ms is not None:
                    try:
                        d_val = float(duration_ms)
                        rec.duration_ms = d_val if d_val >= 0 else None
                    except (ValueError, TypeError):
                        rec.duration_ms = None
                elif rec.started_at and rec.completed_at:
                    diff = (rec.completed_at - rec.started_at).total_seconds() * 1000.0
                    rec.duration_ms = diff if diff >= 0 else None

            self._recalculate_summary(event.execution_id)
            return summary.model_copy(deep=True)

    def get_execution_summary(self, execution_id: str) -> Optional[ExecutionToolSummary]:
        """Retrieve aggregated tool activity summary for a specific execution."""
        if not execution_id:
            return None
        with self._lock:
            summary = self._summaries.get(execution_id.strip())
            return summary.model_copy(deep=True) if summary else None

    def list_execution_summaries(self) -> List[ExecutionToolSummary]:
        """List all active execution tool summaries."""
        with self._lock:
            return [s.model_copy(deep=True) for s in self._summaries.values()]

    def get_invocation(self, execution_id: str, call_id: str) -> Optional[ToolInvocationRecord]:
        """Retrieve a specific tool invocation record by execution_id and call_id."""
        if not execution_id or not call_id:
            return None
        with self._lock:
            inv_map = self._invocations.get(execution_id.strip(), {})
            rec = inv_map.get(call_id.strip())
            return rec.model_copy(deep=True) if rec else None

    def attach_to_bus(self, bus: IEventBus) -> List[str]:
        """Subscribe to ToolCalled and ToolCompleted events on the Event Bus."""
        with self._lock:
            sub_ids = []
            for ev_type in self.TOOL_EVENT_TYPES:
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
        """Clear all in-memory tool observations and summaries."""
        with self._lock:
            self._summaries.clear()
            self._invocations.clear()
            self._seen_event_ids.clear()
            self._subscription_ids.clear()
