"""Validation routines for Execution Events."""

from datetime import datetime
from typing import Any

from infuse.contracts.events import EventSource, EventType, ExecutionEvent
from infuse.events.errors import EventValidationError
from infuse.version import SCHEMA_VERSION


def validate_execution_event(event: Any) -> ExecutionEvent:
    """Validate that the given object is a compliant, well-formed ExecutionEvent envelope.
    
    Raises:
        EventValidationError: If any field is missing, invalid, or out of spec.
    """
    if not isinstance(event, ExecutionEvent):
        if hasattr(event, "model_dump"):
            try:
                event = ExecutionEvent.model_validate(event.model_dump())
            except Exception as e:
                raise EventValidationError(f"Cannot cast payload to ExecutionEvent: {str(e)}")
        elif isinstance(event, dict):
            try:
                event = ExecutionEvent.model_validate(event)
            except Exception as e:
                raise EventValidationError(f"Invalid ExecutionEvent dictionary: {str(e)}")
        else:
            raise EventValidationError(f"Expected ExecutionEvent instance, got {type(event).__name__}")

    # Validate event_id
    if not event.event_id or not isinstance(event.event_id, str) or not event.event_id.strip():
        raise EventValidationError("event_id must be a non-empty string")

    # Validate execution_id
    if not event.execution_id or not isinstance(event.execution_id, str) or not event.execution_id.strip():
        raise EventValidationError("execution_id must be a non-empty string")

    # Validate timestamp
    if not isinstance(event.timestamp, datetime):
        raise EventValidationError(f"timestamp must be a valid datetime, got {type(event.timestamp).__name__}")

    # Validate event type
    if not isinstance(event.type, EventType):
        try:
            EventType(str(event.type))
        except ValueError:
            raise EventValidationError(f"Unknown or invalid event type: '{event.type}'")

    # Validate event source
    if not isinstance(event.source, EventSource):
        try:
            EventSource(str(event.source))
        except ValueError:
            raise EventValidationError(f"Unknown or invalid event source: '{event.source}'")

    # Validate sequence
    if event.sequence is None or not isinstance(event.sequence, int) or event.sequence < 0:
        raise EventValidationError(f"sequence must be a non-negative integer, got {event.sequence}")

    # Validate payload
    if not isinstance(event.payload, dict):
        raise EventValidationError(f"payload must be a dictionary, got {type(event.payload).__name__}")

    # Validate schema version
    if not event.schema_version or not isinstance(event.schema_version, str):
        raise EventValidationError("schema_version must be a non-empty string")

    return event
