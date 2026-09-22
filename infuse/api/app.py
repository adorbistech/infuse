"""Starlette application factory for the INFUSE Universal HTTP API."""

import uuid
from typing import Optional
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from infuse.api.errors import ApiError, ErrorCode
from infuse.api.routes.execute import execute_operation
from infuse.api.routes.executions import get_execution, ingest_event, list_executions
from infuse.api.routes.health import health_check
from infuse.api.routes.policies import list_policies, update_policy
from infuse.api.schemas.errors import ApiErrorResponse
from infuse.api.services.default import (
    DefaultEventService,
    DefaultExecutionService,
    DefaultPolicyService,
)
from infuse.api.services.interfaces import (
    IEventService,
    IExecutionService,
    IPolicyService,
)
from infuse.version import SCHEMA_VERSION


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Extract or generate correlation identifier and attach to request and response headers."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        correlation_id = (
            request.headers.get("X-Correlation-ID")
            or request.headers.get("X-Request-ID")
            or f"corr_{uuid.uuid4().hex[:12]}"
        )
        request.state.correlation_id = correlation_id
        
        try:
            response = await call_next(request)
        except ApiError as exc:
            response = exc.to_response(correlation_id=correlation_id)
        except Exception:
            # Internal server error without leaking stack trace
            error_dto = ApiErrorResponse(
                code=ErrorCode.INTERNAL_ERROR.value,
                message="An unexpected internal server error occurred.",
                details=None,
                correlation_id=correlation_id,
                schema_version=SCHEMA_VERSION
            )
            response = JSONResponse(
                content=error_dto.model_dump(),
                status_code=500
            )

        response.headers["X-Correlation-ID"] = correlation_id
        return response


def create_app(
    execution_service: Optional[IExecutionService] = None,
    event_service: Optional[IEventService] = None,
    policy_service: Optional[IPolicyService] = None,
) -> Starlette:
    """Create and configure the Starlette ASGI application for INFUSE Universal HTTP API."""

    routes = [
        # Health & Operational
        Route("/health", health_check, methods=["GET"]),
        Route("/v1/health", health_check, methods=["GET"]),

        # Execution Lifecycle
        Route("/v1/execute", execute_operation, methods=["POST"]),
        Route("/v1/executions", list_executions, methods=["GET"]),
        Route("/v1/executions/{id}", get_execution, methods=["GET"]),

        # Event Ingestion
        Route("/v1/executions/{id}/events", ingest_event, methods=["POST"]),

        # Governance Policies
        Route("/v1/policies", list_policies, methods=["GET"]),
        Route("/v1/policies/{id}", update_policy, methods=["PUT"]),
    ]

    middleware = [
        Middleware(CorrelationIdMiddleware),
    ]

    app = Starlette(
        debug=False,
        routes=routes,
        middleware=middleware,
    )

    # Attach service layer instances to app state
    app.state.execution_service = execution_service or DefaultExecutionService()
    app.state.event_service = event_service or DefaultEventService()
    app.state.policy_service = policy_service or DefaultPolicyService()

    return app
