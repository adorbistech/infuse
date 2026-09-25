"""Production Application Factory and Server Runner for Block 35.

Wires the Starlette HTTP API with production deployment configuration,
system readiness probe, and graceful shutdown signal handling.
"""

import logging
import signal
import sys
import time
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Mount, Route

from infuse.api.app import CorrelationIdMiddleware, create_app as create_base_api_app
from infuse.chatgpt.router import create_chatgpt_router
from infuse.mcp.server import create_mcp_server
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
from infuse.deployment.config import DeploymentConfig, load_deployment_config
from infuse.deployment.health import ReadinessStatus, SystemReadinessProbe
from infuse.version import __version__, SCHEMA_VERSION

logger = logging.getLogger("infuse.deployment")


class ProductionServerContext:
    """Encapsulates active production server runtime state and lifecycle."""

    def __init__(self, config: DeploymentConfig) -> None:
        self.config = config
        self.start_time = time.time()
        self.is_shutting_down = False
        self.readiness_probe = SystemReadinessProbe(start_time=self.start_time)
        self.execution_service: IExecutionService = DefaultExecutionService()
        self.event_service: IEventService = DefaultEventService()
        self.policy_service: IPolicyService = DefaultPolicyService()


def create_production_app(
    config: Optional[DeploymentConfig] = None,
    context: Optional[ProductionServerContext] = None,
) -> Starlette:
    """Create a fully configured, production-ready Starlette application."""
    cfg = config or load_deployment_config()
    ctx = context or ProductionServerContext(cfg)

    # 1. Base API App
    base_app = create_base_api_app(
        execution_service=ctx.execution_service,
        event_service=ctx.event_service,
        policy_service=ctx.policy_service,
    )

    # 2. Define Deployment-Specific Routes
    async def ready_endpoint(request: Request) -> JSONResponse:
        """Readiness check verifying all subsystem dependencies."""
        if ctx.is_shutting_down:
            return JSONResponse(
                content={
                    "status": "UNREADY",
                    "reason": "Server is shutting down.",
                    "version": __version__,
                },
                status_code=503,
            )

        report = ctx.readiness_probe.evaluate_readiness(
            execution_service=ctx.execution_service,
            event_service=ctx.event_service,
            policy_service=ctx.policy_service,
        )
        status_code = 200 if report.status == ReadinessStatus.READY else 503
        return JSONResponse(content=report.model_dump(mode="json"), status_code=status_code)

    async def info_endpoint(request: Request) -> JSONResponse:
        """Sanitized deployment environment and version info without secrets."""
        safe_info = {
            "name": "INFUSE — Execution Intelligence",
            "version": __version__,
            "schema_version": SCHEMA_VERSION,
            "environment": cfg.environment.value if hasattr(cfg.environment, "value") else str(cfg.environment),
            "metrics_enabled": cfg.enable_metrics,
            "readiness_probe_enabled": cfg.enable_readiness_probe,
            "mcp_server_enabled": cfg.mcp_server_enabled,
            "uptime_seconds": round(time.time() - ctx.start_time, 2),
        }
        return JSONResponse(content=safe_info, status_code=200)

    async def openai_challenge_endpoint(request: Request) -> PlainTextResponse:
        """OpenAI Apps domain challenge verification endpoint."""
        token = os.getenv("OPENAI_APPS_CHALLENGE_TOKEN")
        if not token:
            return PlainTextResponse("OpenAI challenge not configured", status_code=404)
        return PlainTextResponse(token, status_code=200, media_type="text/plain")

    # 3. FastMCP Streamable HTTP Server Setup
    mcp_server = create_mcp_server()
    mcp_server.settings.transport_security.enable_dns_rebinding_protection = False
    mcp_app = mcp_server.streamable_http_app()

    @asynccontextmanager
    async def production_lifespan(app: Starlette):
        async with mcp_server.session_manager.run():
            yield

    base_app.router.lifespan_context = production_lifespan

    # 4. Attach routes to base router
    chatgpt_router = create_chatgpt_router()
    base_app.router.routes.extend([
        Route("/ready", endpoint=ready_endpoint, methods=["GET"]),
        Route("/v1/ready", endpoint=ready_endpoint, methods=["GET"]),
        Route("/v1/info", endpoint=info_endpoint, methods=["GET"]),
        Route("/.well-known/openai-apps-challenge", endpoint=openai_challenge_endpoint, methods=["GET"]),
        Mount("/chatgpt", app=chatgpt_router),
    ])
    base_app.router.routes.extend(mcp_app.routes)

    return base_app


def run_production_server(
    config: Optional[DeploymentConfig] = None,
) -> None:
    """Entrypoint to run the INFUSE production HTTP server."""
    cfg = config or load_deployment_config()

    log_level_str = cfg.log_level.value if hasattr(cfg.log_level, "value") else str(cfg.log_level)
    env_str = cfg.environment.value if hasattr(cfg.environment, "value") else str(cfg.environment)

    logging.basicConfig(
        level=getattr(logging, log_level_str.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    logger.info(
        f"Starting INFUSE Production Server v{__version__} on {cfg.host}:{cfg.port} [{env_str}]"
    )

    app = create_production_app(config=cfg)

    try:
        import uvicorn  # type: ignore

        uvicorn_config = uvicorn.Config(
            app=app,
            host=cfg.host,
            port=cfg.port,
            log_level=log_level_str.lower(),
            timeout_graceful_shutdown=int(cfg.graceful_shutdown_timeout_sec),
            access_log=True,
        )
        server = uvicorn.Server(uvicorn_config)
        server.run()
    except ImportError:
        logger.warning(
            "uvicorn is not installed. Running in test/direct ASGI application mode."
        )


def main() -> None:
    """CLI script entrypoint for 'infuse-server'."""
    try:
        config = load_deployment_config()
        run_production_server(config)
    except Exception as exc:
        sys.stderr.write(f"Fatal error starting INFUSE server: {exc}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
