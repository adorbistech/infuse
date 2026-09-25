"""MCP Resource handlers and registration for INFUSE (Block 30).

Provides read-only contextual URI resources adhering to the Model Context Protocol.
All data is retrieved strictly through the Block 28 SDK.
"""

import json
from mcp.server.fastmcp import FastMCP

from infuse.sdk.client import InfuseClient


def register_resources(mcp: FastMCP, client: InfuseClient) -> None:
    """Register all read-only contextual MCP resources on the FastMCP instance."""

    # 1. infuse://executions/{execution_id}
    @mcp.resource("infuse://executions/{execution_id}")
    def execution_resource(execution_id: str) -> str:
        """Read-only execution summary telemetry resource."""
        try:
            summary = client.executions.get(execution_id)
            return json.dumps(summary.model_dump(), indent=2, default=str)
        except Exception as exc:
            return json.dumps({"error": True, "message": str(exc)}, indent=2)

    # 2. infuse://executions/{execution_id}/state
    @mcp.resource("infuse://executions/{execution_id}/state")
    def execution_state_resource(execution_id: str) -> str:
        """Read-only execution state snapshot resource."""
        try:
            state_info = client.executions.get_state(execution_id)
            return json.dumps(state_info.model_dump(), indent=2, default=str)
        except Exception as exc:
            return json.dumps({"error": True, "message": str(exc)}, indent=2)

    # 3. infuse://executions/{execution_id}/result
    @mcp.resource("infuse://executions/{execution_id}/result")
    def execution_result_resource(execution_id: str) -> str:
        """Read-only full execution result resource."""
        try:
            result = client.executions.get(execution_id)
            return json.dumps(result.model_dump(), indent=2, default=str)
        except Exception as exc:
            return json.dumps({"error": True, "message": str(exc)}, indent=2)

    # 4. infuse://policies/active
    @mcp.resource("infuse://policies/active")
    def active_policy_resource() -> str:
        """Read-only currently active governance policy resource."""
        try:
            policy = client.policies.get_active()
            if not policy:
                return json.dumps({"error": True, "message": "No active policy found"}, indent=2)
            return json.dumps(policy.model_dump(), indent=2, default=str)
        except Exception as exc:
            return json.dumps({"error": True, "message": str(exc)}, indent=2)

    # 5. infuse://governor/{execution_id}
    @mcp.resource("infuse://governor/{execution_id}")
    def governor_decision_resource(execution_id: str) -> str:
        """Read-only Governor decision posture resource."""
        try:
            decision = client.governor.get_decision(execution_id)
            return json.dumps(decision.model_dump(), indent=2, default=str)
        except Exception as exc:
            return json.dumps({"error": True, "message": str(exc)}, indent=2)


__all__ = ["register_resources"]
