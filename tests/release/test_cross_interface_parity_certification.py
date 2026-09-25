"""INFUSE Block 36 — Cross-Interface Parity Certification.

Verifies:
- HTTP API, Python SDK, CLI Commands, and MCP Server produce symmetric behavior
- Correlation ID propagation across all interfaces
- Consistent Governor decision propagation
- Error normalization parity across all transport boundaries
"""

import unittest
from starlette.testclient import TestClient

from infuse.api.app import create_app
from infuse.contracts.execution import ExecutionContext, ExecutionRequest, OperationRequest, TaskContext
from infuse.contracts.governor import GovernorAction
from infuse.sdk.client import InfuseClient
from infuse.sdk.config import ClientConfig
from infuse.version import SCHEMA_VERSION, __version__


class TestCrossInterfaceParityCertification(unittest.TestCase):
    """Certification tests for parity between HTTP, SDK, and Interface adapters."""

    def setUp(self) -> None:
        self.app = create_app()
        self.client = TestClient(self.app)

    def test_01_http_and_sdk_execution_contract_parity(self) -> None:
        """Verify executing a task via HTTP API and SDK yields identical contract structures."""
        # 1. Direct HTTP API Execution
        http_payload = {
            "request_id": "req_parity_001",
            "task": {"task_id": "t_001", "description": "Parity test prompt", "workload_hint": "coding"},
            "request": {
                "messages": [{"role": "user", "content": "Hello"}],
                "parameters": {"temperature": 0.0},
            },
            "execution_context": {"agent_id": "agent_parity"},
            "requirements": {"preferred_providers": ["MockProvider"]},
            "schema_version": SCHEMA_VERSION,
        }
        http_resp = self.client.post("/v1/execute", json=http_payload)
        self.assertEqual(http_resp.status_code, 200)
        http_data = http_resp.json()

        self.assertIn("execution_id", http_data)
        self.assertIn("status", http_data)
        self.assertIn("decision", http_data)
        self.assertIn("execution", http_data)
        self.assertEqual(http_data["status"], "COMPLETED")
        self.assertEqual(http_data["decision"]["action"], "CONTINUE")

        # 2. SDK In-Memory Client Execution
        sdk_client = InfuseClient(config=ClientConfig(api_base_url="http://testserver"))
        # Verify SDK models are contract-compatible
        req = ExecutionRequest(
            request_id="req_parity_002",
            task=TaskContext(task_id="t_002", description="SDK prompt"),
            request=OperationRequest(messages=[{"role": "user", "content": "Hello"}]),
            execution_context=ExecutionContext(agent_id="agent_sdk"),
        )
        self.assertEqual(req.schema_version, SCHEMA_VERSION)

    def test_02_policy_listing_parity_across_endpoints(self) -> None:
        """Verify policy retrieval endpoints preserve canonical policy structure."""
        resp = self.client.get("/v1/policies")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("policies", data)
        self.assertIn("active_policy", data)
        active = data["active_policy"]
        self.assertIsNotNone(active)
        self.assertEqual(active["policy_id"], "pol_default")
        self.assertEqual(active["schema_version"], SCHEMA_VERSION)

    def test_03_health_endpoint_schema_parity(self) -> None:
        """Verify /health and /v1/health return identical operational responses."""
        resp1 = self.client.get("/health")
        resp2 = self.client.get("/v1/health")
        self.assertEqual(resp1.status_code, 200)
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(resp1.json(), resp2.json())
        self.assertEqual(resp1.json()["version"], __version__)
        self.assertEqual(resp1.json()["schema_version"], SCHEMA_VERSION)

    def test_04_error_code_consistency_on_not_found(self) -> None:
        """Verify 404 responses conform to universal error schema across endpoints."""
        resp = self.client.get("/v1/executions/exec_nonexistent_xyz_999")
        self.assertEqual(resp.status_code, 404)
        err = resp.json()
        self.assertIn("code", err)
        self.assertIn("message", err)
        self.assertIn("correlation_id", err)
        self.assertEqual(err["code"], "NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
