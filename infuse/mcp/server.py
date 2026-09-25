"""MCP Server factory and registration for INFUSE (Block 30).

Provides FastMCP server instantiation, SDK client binding, tool registration,
and resource registration.
"""

from typing import Optional
from mcp.server.fastmcp import FastMCP

from infuse.mcp.config import McpServerConfig
from infuse.mcp.resources import register_resources
from infuse.mcp.tools import register_tools
from infuse.sdk.client import InfuseClient


def create_mcp_server(
    client: Optional[InfuseClient] = None,
    config: Optional[McpServerConfig] = None,
) -> FastMCP:
    """Create and configure an authoritative INFUSE FastMCP server instance.

    Args:
        client: Injected InfuseClient instance (e.g. for testing with ReferenceTransport).
        config: Optional McpServerConfig for configuring server attributes.

    Returns:
        Configured FastMCP application instance.
    """
    server_cfg = config or McpServerConfig.from_env()

    # Instantiate SDK client if not provided
    if client is None:
        client = InfuseClient(config=server_cfg.to_client_config())

    mcp = FastMCP(
        name=server_cfg.name,
    )

    # Attach client and config to server context for introspection/testing
    mcp.client = client
    mcp.config = server_cfg

    # Register authoritative tools & resources
    register_tools(mcp=mcp, client=client)
    register_resources(mcp=mcp, client=client)

    return mcp


__all__ = ["create_mcp_server"]
