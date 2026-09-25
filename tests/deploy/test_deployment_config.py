"""INFUSE Block 35 — Deployment Configuration Test Suite.

Verifies:
- Default deployment configuration parameters
- Environment variable parsing and type coercion
- Bounds checking and validation on port, workers, timeouts, and request sizes
- Safe serialization without secret leakage
"""

import unittest
from infuse.deployment.config import (
    DeploymentConfig,
    EnvironmentType,
    LogLevel,
    load_deployment_config,
)


class TestDeploymentConfig(unittest.TestCase):
    """Test suite for deployment configuration parsing, defaults, and validation."""

    def test_01_default_configuration_values(self) -> None:
        """Verify default deployment configuration parameters adhere to production standards."""
        config = DeploymentConfig()
        self.assertEqual(config.host, "0.0.0.0")
        self.assertEqual(config.port, 8000)
        self.assertEqual(config.environment, EnvironmentType.PRODUCTION)
        self.assertEqual(config.log_level, LogLevel.INFO)
        self.assertEqual(config.workers, 1)
        self.assertEqual(config.graceful_shutdown_timeout_sec, 15.0)
        self.assertEqual(config.max_request_size_bytes, 10_485_760)
        self.assertEqual(config.cors_origins, ["*"])
        self.assertFalse(config.cors_allow_credentials)
        self.assertTrue(config.enable_metrics)
        self.assertTrue(config.enable_readiness_probe)
        self.assertFalse(config.mcp_server_enabled)
        self.assertEqual(config.mcp_server_port, 8001)
        self.assertEqual(config.storage_backend, "inmemory")
        self.assertIsNone(config.storage_path)

    def test_02_load_deployment_config_from_custom_env_dict(self) -> None:
        """Verify load_deployment_config accurately parses explicit environment variables."""
        custom_env = {
            "INFUSE_HOST": "127.0.0.1",
            "INFUSE_PORT": "9000",
            "INFUSE_ENVIRONMENT": "staging",
            "INFUSE_LOG_LEVEL": "DEBUG",
            "INFUSE_WORKERS": "4",
            "INFUSE_SHUTDOWN_TIMEOUT_SEC": "30.5",
            "INFUSE_MAX_REQUEST_SIZE_BYTES": "20971520",
            "INFUSE_CORS_ORIGINS": "http://localhost:3000, https://app.example.com",
            "INFUSE_ENABLE_METRICS": "false",
            "INFUSE_ENABLE_READINESS_PROBE": "true",
            "INFUSE_MCP_SERVER_ENABLED": "true",
            "INFUSE_MCP_SERVER_PORT": "9001",
            "INFUSE_STORAGE_BACKEND": "filesystem",
            "INFUSE_STORAGE_PATH": "/var/lib/infuse/data",
        }
        config = load_deployment_config(custom_env)
        self.assertEqual(config.host, "127.0.0.1")
        self.assertEqual(config.port, 9000)
        self.assertEqual(config.environment, EnvironmentType.STAGING)
        self.assertEqual(config.log_level, LogLevel.DEBUG)
        self.assertEqual(config.workers, 4)
        self.assertEqual(config.graceful_shutdown_timeout_sec, 30.5)
        self.assertEqual(config.max_request_size_bytes, 20971520)
        self.assertEqual(config.cors_origins, ["http://localhost:3000", "https://app.example.com"])
        self.assertFalse(config.enable_metrics)
        self.assertTrue(config.enable_readiness_probe)
        self.assertTrue(config.mcp_server_enabled)
        self.assertEqual(config.mcp_server_port, 9001)
        self.assertEqual(config.storage_backend, "filesystem")
        self.assertEqual(config.storage_path, "/var/lib/infuse/data")

    def test_03_invalid_port_raises_validation_error(self) -> None:
        """Verify invalid or out-of-range port numbers raise clear exceptions."""
        with self.assertRaises(Exception):
            load_deployment_config({"INFUSE_PORT": "not_a_number"})

        with self.assertRaises(Exception):
            load_deployment_config({"INFUSE_PORT": "70000"})

        with self.assertRaises(Exception):
            load_deployment_config({"INFUSE_PORT": "0"})

    def test_04_invalid_environment_raises_validation_error(self) -> None:
        """Verify unapproved environment names raise ValueError."""
        with self.assertRaises(ValueError):
            load_deployment_config({"INFUSE_ENVIRONMENT": "quantum_space"})

    def test_05_invalid_log_level_raises_validation_error(self) -> None:
        """Verify unapproved log levels raise ValueError."""
        with self.assertRaises(ValueError):
            load_deployment_config({"INFUSE_LOG_LEVEL": "SUPER_VERBOSE"})

    def test_06_invalid_workers_and_timeout_raise_validation_error(self) -> None:
        """Verify negative or non-numeric worker count and timeout raise errors."""
        with self.assertRaises(Exception):
            load_deployment_config({"INFUSE_WORKERS": "0"})

        with self.assertRaises(Exception):
            load_deployment_config({"INFUSE_WORKERS": "-5"})

        with self.assertRaises(Exception):
            load_deployment_config({"INFUSE_SHUTDOWN_TIMEOUT_SEC": "-1.0"})

    def test_07_empty_host_rejected(self) -> None:
        """Verify blank host strings fail validation."""
        with self.assertRaises(Exception):
            DeploymentConfig(host="   ")

    def test_08_cors_origins_normalization(self) -> None:
        """Verify various CORS origins formats (string, list, wildcard) normalize properly."""
        cfg1 = DeploymentConfig(cors_origins="*")
        self.assertEqual(cfg1.cors_origins, ["*"])

        cfg2 = DeploymentConfig(cors_origins="https://alpha.com, https://beta.com")
        self.assertEqual(cfg2.cors_origins, ["https://alpha.com", "https://beta.com"])

        cfg3 = DeploymentConfig(cors_origins=["https://gamma.com", "https://delta.com"])
        self.assertEqual(cfg3.cors_origins, ["https://gamma.com", "https://delta.com"])

    def test_09_to_safe_dict_serializes_cleanly(self) -> None:
        """Verify to_safe_dict returns clean string representations for enums and zero secret fields."""
        config = DeploymentConfig(environment=EnvironmentType.DEVELOPMENT, log_level=LogLevel.WARNING)
        safe = config.to_safe_dict()
        self.assertEqual(safe["environment"], "development")
        self.assertEqual(safe["log_level"], "WARNING")
        self.assertIn("host", safe)
        self.assertIn("port", safe)
        # Ensure no credential key exists
        self.assertNotIn("api_key", safe)
        self.assertNotIn("password", safe)
        self.assertNotIn("token", safe)

    def test_10_support_for_infuse_env_alias(self) -> None:
        """Verify INFUSE_ENV works as an alias for INFUSE_ENVIRONMENT."""
        config = load_deployment_config({"INFUSE_ENV": "development"})
        self.assertEqual(config.environment, EnvironmentType.DEVELOPMENT)

    def test_11_max_request_size_validation(self) -> None:
        """Verify max request size validation rejects zero or negative limits."""
        with self.assertRaises(Exception):
            DeploymentConfig(max_request_size_bytes=100)  # ge=1024

    def test_12_mcp_port_validation(self) -> None:
        """Verify MCP server port bounds validation."""
        with self.assertRaises(Exception):
            DeploymentConfig(mcp_server_port=999999)


if __name__ == "__main__":
    unittest.main()
