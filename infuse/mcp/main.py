"""INFUSE MCP Server main CLI entrypoint (Block 30).

Launches the Model Context Protocol server over stdio or HTTP transports.
Ensures strict stdio / stderr separation so JSON-RPC protocol messages are never
polluted by diagnostic logs.
"""

import argparse
import logging
import sys
from typing import List, Optional

from infuse.mcp.config import McpServerConfig
from infuse.mcp.server import create_mcp_server
from infuse.version import __version__


def setup_logging(log_level_str: str = "INFO") -> None:
    """Configure logging to write strictly to stderr."""
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
        force=True,
    )


def create_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser for the MCP server."""
    parser = argparse.ArgumentParser(
        prog="infuse-mcp",
        description="INFUSE — Model Context Protocol (MCP) Server (Block 30)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--endpoint",
        "--base-url",
        dest="base_url",
        type=str,
        default=None,
        help="Target INFUSE API base URL (overrides INFUSE_BASE_URL)",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="INFUSE authorization key (overrides INFUSE_API_KEY)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="Request timeout in seconds (overrides INFUSE_TIMEOUT_SECONDS)",
    )
    parser.add_argument(
        "--transport",
        type=str,
        choices=["stdio", "streamable_http", "sse"],
        default="stdio",
        help="MCP transport protocol",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host address for HTTP/SSE transport",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8001,
        help="Port for HTTP/SSE transport",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging verbosity level (written to stderr)",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        default=False,
        help="Print INFUSE MCP server version and exit",
    )
    return parser


def run_server(args: Optional[List[str]] = None) -> int:
    """Run the MCP server entry point."""
    parser = create_parser()
    parsed = parser.parse_args(args if args is not None else sys.argv[1:])

    if parsed.version:
        print(f"INFUSE MCP Server v{__version__}")
        return 0

    setup_logging(parsed.log_level)
    logger = logging.getLogger("infuse.mcp")
    logger.info(f"Starting INFUSE MCP Server v{__version__} on transport={parsed.transport}")

    cfg = McpServerConfig.from_env()
    if parsed.base_url:
        cfg.base_url = parsed.base_url
    if parsed.api_key:
        cfg.api_key = parsed.api_key
    if parsed.timeout:
        cfg.timeout_seconds = parsed.timeout
    cfg.transport = parsed.transport
    cfg.log_level = parsed.log_level

    server = create_mcp_server(config=cfg)

    # Run with selected transport
    if parsed.transport == "stdio":
        server.run(transport="stdio")
    elif parsed.transport in ("streamable_http", "sse"):
        server.run(transport=parsed.transport)
    else:
        server.run(transport="stdio")

    return 0


def main() -> None:
    """Console script entrypoint."""
    sys.exit(run_server())


if __name__ == "__main__":
    main()
