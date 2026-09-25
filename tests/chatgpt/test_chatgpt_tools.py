"""Tests for INFUSE ChatGPT App Tools and OpenAPI Schemas."""

import unittest
from starlette.testclient import TestClient

from infuse.chatgpt.config import AuthMode, ChatGptAppConfig
from infuse.chatgpt.models import (
    ControlExecutionInput,
    ExecuteTaskInput,
    GetExecutionInput,
    GetPolicyInput,
    ListExecutionsInput,
    ToolCategory,
)
from infuse.chatgpt.router import create_chatgpt_router
from infuse.chatgpt.schema import generate_openapi_schema
from infuse.chatgpt.tools import ChatGptToolRegistry
from infuse.contracts.governor import GovernorAction
from infuse.sdk.client import InfuseClient
from infuse.version import SCHEMA_VERSION, __version__


class TestChatGptTools(unittest.TestCase):
    """Test suite for ChatGPT curated tools and endpoint handlers."""

    def setUp(self) -> None:
        self.config = ChatGptAppConfig(
            auth_mode=AuthMode.BEARER,
            api_key_secret="infuse_test_key_123",
            public_url="https://api.infuse.adorbistech.com",
        )
        self.router = create_chatgpt_router(config=self.config)
        self.test_client = TestClient(self.router)
        self.auth_headers = {"Authorization": "Bearer infuse_test_key_123"}

    def test_01_openapi_schema_generation(self) -> None:
        """Verify OpenAPI 3.1.0 schema generated for ChatGPT Action manifest."""
        schema = generate_openapi_schema(server_url="https://api.infuse.adorbistech.com")
        self.assertEqual(schema["openapi"], "3.1.0")
        self.assertIn("/chatgpt/v1/system", schema["paths"])
        self.assertIn("/chatgpt/v1/executions", schema["paths"])
        self.assertIn("/chatgpt/v1/execute", schema["paths"])
        self.assertIn("/chatgpt/v1/control", schema["paths"])
        self.assertIn("BearerAuth", schema["components"]["securitySchemes"])

        # Check endpoint GET /openapi.json
        resp = self.test_client.get("/openapi.json")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["openapi"], "3.1.0")

    def test_02_get_system_info_tool(self) -> None:
        """Verify get_system_info returns sanitized version and capability metadata."""
        resp = self.test_client.get("/v1/system", headers=self.auth_headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["tool_name"], "get_system_info")
        self.assertEqual(data["category"], "READ")
        self.assertEqual(data["data"]["version"], __version__)
        self.assertEqual(data["data"]["schema_version"], SCHEMA_VERSION)
        self.assertIn("NORMAL", data["data"]["canonical_states"])
        self.assertIn("CONTINUE", data["data"]["canonical_actions"])

    def test_03_execute_task_tool(self) -> None:
        """Verify execute_task routes through the universal core and returns governed result."""
        payload = {
            "task_description": "Analyze repository architecture",
            "prompt": "Inspect codebase module boundaries",
            "workload_hint": "reasoning",
            "temperature": 0.1,
        }
        resp = self.test_client.post("/v1/execute", json=payload, headers=self.auth_headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["category"], "EXECUTE")
        self.assertIn("execution_id", data["data"])
        self.assertIn("decision", data["data"])
        self.assertEqual(data["data"]["decision"]["action"], "CONTINUE")
        self.assertIn("ui_card", data)

    def test_04_list_executions_tool(self) -> None:
        """Verify list_executions returns paginated execution summaries."""
        # First execute a task to ensure at least one execution exists
        self.test_client.post(
            "/v1/execute",
            json={"task_description": "Task for listing test"},
            headers=self.auth_headers,
        )

        resp = self.test_client.get("/v1/executions?limit=10", headers=self.auth_headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["category"], "READ")
        self.assertIn("executions", data["data"])
        self.assertIsInstance(data["data"]["executions"], list)

    def test_05_get_execution_state_and_result_tools(self) -> None:
        """Verify get_execution_state and get_execution_result on real execution."""
        exec_resp = self.test_client.post(
            "/v1/execute",
            json={"task_description": "State inspection task"},
            headers=self.auth_headers,
        )
        exec_id = exec_resp.json()["data"]["execution_id"]

        # Get state
        state_resp = self.test_client.get(f"/v1/executions/{exec_id}/state", headers=self.auth_headers)
        self.assertEqual(state_resp.status_code, 200)
        state_data = state_resp.json()
        self.assertTrue(state_data["success"])
        self.assertEqual(state_data["category"], "ANALYZE")
        self.assertIn("state", state_data["data"])

        # Get result
        result_resp = self.test_client.get(f"/v1/executions/{exec_id}/result", headers=self.auth_headers)
        self.assertEqual(result_resp.status_code, 200)
        res_data = result_resp.json()
        self.assertTrue(res_data["success"])
        self.assertEqual(res_data["category"], "READ")
        self.assertEqual(res_data["data"]["execution_id"], exec_id)

    def test_06_inspect_execution_and_governor_decision(self) -> None:
        """Verify inspect_execution and inspect_governor_decision return detailed analytics."""
        exec_resp = self.test_client.post(
            "/v1/execute",
            json={"task_description": "Governor analytics test"},
            headers=self.auth_headers,
        )
        exec_id = exec_resp.json()["data"]["execution_id"]

        # Inspect execution
        inspect_resp = self.test_client.get(f"/v1/executions/{exec_id}/inspect", headers=self.auth_headers)
        self.assertEqual(inspect_resp.status_code, 200)
        insp_data = inspect_resp.json()
        self.assertTrue(insp_data["success"])
        self.assertIn("analysis", insp_data["data"])
        self.assertIn("is_healthy", insp_data["data"]["analysis"])

        # Inspect governor decision
        gov_resp = self.test_client.get(f"/v1/executions/{exec_id}/governor", headers=self.auth_headers)
        self.assertEqual(gov_resp.status_code, 200)
        gov_data = gov_resp.json()
        self.assertTrue(gov_data["success"])
        self.assertIn("action", gov_data["data"])

    def test_07_provider_health_tool(self) -> None:
        """Verify get_provider_health returns provider status matrix."""
        resp = self.test_client.get("/v1/providers/health", headers=self.auth_headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["overall_state"], "HEALTHY")
        self.assertTrue(len(data["data"]["providers"]) >= 3)

    def test_08_policy_tools(self) -> None:
        """Verify list_policies and get_policy tools."""
        # List policies
        list_resp = self.test_client.get("/v1/policies", headers=self.auth_headers)
        self.assertEqual(list_resp.status_code, 200)
        data = list_resp.json()
        self.assertTrue(data["success"])

        # Get active policy
        active_resp = self.test_client.get("/v1/policies/pol_default", headers=self.auth_headers)
        self.assertEqual(active_resp.status_code, 200)
        pol_data = active_resp.json()
        self.assertTrue(pol_data["success"])

    def test_09_governed_control_tool(self) -> None:
        """Verify control_execution dispatches through Execution Control Boundary."""
        exec_resp = self.test_client.post(
            "/v1/execute",
            json={"task_description": "Control dispatch test"},
            headers=self.auth_headers,
        )
        exec_id = exec_resp.json()["data"]["execution_id"]

        control_payload = {
            "execution_id": exec_id,
            "action": "THROTTLE",
            "reason": "Test pacing from ChatGPT",
            "delay_ms": 250,
        }
        resp = self.test_client.post("/v1/control", json=control_payload, headers=self.auth_headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["category"], "CONTROL")
        self.assertIn(data["data"]["status"], ["APPLIED", "UNSUPPORTED", "IGNORED"])


if __name__ == "__main__":
    unittest.main()
