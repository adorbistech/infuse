"""Executions and event ingestion route handlers."""

from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse

from infuse.api.errors import (
    BadRequestError,
    MalformedJsonError,
    NotFoundError,
    RequestValidationError,
)
from infuse.contracts.events import ExecutionEvent
from infuse.version import SCHEMA_VERSION


async def list_executions(request: Request) -> JSONResponse:
    """GET /v1/executions - List and filter execution summaries."""
    query_params = request.query_params
    query = query_params.get("query")
    state = query_params.get("state")
    agent = query_params.get("agent")
    
    limit_str = query_params.get("limit", "50")
    offset_str = query_params.get("offset", "0")

    try:
        limit = int(limit_str)
        if limit < 1 or limit > 200:
            raise ValueError("Limit must be between 1 and 200.")
    except ValueError as exc:
        raise BadRequestError(f"Invalid 'limit' query parameter: {limit_str}") from exc

    try:
        offset = int(offset_str)
        if offset < 0:
            raise ValueError("Offset must be non-negative.")
    except ValueError as exc:
        raise BadRequestError(f"Invalid 'offset' query parameter: {offset_str}") from exc

    execution_service = request.app.state.execution_service
    results = execution_service.list_executions(
        query=query,
        state=state,
        agent=agent,
        limit=limit,
        offset=offset
    )
    return JSONResponse(content=results, status_code=200)


async def get_execution(request: Request) -> JSONResponse:
    """GET /v1/executions/{id} - Retrieve detailed execution telemetry."""
    execution_id = request.path_params.get("id", "").strip()
    if not execution_id:
        raise BadRequestError("Execution ID path parameter is required.")

    execution_service = request.app.state.execution_service
    execution = execution_service.get_execution(execution_id)
    if not execution:
        raise NotFoundError(f"Execution with ID '{execution_id}' was not found.")

    return JSONResponse(
        content=execution.model_dump(mode="json"),
        status_code=200
    )


async def ingest_event(request: Request) -> JSONResponse:
    """POST /v1/executions/{id}/events - Ingest execution telemetry event."""
    execution_id = request.path_params.get("id", "").strip()
    if not execution_id:
        raise BadRequestError("Execution ID path parameter is required.")

    try:
        body = await request.json()
    except Exception as exc:
        raise MalformedJsonError("Request body must be valid JSON.") from exc

    if not isinstance(body, dict):
        raise RequestValidationError("Event payload must be a JSON object.")

    # Populate execution_id from path if not provided in payload
    if "execution_id" not in body or not body["execution_id"]:
        body["execution_id"] = execution_id

    try:
        event = ExecutionEvent.model_validate(body)
    except ValidationError as exc:
        raise RequestValidationError(
            message="Invalid execution event schema.",
            details={"errors": exc.errors()}
        ) from exc

    event_service = request.app.state.event_service
    event_id = event_service.ingest_event(execution_id, event)

    return JSONResponse(
        content={
            "status": "INGESTED",
            "event_id": event_id,
            "execution_id": execution_id,
            "schema_version": SCHEMA_VERSION
        },
        status_code=201
    )
