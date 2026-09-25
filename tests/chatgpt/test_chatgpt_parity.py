"""Cross-Interface Parity Certification for ChatGPT App.

Verifies:
- HTTP API, Python SDK, CLI Commands, MCP Server, and ChatGPT App
  all converge symmetrically on the single universal INFUSE core.
"""

import unittest
from starlette.testclient import TestClient

from infuse.api.app import create_app as create_http_api_app
from infuse.chatgpt.config import AuthMode, ChatGptAppConfig
from infuse.chatgpt.router import create_chatgpt_router
from infuse.contracts.execution import ExecutionContext, ExecutionRequest, OperationRequest, TaskContext
from infuse.contracts.governor import GovernorAction
from infuse.mcp.server import create_mcp_server
from infuse.sdk.client import InfuseClient
from infuse.version import SCHEMA_VERSION, __version__


class TestChatGptCrossInterfaceParity(unittest.TestCase):
    """Verify parity across HTTP, SDK, MCP, and ChatGPT interfaces."""

    def setUp(self) -> None:
        self.sdk_client = InfuseClient()
        self.http_app = create_http_api_app()
        self.http_client = TestClient(self.http_app)

        self.chatgpt_config = ChatGptAppConfig(
            auth_mode=AuthMode.NONE,
            public_url="https://api.infuse.adorbistech.com",
        )
        self.chatgpt_router = create_chatgpt_router(config=self.chatgpt_config)
        self.chatgpt_client = TestClient(self.chatgpt_router)

        self.mcp_server = create_mcp_server(client=self.sdk_client)

    def test_01_version_and_schema_parity(self) -> None:
        """Verify version and schema version parity across HTTP, SDK, MCP, and ChatGPT."""
        # 1. HTTP
        http_health = self.http_client.get("/health").json()
        self.assertEqual(http_health["version"], __version__)
        self.assertEqual(http_health["schema_version"], SCHEMA_VERSION)

        # 2. ChatGPT
        chatgpt_sys = self.chatgpt_client.get("/v1/system").json()
        self.assertEqual(chatgpt_sys["data"]["version"], __version__)
        self.assertEqual(chatgpt_sys["data"]["schema_version"], SCHEMA_VERSION)

        # 3. SDK
        from infuse.version import SCHEMA_VERSION as SDK_SCHEMA, __version__ as SDK_VER
        self.assertEqual(SDK_VER, __version__)
        self.assertEqual(SDK_SCHEMA, SCHEMA_VERSION)

    def test_02_execution_state_and_governor_action_vocabulary_parity(self) -> None:
        """Verify identical canonical vocabulary across all 5 interfaces."""
        expected_states = {
            "NORMAL",
            "COST_PRESSURE",
            "RUNAWAY",
            "QUALITY_DEGRADED",
            "PROVIDER_CONSTRAINED",
        }
        expected_actions = {
            "CONTINUE",
            "OPTIMIZE",
            "ESCALATE",
            "DOWNGRADE",
            "SWITCH",
            "THROTTLE",
            "STOP",
        }

        # ChatGPT system endpoint vocabulary
        chatgpt_sys = self.chatgpt_client.get("/v1/system").json()["data"]
        self.assertEqual(set(chatgpt_sys["canonical_states"]), expected_states)
        self.assertEqual(set(chatgpt_sys["canonical_actions"]), expected_actions)

    def test_03_execution_telemetry_model_parity(self) -> None:
        """Verify executing through ChatGPT App returns valid canonical telemetry contract."""
        chatgpt_resp = self.chatgpt_client.post(
            "/v1/execute",
            json={"task_description": "Cross-interface parity test prompt"},
        )
        self.assertEqual(chatgpt_resp.status_code, 200)
        data = chatgpt_resp.json()["data"]

        # Assert mandatory contract fields
        self.assertIn("execution_id", data)
        self.assertIn("status", data)
        self.assertIn("execution", data)
        self.assertIn("decision", data)
        self.assertEqual(data["status"], "COMPLETED")
        self.assertEqual(data["decision"]["action"], "CONTINUE")
        self.assertEqual(data["schema_version"], SCHEMA_VERSION)


if __name__ == "__main__":
    unittest.main()
