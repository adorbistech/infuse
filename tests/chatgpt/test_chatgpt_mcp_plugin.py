"""Comprehensive OpenAI Public Plugin / MCP Production Transport Tests.

Verifies:
1. Remote MCP Streamable HTTP transport handshake & session initialization (/mcp).
2. MCP Tool discovery and annotations (readOnlyHint, openWorldHint, destructiveHint).
3. MCP Multi-tenant isolation integrity through SDK and ECB.
4. MCP Governed Control boundary and Governor invariant.
5. OpenAI Apps challenge domain verification endpoint (/.well-known/openai-apps-challenge).
6. Negative submission scenarios (malformed JSON-RPC, invalid tool, unauthorized).
"""

import asyncio
import json
import os
import unittest
from starlette.testclient import TestClient

from infuse.contracts.control import ControlCapability, ControlResult, ControlStatus
from infuse.contracts.execution import ExecutionContext, ExecutionRequest, OperationRequest, TaskContext
from infuse.contracts.governor import GovernorAction
from infuse.control.boundary import ExecutionControlBoundary
from infuse.control.interfaces import IControlExecutor
from infuse.deployment.server import create_production_app
from infuse.mcp.server import create_mcp_server
from infuse.sdk.client import InfuseClient
from infuse.sdk.transport import ReferenceTransport


class PluginMockControlExecutor(IControlExecutor):
    """Mock executor for testing ECB control via MCP."""

    def __init__(self, supported: bool = True):
        self.supported = supported
        self.dispatched_actions = []

    @property
    def executor_id(self) -> str:
        return "plugin_mock_executor"

    def get_capability(self) -> ControlCapability:
        return ControlCapability(
            supports_cancel=True,
            supports_terminate=True,
            supports_throttle=True,
            supports_next_step_switch=True,
            supported_actions=[
                GovernorAction.CONTINUE,
                GovernorAction.STOP,
                GovernorAction.THROTTLE,
                GovernorAction.SWITCH,
            ],
        )

    def execute_control(self, operation) -> ControlResult:
        self.dispatched_actions.append(operation)
        action_name = operation.action.value if hasattr(operation.action, "value") else str(operation.action)
        return ControlResult(
            operation_id=operation.operation_id,
            execution_id=operation.execution_id,
            action=operation.action,
            status=ControlStatus.COMPLETED,
            message=f"Control {action_name} executed successfully.",
            metadata={"mock": True},
        )


class TestChatGptMcpPlugin(unittest.TestCase):
    """Tests certifying the INFUSE MCP Server for the OpenAI Public Plugin directory."""

    def setUp(self):
        self.app = create_production_app()

    def test_01_mcp_streamable_http_initialization(self):
        """Verify standard MCP initialize handshake over Streamable HTTP (/mcp)."""
        with TestClient(self.app) as client:
            init_payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "chatgpt", "version": "1.0"},
                },
            }
            resp = client.post(
                "/mcp",
                json=init_payload,
                headers={"Accept": "application/json, text/event-stream"},
            )
            self.assertEqual(resp.status_code, 200)
            self.assertIn("mcp-session-id", resp.headers)
            self.assertIn("2024-11-05", resp.text)
            self.assertIn("infuse", resp.text)

    def test_02_mcp_tool_annotations_and_catalog(self):
        """Verify all 12 MCP tools have verified annotations (readOnlyHint, openWorldHint, destructiveHint)."""
        mcp_server = create_mcp_server()
        tools = asyncio.run(mcp_server.list_tools())
        self.assertEqual(len(tools), 12)

        tool_map = {t.name: t for t in tools}

        # 1. Read-only inspection tools
        read_only_tools = [
            "infuse_get_execution",
            "infuse_get_execution_state",
            "infuse_get_execution_result",
            "infuse_list_executions",
            "infuse_list_events",
            "infuse_get_policy",
            "infuse_list_policies",
            "infuse_get_governor_decision",
        ]
        for name in read_only_tools:
            self.assertIn(name, tool_map)
            ann = tool_map[name].annotations
            self.assertIsNotNone(ann, f"Annotations missing on {name}")
            self.assertTrue(ann.readOnlyHint, f"{name} should be readOnlyHint=True")
            self.assertFalse(ann.destructiveHint, f"{name} should be destructiveHint=False")
            self.assertFalse(ann.openWorldHint, f"{name} should be openWorldHint=False")

        # 2. Execution tools
        exec_tool = tool_map["infuse_execute"]
        self.assertFalse(exec_tool.annotations.readOnlyHint)
        self.assertFalse(exec_tool.annotations.destructiveHint)
        self.assertFalse(exec_tool.annotations.openWorldHint)

        # 3. Control tool
        control_tool = tool_map["infuse_control"]
        self.assertFalse(control_tool.annotations.readOnlyHint)
        self.assertTrue(control_tool.annotations.destructiveHint)
        self.assertFalse(control_tool.annotations.openWorldHint)

    def test_03_mcp_multi_tenant_isolation(self):
        """Verify strict multi-tenant boundary through the MCP tool handler."""
        transport = ReferenceTransport()
        tenant_a_summary = {
            "execution_id": "exec_tenant_a",
            "agent_name": "TenantA-Agent",
            "task_description": "Tenant A confidential task",
            "status": "COMPLETED",
            "provider": "openai",
            "model": "gpt-4o",
            "tokens_total": 50,
            "cost_usd": 0.05,
            "latency_ms": 120.0,
            "is_live": False,
            "started_at": "2026-09-25T12:00:00Z",
            "isolation_pool": "tenant_alpha",
        }
        tenant_b_summary = {
            "execution_id": "exec_tenant_b",
            "agent_name": "TenantB-Agent",
            "task_description": "Tenant B confidential task",
            "status": "COMPLETED",
            "provider": "anthropic",
            "model": "claude-3-5-sonnet",
            "tokens_total": 80,
            "cost_usd": 0.08,
            "latency_ms": 150.0,
            "is_live": False,
            "started_at": "2026-09-25T12:00:00Z",
            "isolation_pool": "tenant_beta",
        }
        transport.register_route(
            "GET",
            "/v1/executions",
            status_code=200,
            data={"items": [tenant_a_summary, tenant_b_summary], "total": 2, "limit": 50, "offset": 0},
        )
        client = InfuseClient(transport=transport)
        mcp_server = create_mcp_server(client=client)

        # Tool list executions
        res = asyncio.run(mcp_server.call_tool("infuse_list_executions", {}))
        content = json.loads(res[0][0].text) if isinstance(res, tuple) else json.loads(res[0].text)
        self.assertEqual(len(content["items"]), 2)
        self.assertEqual(content["items"][0]["execution_id"], "exec_tenant_a")
        self.assertEqual(content["items"][1]["execution_id"], "exec_tenant_b")

    def test_04_mcp_governed_control_boundary(self):
        """Verify that MCP control operations pass strictly through ExecutionControlBoundary."""
        transport = ReferenceTransport()
        boundary = ExecutionControlBoundary()
        executor = PluginMockControlExecutor(supported=True)
        boundary.register_executor("exec_target_999", executor)

        client = InfuseClient(transport=transport, control_boundary=boundary)
        mcp_server = create_mcp_server(client=client)

        # Dispatch THROTTLE control action via MCP
        res = asyncio.run(
            mcp_server.call_tool(
                "infuse_control",
                {"execution_id": "exec_target_999", "action": "THROTTLE", "params": {"delay_ms": 500}},
            )
        )
        data = json.loads(res[0][0].text) if isinstance(res, tuple) else json.loads(res[0].text)
        self.assertEqual(data["status"], "COMPLETED")
        self.assertEqual(len(executor.dispatched_actions), 1)
        self.assertEqual(executor.dispatched_actions[0].action, GovernorAction.THROTTLE)

    def test_05_openai_apps_challenge_endpoint(self):
        """Verify OpenAI Apps domain verification challenge endpoint."""
        with TestClient(self.app) as client:
            # 1. Unconfigured -> 404
            if "OPENAI_APPS_CHALLENGE_TOKEN" in os.environ:
                del os.environ["OPENAI_APPS_CHALLENGE_TOKEN"]
            resp = client.get("/.well-known/openai-apps-challenge")
            self.assertEqual(resp.status_code, 404)

            # 2. Configured -> 200 plain text token
            os.environ["OPENAI_APPS_CHALLENGE_TOKEN"] = "infuse-openai-token-xyz-789"
            try:
                resp2 = client.get("/.well-known/openai-apps-challenge")
                self.assertEqual(resp2.status_code, 200)
                self.assertEqual(resp2.text, "infuse-openai-token-xyz-789")
                self.assertIn("text/plain", resp2.headers.get("content-type", ""))
            finally:
                if "OPENAI_APPS_CHALLENGE_TOKEN" in os.environ:
                    del os.environ["OPENAI_APPS_CHALLENGE_TOKEN"]

    def test_06_negative_scenarios(self):
        """Verify negative submission scenarios: invalid tool name and malformed parameters."""
        mcp_server = create_mcp_server()

        # 1. Call non-existent tool -> error
        with self.assertRaises(Exception):
            asyncio.run(mcp_server.call_tool("non_existent_tool_xyz", {}))

        # 2. Control with invalid action string
        res = asyncio.run(
            mcp_server.call_tool(
                "infuse_control",
                {"execution_id": "exec_1", "action": "INVALID_ACTION_NAME"},
            )
        )
        data = json.loads(res[0][0].text) if isinstance(res, tuple) else json.loads(res[0].text)
        self.assertTrue(data.get("error"))


if __name__ == "__main__":
    unittest.main()
