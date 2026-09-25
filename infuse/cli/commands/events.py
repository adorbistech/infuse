"""Events commands for INFUSE CLI (Block 29)."""

import json
import os
import sys
import uuid
from typing import Any, Dict, Optional

from infuse.cli.exit_codes import EXIT_SUCCESS, EXIT_USAGE_ERROR
from infuse.cli.formatter import (
    format_error,
    format_event_response,
    format_json,
)
from infuse.contracts.events import EventSource, EventType, ExecutionEvent
from infuse.sdk.client import InfuseClient


def handle_events_publish(
    client: InfuseClient,
    execution_id: str,
    event_type: Optional[str] = None,
    source: Optional[str] = None,
    payload_str: Optional[str] = None,
    input_file: Optional[str] = None,
    sequence: int = 1,
    json_mode: bool = False,
) -> int:
    """Publish a telemetry event for an execution."""
    if input_file:
        if not os.path.exists(input_file):
            print(
                format_error(f"Event file not found: {input_file}", "FILE_NOT_FOUND", json_mode=json_mode),
                file=sys.stderr,
            )
            return EXIT_USAGE_ERROR
        try:
            with open(input_file, "r", encoding="utf-8") as f:
                event_data = json.load(f)
            if isinstance(event_data, dict):
                event_data["execution_id"] = execution_id
                if "event_id" not in event_data:
                    event_data["event_id"] = f"evt_{uuid.uuid4().hex[:8]}"
            resp = client.events.publish(execution_id, event_data)
            print(format_event_response(resp, json_mode=json_mode))
            return EXIT_SUCCESS
        except Exception as exc:
            print(
                format_error(f"Failed to read event file: {exc}", "INVALID_INPUT", json_mode=json_mode),
                file=sys.stderr,
            )
            return EXIT_USAGE_ERROR

    payload_dict: Dict[str, Any] = {}
    if payload_str:
        try:
            payload_dict = json.loads(payload_str)
        except Exception:
            payload_dict = {"message": payload_str}

    ev_type = EventType.TOKEN_OBSERVED
    if event_type:
        try:
            # Handle case insensitive or matching
            for et in EventType:
                if et.value.lower() == event_type.lower() or et.name.lower() == event_type.lower():
                    ev_type = et
                    break
        except Exception:
            ev_type = EventType.TOKEN_OBSERVED

    ev_src = EventSource.AGENT
    if source:
        try:
            for es in EventSource:
                if es.value.lower() == source.lower() or es.name.lower() == source.lower():
                    ev_src = es
                    break
        except Exception:
            ev_src = EventSource.AGENT

    event = ExecutionEvent(
        event_id=f"evt_{uuid.uuid4().hex[:8]}",
        execution_id=execution_id,
        sequence=sequence,
        type=ev_type,
        source=ev_src,
        payload=payload_dict,
    )

    resp = client.events.publish(execution_id, event)
    print(format_event_response(resp, json_mode=json_mode))
    return EXIT_SUCCESS


def handle_events_list(
    client: InfuseClient,
    execution_id: str,
    json_mode: bool = False,
) -> int:
    """Inspect timeline events for an execution."""
    summary = client.executions.get(execution_id)
    events_data = getattr(summary, "timeline_events", [])
    if json_mode:
        print(format_json(events_data))
    else:
        if not events_data:
            print(f"No timeline events recorded for execution '{execution_id}'.")
        else:
            print(f"Timeline events for execution '{execution_id}':")
            for ev in events_data:
                print(f"  - [{getattr(ev, 'timestamp', '')}] {getattr(ev, 'event_type', '')}: {getattr(ev, 'summary', '')}")
    return EXIT_SUCCESS


__all__ = [
    "handle_events_publish",
    "handle_events_list",
]
