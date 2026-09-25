"""Starlette router and endpoints for the INFUSE ChatGPT App."""

import json
from typing import Any, Dict, Optional
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route, Router

from infuse.chatgpt.auth import AuthError, AuthenticatedContext, ChatGptAuthService
from infuse.chatgpt.config import ChatGptAppConfig
from infuse.chatgpt.models import (
    ControlExecutionInput,
    ExecuteTaskInput,
    GetExecutionInput,
    GetPolicyInput,
    ListExecutionsInput,
)
from infuse.chatgpt.schema import generate_openapi_schema
from infuse.chatgpt.tools import ChatGptToolRegistry
from infuse.sdk.client import InfuseClient
from infuse.sdk.transport import ITransport, TransportResponse


class InProcessStarletteTransport(ITransport):
    """Deterministic in-memory transport routing directly to Starlette API app."""

    def __init__(self, app: Optional[Any] = None) -> None:
        from infuse.api.app import create_app
        from starlette.testclient import TestClient

        self.app = app or create_app()
        self.client = TestClient(self.app)

    def send_request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> TransportResponse:
        resp = self.client.request(
            method=method,
            url=path,
            params=params,
            json=json_data,
            headers=headers,
        )
        try:
            data = resp.json()
        except Exception:
            data = resp.text
        return TransportResponse(
            status_code=resp.status_code,
            data=data,
            headers=dict(resp.headers),
        )


def create_chatgpt_router(
    client: Optional[InfuseClient] = None,
    config: Optional[ChatGptAppConfig] = None,
) -> Router:
    """Create Starlette Router exposing ChatGPT Action endpoints."""
    cfg = config or ChatGptAppConfig.from_env()
    sdk_client = client or InfuseClient(transport=InProcessStarletteTransport())
    auth_service = ChatGptAuthService(cfg)
    tool_registry = ChatGptToolRegistry(sdk_client)

    def _authenticate(request: Request) -> AuthenticatedContext:
        """Helper to extract authorization header and authenticate."""
        auth_header = request.headers.get("Authorization")
        return auth_service.authenticate_header(auth_header)

    async def openapi_schema_endpoint(request: Request) -> JSONResponse:
        """Serve dynamic OpenAPI 3.1.0 schema."""
        base_url = str(request.base_url).rstrip("/")
        schema = generate_openapi_schema(server_url=cfg.public_url or base_url)
        return JSONResponse(content=schema)

    async def system_endpoint(request: Request) -> JSONResponse:
        try:
            ctx = _authenticate(request)
            auth_service.enforce_scope(ctx, "read:executions")
            res = tool_registry.get_system_info(ctx)
            return JSONResponse(content=res.model_dump(mode="json"))
        except AuthError as exc:
            return JSONResponse(
                content={"success": False, "tool_name": "get_system_info", "category": "READ", "error": exc.message, "error_code": exc.error_code},
                status_code=exc.status_code,
            )

    async def list_executions_endpoint(request: Request) -> JSONResponse:
        try:
            ctx = _authenticate(request)
            auth_service.enforce_scope(ctx, "read:executions")
            params = ListExecutionsInput(
                query=request.query_params.get("query"),
                state=request.query_params.get("state"),
                agent=request.query_params.get("agent"),
                limit=int(request.query_params.get("limit", 20)),
                offset=int(request.query_params.get("offset", 0)),
            )
            res = tool_registry.list_executions(params, ctx)
            return JSONResponse(content=res.model_dump(mode="json"))
        except AuthError as exc:
            return JSONResponse(
                content={"success": False, "tool_name": "list_executions", "category": "READ", "error": exc.message, "error_code": exc.error_code},
                status_code=exc.status_code,
            )
        except Exception as exc:
            return JSONResponse(
                content={"success": False, "tool_name": "list_executions", "category": "READ", "error": str(exc), "error_code": "INVALID_PARAMETERS"},
                status_code=400,
            )

    async def execution_state_endpoint(request: Request) -> JSONResponse:
        try:
            ctx = _authenticate(request)
            auth_service.enforce_scope(ctx, "read:executions")
            exec_id = request.path_params.get("execution_id", "")
            params = GetExecutionInput(execution_id=exec_id)
            res = tool_registry.get_execution_state(params, ctx)
            return JSONResponse(content=res.model_dump(mode="json"))
        except AuthError as exc:
            return JSONResponse(
                content={"success": False, "tool_name": "get_execution_state", "category": "ANALYZE", "error": exc.message, "error_code": exc.error_code},
                status_code=exc.status_code,
            )

    async def execution_result_endpoint(request: Request) -> JSONResponse:
        try:
            ctx = _authenticate(request)
            auth_service.enforce_scope(ctx, "read:executions")
            exec_id = request.path_params.get("execution_id", "")
            params = GetExecutionInput(execution_id=exec_id)
            res = tool_registry.get_execution_result(params, ctx)
            return JSONResponse(content=res.model_dump(mode="json"))
        except AuthError as exc:
            return JSONResponse(
                content={"success": False, "tool_name": "get_execution_result", "category": "READ", "error": exc.message, "error_code": exc.error_code},
                status_code=exc.status_code,
            )

    async def inspect_execution_endpoint(request: Request) -> JSONResponse:
        try:
            ctx = _authenticate(request)
            auth_service.enforce_scope(ctx, "read:executions")
            exec_id = request.path_params.get("execution_id", "")
            params = GetExecutionInput(execution_id=exec_id)
            res = tool_registry.inspect_execution(params, ctx)
            return JSONResponse(content=res.model_dump(mode="json"))
        except AuthError as exc:
            return JSONResponse(
                content={"success": False, "tool_name": "inspect_execution", "category": "ANALYZE", "error": exc.message, "error_code": exc.error_code},
                status_code=exc.status_code,
            )

    async def governor_decision_endpoint(request: Request) -> JSONResponse:
        try:
            ctx = _authenticate(request)
            auth_service.enforce_scope(ctx, "read:executions")
            exec_id = request.path_params.get("execution_id", "")
            params = GetExecutionInput(execution_id=exec_id)
            res = tool_registry.inspect_governor_decision(params, ctx)
            return JSONResponse(content=res.model_dump(mode="json"))
        except AuthError as exc:
            return JSONResponse(
                content={"success": False, "tool_name": "inspect_governor_decision", "category": "ANALYZE", "error": exc.message, "error_code": exc.error_code},
                status_code=exc.status_code,
            )

    async def provider_health_endpoint(request: Request) -> JSONResponse:
        try:
            ctx = _authenticate(request)
            auth_service.enforce_scope(ctx, "read:executions")
            res = tool_registry.get_provider_health(ctx)
            return JSONResponse(content=res.model_dump(mode="json"))
        except AuthError as exc:
            return JSONResponse(
                content={"success": False, "tool_name": "get_provider_health", "category": "READ", "error": exc.message, "error_code": exc.error_code},
                status_code=exc.status_code,
            )

    async def list_policies_endpoint(request: Request) -> JSONResponse:
        try:
            ctx = _authenticate(request)
            auth_service.enforce_scope(ctx, "read:policies")
            res = tool_registry.list_policies(ctx)
            return JSONResponse(content=res.model_dump(mode="json"))
        except AuthError as exc:
            return JSONResponse(
                content={"success": False, "tool_name": "list_policies", "category": "READ", "error": exc.message, "error_code": exc.error_code},
                status_code=exc.status_code,
            )

    async def get_policy_endpoint(request: Request) -> JSONResponse:
        try:
            ctx = _authenticate(request)
            auth_service.enforce_scope(ctx, "read:policies")
            pol_id = request.path_params.get("policy_id", "")
            params = GetPolicyInput(policy_id=pol_id if pol_id else None)
            res = tool_registry.get_policy(params, ctx)
            return JSONResponse(content=res.model_dump(mode="json"))
        except AuthError as exc:
            return JSONResponse(
                content={"success": False, "tool_name": "get_policy", "category": "READ", "error": exc.message, "error_code": exc.error_code},
                status_code=exc.status_code,
            )

    async def execute_task_endpoint(request: Request) -> JSONResponse:
        try:
            ctx = _authenticate(request)
            auth_service.enforce_scope(ctx, "execute:tasks")
            body = await request.json()
            params = ExecuteTaskInput.model_validate(body)
            res = tool_registry.execute_task(params, ctx)
            return JSONResponse(content=res.model_dump(mode="json"))
        except AuthError as exc:
            return JSONResponse(
                content={"success": False, "tool_name": "execute_task", "category": "EXECUTE", "error": exc.message, "error_code": exc.error_code},
                status_code=exc.status_code,
            )
        except Exception as exc:
            return JSONResponse(
                content={"success": False, "tool_name": "execute_task", "category": "EXECUTE", "error": str(exc), "error_code": "INVALID_REQUEST_BODY"},
                status_code=422,
            )

    async def control_execution_endpoint(request: Request) -> JSONResponse:
        try:
            ctx = _authenticate(request)
            auth_service.enforce_scope(ctx, "control:write")
            body = await request.json()
            params = ControlExecutionInput.model_validate(body)
            res = tool_registry.control_execution(params, ctx)
            return JSONResponse(content=res.model_dump(mode="json"))
        except AuthError as exc:
            return JSONResponse(
                content={"success": False, "tool_name": "control_execution", "category": "CONTROL", "error": exc.message, "error_code": exc.error_code},
                status_code=exc.status_code,
            )
        except Exception as exc:
            return JSONResponse(
                content={"success": False, "tool_name": "control_execution", "category": "CONTROL", "error": str(exc), "error_code": "INVALID_REQUEST_BODY"},
                status_code=422,
            )

    routes = [
        Route("/openapi.json", openapi_schema_endpoint, methods=["GET"]),
        Route("/v1/system", system_endpoint, methods=["GET"]),
        Route("/v1/executions", list_executions_endpoint, methods=["GET"]),
        Route("/v1/executions/{execution_id}/state", execution_state_endpoint, methods=["GET"]),
        Route("/v1/executions/{execution_id}/result", execution_result_endpoint, methods=["GET"]),
        Route("/v1/executions/{execution_id}/inspect", inspect_execution_endpoint, methods=["GET"]),
        Route("/v1/executions/{execution_id}/governor", governor_decision_endpoint, methods=["GET"]),
        Route("/v1/providers/health", provider_health_endpoint, methods=["GET"]),
        Route("/v1/policies", list_policies_endpoint, methods=["GET"]),
        Route("/v1/policies/{policy_id}", get_policy_endpoint, methods=["GET"]),
        Route("/v1/execute", execute_task_endpoint, methods=["POST"]),
        Route("/v1/control", control_execution_endpoint, methods=["POST"]),
    ]

    return Router(routes=routes)
