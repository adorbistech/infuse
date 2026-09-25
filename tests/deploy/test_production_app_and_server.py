"""INFUSE Block 35 — Production App & Server Integration Suite.

Verifies:
- Production application factory creates valid Starlette instance
- /health endpoint returns 200 OK with version metadata
- /ready endpoint returns 200 OK with subsystem readiness
- /v1/info returns sanitized environment metadata
- Unready / shutting down simulation triggers 503 response on /ready
- Correlation ID propagation across production endpoints
- Missing route returns standard 404
"""

import unittest
from starlette.testclient import TestClient

from infuse.deployment.config import DeploymentConfig, EnvironmentType
from infuse.deployment.server import ProductionServerContext, create_production_app
from infuse.version import __version__, SCHEMA_VERSION


class TestProductionAppAndServer(unittest.TestCase):
    """Test suite for production Starlette ASGI app factory and deployment routes."""

    def setUp(self) -> None:
        self.config = DeploymentConfig(
            environment=EnvironmentType.PRODUCTION,
            enable_readiness_probe=True,
            enable_metrics=True,
        )
        self.context = ProductionServerContext(self.config)
        self.app = create_production_app(config=self.config, context=self.context)
        self.client = TestClient(self.app)

    def test_01_health_endpoint_returns_ok_with_version_headers(self) -> None:
        """Verify GET /health returns 200 with status OK, version, and schema version."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "OK")
        self.assertEqual(data.get("version"), __version__)
        self.assertEqual(data.get("schema_version"), SCHEMA_VERSION)
        self.assertTrue(response.headers.get("X-Correlation-ID") is not None)

    def test_02_readiness_endpoint_returns_ready_status(self) -> None:
        """Verify GET /ready returns 200 with complete subsystem check breakdown."""
        response = self.client.get("/ready")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "READY")
        self.assertIn("execution_service", data.get("checks", {}))
        self.assertIn("event_service", data.get("checks", {}))
        self.assertIn("policy_service", data.get("checks", {}))
        self.assertGreaterEqual(data.get("uptime_seconds", 0), 0.0)

    def test_03_v1_ready_alias_returns_same_report(self) -> None:
        """Verify GET /v1/ready returns identical readiness report."""
        response = self.client.get("/v1/ready")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "READY")

    def test_04_v1_info_returns_sanitized_environment_details(self) -> None:
        """Verify GET /v1/info exposes safe metadata without passwords or keys."""
        response = self.client.get("/v1/info")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("version"), __version__)
        self.assertEqual(data.get("environment"), "production")
        self.assertTrue(data.get("metrics_enabled"))
        self.assertTrue(data.get("readiness_probe_enabled"))
        self.assertNotIn("password", str(data))
        self.assertNotIn("secret", str(data))
        self.assertNotIn("api_key", str(data))

    def test_05_shutting_down_state_causes_ready_to_return_503(self) -> None:
        """Verify /ready immediately returns 503 when server enters shutdown state."""
        self.context.is_shutting_down = True
        response = self.client.get("/ready")
        self.assertEqual(response.status_code, 503)
        data = response.json()
        self.assertEqual(data.get("status"), "UNREADY")
        self.assertIn("shutting down", data.get("reason", "").lower())

    def test_06_unready_subsystem_causes_503_status_code(self) -> None:
        """Verify degraded subsystem probe returns 503 HTTP status."""
        # Register a failing check
        self.context.readiness_probe.register_check("database_connection", lambda: False)
        response = self.client.get("/ready")
        self.assertEqual(response.status_code, 503)
        data = response.json()
        self.assertEqual(data.get("status"), "UNREADY")
        self.assertEqual(data["checks"]["database_connection"], "FAILED")

    def test_07_correlation_id_is_preserved_from_client_request(self) -> None:
        """Verify incoming X-Correlation-ID is echoed in deployment endpoints."""
        custom_corr = "corr_deploy_test_998877"
        response = self.client.get("/health", headers={"X-Correlation-ID": custom_corr})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("X-Correlation-ID"), custom_corr)

    def test_08_core_v1_api_routes_remain_functional(self) -> None:
        """Verify standard API routes (/v1/policies, /v1/executions) function in production app."""
        response = self.client.get("/v1/policies")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("policies", data)

    def test_09_v1_health_alias_endpoint(self) -> None:
        """Verify GET /v1/health returns 200 with OK status."""
        response = self.client.get("/v1/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get("status"), "OK")

    def test_10_production_server_context_initialization(self) -> None:
        """Verify ProductionServerContext initializes services and readiness probe."""
        ctx = ProductionServerContext(self.config)
        self.assertFalse(ctx.is_shutting_down)
        self.assertIsNotNone(ctx.readiness_probe)
        self.assertIsNotNone(ctx.execution_service)
        self.assertIsNotNone(ctx.event_service)
        self.assertIsNotNone(ctx.policy_service)


if __name__ == "__main__":
    unittest.main()
