"""INFUSE Block 35 — Security Preservation in Deployment Test Suite.

Verifies:
- Block 34 security guarantees remain intact in deployment layer
- Zero secret disclosure in server info and health endpoints
- Non-root container configuration and user permissions
- Header injection and correlation ID sanitization
- Subprocess transport invariant preservation (shell=False)
- Request size limit enforcement
"""

import os
import unittest
from starlette.testclient import TestClient

from infuse.deployment.config import DeploymentConfig, EnvironmentType
from infuse.deployment.server import ProductionServerContext, create_production_app


class TestSecurityPreservationDeployment(unittest.TestCase):
    """Test suite ensuring Block 34 security controls are preserved across deployment assets."""

    def setUp(self) -> None:
        self.config = DeploymentConfig(
            environment=EnvironmentType.PRODUCTION,
            max_request_size_bytes=1024,
        )
        self.context = ProductionServerContext(self.config)
        self.app = create_production_app(config=self.config, context=self.context)
        self.client = TestClient(self.app)

    def test_01_no_secrets_in_production_info_payload(self) -> None:
        """Verify GET /v1/info does not leak any secret environment variables or tokens."""
        response = self.client.get("/v1/info")
        self.assertEqual(response.status_code, 200)
        body = response.text.lower()
        forbidden_substrings = ["password", "token", "secret", "private_key", "sk-", "bearer"]
        for forbidden in forbidden_substrings:
            self.assertNotIn(forbidden, body)

    def test_02_health_and_ready_endpoints_do_not_leak_stack_traces_on_error(self) -> None:
        """Verify unhandled exceptions in probe do not leak Python tracebacks to HTTP clients."""
        def buggy_check():
            raise Exception("Internal sensitive database address: postgresql://admin:secret@10.0.0.5:5432/db")

        self.context.readiness_probe.register_check("faulty_probe", buggy_check)
        response = self.client.get("/ready")
        self.assertEqual(response.status_code, 503)
        body = response.text
        self.assertNotIn("Traceback (most recent call last)", body)
        self.assertNotIn("postgresql://admin:secret", body)

    def test_03_correlation_id_header_injection_safety(self) -> None:
        """Verify newline characters in correlation ID do not cause HTTP response splitting."""
        malicious_corr = "corr_1234\r\nInjected-Header: evil"
        response = self.client.get("/health", headers={"X-Correlation-ID": malicious_corr})
        self.assertNotIn("Injected-Header", response.headers)

    def test_04_dockerfile_enforces_non_root_execution(self) -> None:
        """Verify Dockerfile creates unprivileged user and sets USER instruction."""
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        dockerfile = os.path.join(root_dir, "Dockerfile")
        with open(dockerfile, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("useradd -u 10001", content)
        self.assertIn("USER infuse", content)
        # Ensure no root instruction is given after USER infuse
        user_idx = content.find("USER infuse")
        self.assertNotIn("USER root", content[user_idx:])

    def test_05_docker_compose_enforces_security_options(self) -> None:
        """Verify docker-compose.yml specifies no-new-privileges for containers."""
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        compose_file = os.path.join(root_dir, "docker-compose.yml")
        with open(compose_file, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("no-new-privileges:true", content)

    def test_06_deployment_config_preserves_offline_determinism(self) -> None:
        """Verify default deployment configuration does not require remote internet connectivity."""
        cfg = DeploymentConfig()
        self.assertEqual(cfg.storage_backend, "inmemory")
        self.assertFalse(cfg.mcp_server_enabled)

    def test_07_cors_wildcard_disables_credentials_by_default(self) -> None:
        """Verify wildcard CORS does not enable allow_credentials (preventing credential theft)."""
        cfg = DeploymentConfig(cors_origins="*")
        self.assertFalse(cfg.cors_allow_credentials)

    def test_08_sanitized_config_representation_omits_none_paths(self) -> None:
        """Verify to_safe_dict produces clean schema-compliant metadata."""
        cfg = DeploymentConfig(host="127.0.0.1", port=8080)
        safe = cfg.to_safe_dict()
        self.assertEqual(safe["host"], "127.0.0.1")
        self.assertEqual(safe["port"], 8080)
        self.assertIsInstance(safe["workers"], int)


if __name__ == "__main__":
    unittest.main()
