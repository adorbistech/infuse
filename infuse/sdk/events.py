"""Event Client for the INFUSE SDK (Block 28).

Provides typed operations for publishing telemetry and runtime events
onto the canonical INFUSE Event Bus.
"""

from typing import Any, Dict, Union
from pydantic import ValidationError

from infuse.contracts.events import ExecutionEvent
from infuse.sdk.errors import ValidationError as SdkValidationError
from infuse.sdk.models import EventIngestResponse
from infuse.sdk.transport import ITransport


class EventClient:
    """Developer-facing interface for event publishing and ingestion."""

    def __init__(self, transport: ITransport) -> None:
        self._transport = transport

    def publish(
        self,
        execution_id: str,
        event: Union[ExecutionEvent, Dict[str, Any]],
    ) -> EventIngestResponse:
        """Publish an execution telemetry event.

        Maps to: POST /v1/executions/{id}/events
        """
        if not execution_id or not execution_id.strip():
            raise ValueError("execution_id must not be empty.")

        clean_id = execution_id.strip()

        if isinstance(event, dict):
            event_dict = dict(event)
            if "execution_id" not in event_dict or not event_dict["execution_id"]:
                event_dict["execution_id"] = clean_id
            try:
                validated_ev = ExecutionEvent.model_validate(event_dict)
            except ValidationError as exc:
                raise SdkValidationError(
                    message="Invalid execution event schema.",
                    details={"errors": exc.errors()},
                ) from exc
        elif isinstance(event, ExecutionEvent):
            validated_ev = event
        else:
            raise ValueError("event must be an ExecutionEvent instance or a valid dictionary.")

        payload = validated_ev.model_dump(mode="json")
        resp = self._transport.send_request(
            method="POST",
            path=f"/v1/executions/{clean_id}/events",
            json_data=payload,
        )

        raw = resp.data or {}
        return EventIngestResponse(
            status=raw.get("status", "INGESTED"),
            event_id=raw.get("event_id", validated_ev.event_id),
            execution_id=clean_id,
            schema_version=raw.get("schema_version", "1.0.0"),
        )


__all__ = ["EventClient"]
