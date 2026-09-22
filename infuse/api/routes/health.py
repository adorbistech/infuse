"""Operational health check endpoints."""

from starlette.requests import Request
from starlette.responses import JSONResponse

from infuse.version import __version__, SCHEMA_VERSION


async def health_check(request: Request) -> JSONResponse:
    """Return operational health status."""
    return JSONResponse(
        content={
            "status": "OK",
            "version": __version__,
            "schema_version": SCHEMA_VERSION
        },
        status_code=200
    )
