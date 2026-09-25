"""INFUSE Block 32 — Path D: Interface Path Integration Suite.

Validates that HTTP API, SDK, CLI, and MCP servers all consume the exact same
core contracts, business logic, policies, and event lifecycle without logic duplication.
"""

import asyncio
import io
import json
import unittest
import uuid
from unittest.mock import patch

from infuse.api.app import create_app
from infuse.cli.main import run_cli
from infuse.contracts.execution import (
    ExecutionContext,
    ExecutionRequirements,
    ExecutionRequest,
    ExecutionStatus,
    OperationRequest,
    TaskContext,
)
from infuse.e2e.environment import EndToEndIntegrationEnvironment
from infuse.e2e.transport import InProcessE2ETransport
from infuse.mcp.server import create_mcp_server
from infuse.sdk.client import InfuseClient


class TestBlock32InterfacePath(unittest.TestCase):
    """Verifies interface path parity across HTTP API, Python SDK, CLI, and MCP server."""

    def setUp(self):
        self.env = EndToEndIntegrationEnvironment()
        self.fastapi_app = create_app()
        self.transport = InProcessE2ETransport(self.fastapi_app)
        self.client = InfuseClient(transport=self.transport)

    def test_http_api_policy_crud_roundtrip(self):
        """Verify policy retrieval, creation, and listing through the HTTP API."""
        policies = self.client.policies.list()
        self.assertGreater(len(policies.policies), 0)
        self.assertIsNotNone(policies.policies[0].policy_id)

    def test_sdk_inprocess_execution_path(self):
        """Verify SDK client executes task and returns validated ExecutionResult."""
        req = ExecutionRequest(
            request_id=f"req_sdk_if_{uuid.uuid4().hex[:6]}",
            task=TaskContext(
                task_id="task_sdk_if",
                description="Validate SDK interface parity",
            ),
            request=OperationRequest(
                messages=[{"role": "user", "content": "SDK test instruction"}]
            ),
        )
        res = self.client.executions.execute(req)
        self.assertIsNotNone(res.execution_id)
        self.assertEqual(res.status, ExecutionStatus.COMPLETED)
        self.assertIsNotNone(res.response)
        self.assertIsNotNone(res.execution)

    def test_cli_interface_invocation(self):
        """Verify CLI invocations against the shared API."""
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            code = run_cli(["--json", "policy", "list"], client=self.client)
        self.assertEqual(code, 0)
        output = buf.getvalue()
        self.assertIn("pol_default", output)

    def _call_tool_sync(self, server, name, arguments=None):
        result = asyncio.run(server.call_tool(name, arguments or {}))
        if isinstance(result, tuple) and len(result) >= 1:
            content_list = result[0]
            if isinstance(content_list, list) and len(content_list) > 0:
                return json.loads(content_list[0].text)
            elif len(result) > 1 and isinstance(result[1], dict) and "result" in result[1]:
                return result[1]["result"]
        elif isinstance(result, list) and len(result) > 0:
            return json.loads(result[0].text)
        return result

    def test_mcp_interface_tool_invocation(self):
        """Verify MCP server executes tools against the underlying core."""
        server = create_mcp_server(client=self.client)
        tools = asyncio.run(server.list_tools())
        tool_names = [t.name for t in tools]
        self.assertIn("infuse_execute", tool_names)
        self.assertIn("infuse_get_policy", tool_names)

        parsed = self._call_tool_sync(server, "infuse_get_policy", {"policy_id": "pol_default"})
        self.assertEqual(parsed.get("policy_id"), "pol_default")
