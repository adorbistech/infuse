"""Production Application Factory and Server Runner for Block 35.

Wires the Starlette HTTP API with production deployment configuration,
system readiness probe, and graceful shutdown signal handling.
"""

import logging
import signal
import sys
import time
from typing import Any, Dict, List, Optional
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from infuse.api.app import CorrelationIdMiddleware, create_app as create_base_api_app
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

    # Add extra routes to the base application router
    base_app.router.routes.extend([
        Route("/ready", endpoint=ready_endpoint, methods=["GET"]),
        Route("/v1/ready", endpoint=ready_endpoint, methods=["GET"]),
        Route("/v1/info", endpoint=info_endpoint, methods=["GET"]),
    ])

    return base_app


def run_production_server(
    config: Optional[DeploymentConfig] = None,
) -> None:
    """Entrypoint to run the INFUSE production HTTP server."""
    cfg = config or load_deployment_config()

    logging.basicConfig(
        level=getattr(logging, cfg.log_level.value, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    logger.info(
        f"Starting INFUSE Production Server v{__version__} on {cfg.host}:{cfg.port} [{cfg.environment.value}]"
    )

    app = create_production_app(config=cfg)

    try:
        import uvicorn  # type: ignore

        uvicorn_config = uvicorn.Config(
            app=app,
            host=cfg.host,
            port=cfg.port,
            log_level=cfg.log_level.value.lower(),
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
