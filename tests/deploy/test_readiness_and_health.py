"""INFUSE Block 35 — Readiness & Health Probes Test Suite.

Verifies:
- SystemReadinessProbe evaluates subsystem readiness accurately
- Subsystem health state mapping (OK, DEGRADED, ERROR, UNREADY)
- Custom subsystem check registrations
- Uptime calculations
- Liveness and readiness contract integrity
"""

import time
import unittest
from infuse.api.services.default import (
    DefaultEventService,
    DefaultExecutionService,
    DefaultPolicyService,
)
from infuse.deployment.health import (
    ReadinessCheckResult,
    ReadinessStatus,
    SystemReadinessProbe,
)
from infuse.version import __version__, SCHEMA_VERSION


class TestReadinessAndHealth(unittest.TestCase):
    """Test suite for system readiness probes and operational health verification."""

    def setUp(self) -> None:
        self.exec_svc = DefaultExecutionService()
        self.event_svc = DefaultEventService()
        self.policy_svc = DefaultPolicyService()
        self.probe = SystemReadinessProbe(start_time=time.time() - 10.0)

    def test_01_probe_returns_ready_when_all_services_healthy(self) -> None:
        """Verify probe returns READY status when execution, event, and policy services are valid."""
        report = self.probe.evaluate_readiness(
            execution_service=self.exec_svc,
            event_service=self.event_svc,
            policy_service=self.policy_svc,
        )
        self.assertIsInstance(report, ReadinessCheckResult)
        self.assertEqual(report.status, ReadinessStatus.READY)
        self.assertEqual(report.checks.get("execution_service"), "OK")
        self.assertEqual(report.checks.get("event_service"), "OK")
        self.assertEqual(report.checks.get("policy_service"), "OK")
        self.assertGreaterEqual(report.uptime_seconds, 10.0)
        self.assertEqual(report.version, __version__)
        self.assertEqual(report.schema_version, SCHEMA_VERSION)

    def test_02_probe_flags_degraded_service(self) -> None:
        """Verify probe returns UNREADY status if a service lacks required interfaces."""
        class BrokenExecutionService:
            pass  # Missing execute and get_execution methods

        report = self.probe.evaluate_readiness(
            execution_service=BrokenExecutionService(),
            event_service=self.event_svc,
            policy_service=self.policy_svc,
        )
        self.assertEqual(report.status, ReadinessStatus.UNREADY)
        self.assertEqual(report.checks.get("execution_service"), "DEGRADED")

    def test_03_probe_catches_service_inspection_exceptions(self) -> None:
        """Verify probe safely catches exceptions during service inspection."""
        class ExplodingService:
            def __getattr__(self, name):
                raise RuntimeError("Service crashed on attribute lookup!")

        report = self.probe.evaluate_readiness(
            execution_service=ExplodingService(),
            event_service=self.event_svc,
            policy_service=self.policy_svc,
        )
        self.assertEqual(report.status, ReadinessStatus.UNREADY)
        self.assertEqual(report.checks.get("execution_service"), "ERROR")

    def test_04_probe_handles_custom_registered_check_passing(self) -> None:
        """Verify custom health check functions can be registered and evaluated."""
        self.probe.register_check("database_connection", lambda: True)
        report = self.probe.evaluate_readiness(
            execution_service=self.exec_svc,
            event_service=self.event_svc,
            policy_service=self.policy_svc,
        )
        self.assertEqual(report.status, ReadinessStatus.READY)
        self.assertEqual(report.checks.get("database_connection"), "OK")

    def test_05_probe_handles_custom_registered_check_failing(self) -> None:
        """Verify failing custom check causes UNREADY status."""
        self.probe.register_check("external_provider_reachability", lambda: False)
        report = self.probe.evaluate_readiness(
            execution_service=self.exec_svc,
            event_service=self.event_svc,
            policy_service=self.policy_svc,
        )
        self.assertEqual(report.status, ReadinessStatus.UNREADY)
        self.assertEqual(report.checks.get("external_provider_reachability"), "FAILED")

    def test_06_probe_handles_custom_check_raising_exception(self) -> None:
        """Verify custom check raising unhandled exception is safely recorded as ERROR."""
        def failing_check():
            raise ConnectionError("Network unreachable")

        self.probe.register_check("sidecar_socket", failing_check)
        report = self.probe.evaluate_readiness()
        self.assertEqual(report.status, ReadinessStatus.UNREADY)
        self.assertEqual(report.checks.get("sidecar_socket"), "ERROR")

    def test_07_probe_evaluates_without_services_gracefully(self) -> None:
        """Verify evaluate_readiness succeeds when called with None services."""
        report = self.probe.evaluate_readiness()
        self.assertEqual(report.status, ReadinessStatus.READY)
        self.assertEqual(report.checks.get("execution_service"), "OK")

    def test_08_readiness_report_contains_no_secrets_or_addresses(self) -> None:
        """Verify readiness report contains only safe strings and no memory pointers or tokens."""
        report = self.probe.evaluate_readiness(
            execution_service=self.exec_svc,
            event_service=self.event_svc,
            policy_service=self.policy_svc,
        )
        serialized = report.model_dump_json()
        self.assertNotIn("0x", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("sk-", serialized)


if __name__ == "__main__":
    unittest.main()
