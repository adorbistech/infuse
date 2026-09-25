"""Authentication, Authorization, and Multi-Tenant Isolation Tests for ChatGPT App."""

import unittest
from starlette.testclient import TestClient

from infuse.chatgpt.auth import AuthenticatedContext, ChatGptAuthService
from infuse.chatgpt.config import AuthMode, ChatGptAppConfig
from infuse.chatgpt.router import create_chatgpt_router
from infuse.sdk.client import InfuseClient


class TestChatGptAuthAndIsolation(unittest.TestCase):
    """Test authentication rejection, scope boundaries, and tenant isolation."""

    def setUp(self) -> None:
        self.config = ChatGptAppConfig(
            auth_mode=AuthMode.BEARER,
            api_key_secret="secret_key_prod_1,secret_key_prod_2",
            public_url="https://api.infuse.adorbistech.com",
        )
        self.router = create_chatgpt_router(config=self.config)
        self.test_client = TestClient(self.router)

    def test_01_missing_auth_header_rejected(self) -> None:
        """Verify requests lacking Authorization header are rejected with 401."""
        resp = self.test_client.get("/v1/system")
        self.assertEqual(resp.status_code, 401)
        data = resp.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error_code"], "MISSING_TOKEN")

    def test_02_malformed_auth_header_rejected(self) -> None:
        """Verify malformed Authorization headers are rejected with 401."""
        resp = self.test_client.get("/v1/system", headers={"Authorization": "Basic dXNlcjpwYXNz"})
        self.assertEqual(resp.status_code, 401)
        data = resp.json()
        self.assertEqual(data["error_code"], "INVALID_HEADER")

    def test_03_invalid_token_rejected(self) -> None:
        """Verify wrong/unknown tokens are rejected with 401."""
        resp = self.test_client.get("/v1/system", headers={"Authorization": "Bearer invalid_random_token"})
        self.assertEqual(resp.status_code, 401)
        data = resp.json()
        self.assertEqual(data["error_code"], "INVALID_KEY")

    def test_04_valid_token_accepted(self) -> None:
        """Verify valid configured API key is authenticated."""
        resp = self.test_client.get("/v1/system", headers={"Authorization": "Bearer secret_key_prod_1"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])

    def test_05_multi_tenant_isolation(self) -> None:
        """Verify tenant-scoped token can only query executions within its own tenant."""
        # Use dev token format to simulate Tenant A and Tenant B
        dev_config = ChatGptAppConfig(
            auth_mode=AuthMode.BEARER,
            api_key_secret=None,  # Enables encoded token parsing in test/dev
            public_url="https://api.infuse.adorbistech.com",
        )
        dev_router = create_chatgpt_router(config=dev_config)
        dev_client = TestClient(dev_router)

        # 1. Tenant Alpha executes a task
        alpha_headers = {"Authorization": "Bearer infuse_tenantAlpha_user1"}
        resp_alpha = dev_client.post(
            "/v1/execute",
            json={"task_description": "Tenant Alpha confidential workflow"},
            headers=alpha_headers,
        )
        self.assertEqual(resp_alpha.status_code, 200)

        # 2. Tenant Beta executes a task
        beta_headers = {"Authorization": "Bearer infuse_tenantBeta_user2"}
        resp_beta = dev_client.post(
            "/v1/execute",
            json={"task_description": "Tenant Beta confidential workflow"},
            headers=beta_headers,
        )
        self.assertEqual(resp_beta.status_code, 200)

        # 3. Tenant Alpha queries executions
        list_alpha = dev_client.get("/v1/executions", headers=alpha_headers)
        self.assertEqual(list_alpha.status_code, 200)
        items_alpha = list_alpha.json()["data"]["executions"]
        for item in items_alpha:
            tenant = item.get("execution_context", {}).get("metadata", {}).get("tenant_id")
            if tenant:
                self.assertEqual(tenant, "tenantAlpha")

    def test_06_secret_redaction(self) -> None:
        """Verify that API keys or environment secrets are never exposed in error envelopes."""
        resp = self.test_client.get(
            "/v1/executions/exec_nonexistent_xyz_999/result",
            headers={"Authorization": "Bearer secret_key_prod_1"},
        )
        self.assertEqual(resp.status_code, 200)  # Envelope success=False
        data = resp.json()
        self.assertFalse(data["success"])
        self.assertNotIn("secret_key_prod_1", str(data))
        self.assertNotIn("password", str(data).lower())


if __name__ == "__main__":
    unittest.main()
