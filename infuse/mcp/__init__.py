"""INFUSE Model Context Protocol (MCP) Server Layer (Block 30).

Exposes the full capabilities of INFUSE to MCP-compliant AI agents and tools
strictly via the Block 28 SDK.
"""

from infuse.mcp.config import McpServerConfig
from infuse.mcp.errors import format_mcp_error, map_error_to_code
from infuse.mcp.main import create_parser, main, run_server
from infuse.mcp.server import create_mcp_server

__all__ = [
    "create_mcp_server",
    "McpServerConfig",
    "format_mcp_error",
    "map_error_to_code",
    "create_parser",
    "run_server",
    "main",
]
