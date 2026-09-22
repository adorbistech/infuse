"""POST /v1/execute route handler."""

import json
from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse

from infuse.api.errors import MalformedJsonError, RequestValidationError
from infuse.contracts.execution import ExecutionRequest


async def execute_operation(request: Request) -> JSONResponse:
    """Handle normalized execution dispatch request."""
    try:
        body = await request.json()
    except Exception as exc:
        raise MalformedJsonError("Request body must be valid JSON.") from exc

    if not isinstance(body, dict):
        raise RequestValidationError("Execution request payload must be a JSON object.")

    try:
        exec_request = ExecutionRequest.model_validate(body)
    except ValidationError as exc:
        raise RequestValidationError(
            message="Invalid execution request schema.",
            details={"errors": exc.errors()}
        ) from exc

    execution_service = request.app.state.execution_service
    result = execution_service.execute(exec_request)

    return JSONResponse(
        content=result.model_dump(mode="json"),
        status_code=200
    )
