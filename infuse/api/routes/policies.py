"""Governance Policy route handlers."""

from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse

from infuse.api.errors import (
    BadRequestError,
    MalformedJsonError,
    RequestValidationError,
)
from infuse.contracts.policy import GovernancePolicy
from infuse.version import SCHEMA_VERSION


async def list_policies(request: Request) -> JSONResponse:
    """GET /v1/policies - Retrieve active policy and all policy revisions."""
    policy_service = request.app.state.policy_service
    policies = policy_service.list_policies()
    active_policy = policy_service.get_active_policy()

    return JSONResponse(
        content={
            "policies": [p.model_dump(mode="json") for p in policies],
            "active_policy": active_policy.model_dump(mode="json") if active_policy else None,
            "schema_version": SCHEMA_VERSION
        },
        status_code=200
    )


async def update_policy(request: Request) -> JSONResponse:
    """PUT /v1/policies/{id} - Create or update a governance policy."""
    policy_id = request.path_params.get("id", "").strip()
    if not policy_id:
        raise BadRequestError("Policy ID path parameter is required.")

    try:
        body = await request.json()
    except Exception as exc:
        raise MalformedJsonError("Request body must be valid JSON.") from exc

    if not isinstance(body, dict):
        raise RequestValidationError("Policy payload must be a JSON object.")

    # Ensure policy_id matches path if present, or assign from path
    body["policy_id"] = policy_id

    try:
        policy = GovernancePolicy.model_validate(body)
    except ValidationError as exc:
        raise RequestValidationError(
            message="Invalid governance policy schema.",
            details={"errors": exc.errors()}
        ) from exc

    policy_service = request.app.state.policy_service
    saved_policy = policy_service.update_policy(policy_id, policy)

    return JSONResponse(
        content=saved_policy.model_dump(mode="json"),
        status_code=200
    )
