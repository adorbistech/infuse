"""INFUSE Block 34 — Universal HTTP API Boundary Security Suite.

Validates that:
- Malformed JSON payloads return clean 400 errors without crashing the server
- Schema validation rejections return structured 400/422 responses
- Invalid/traversal IDs in URL paths are safely rejected or handled
- Unhandled server exceptions never leak stack traces to the client
- Correlation IDs are sanitized and propagated in response headers
"""

import json
import unittest
from starlette.testclient import TestClient

from infuse.api.app import create_app
from infuse.api.services.interfaces import IExecutionService


class TestApiBoundarySecurity(unittest.TestCase):
    """Verifies security controls and error boundaries at the Universal HTTP API layer."""

    def setUp(self) -> None:
        self.app = create_app()
        self.client = TestClient(self.app, raise_server_exceptions=False)

    def test_01_malformed_json_request_body_returns_400(self) -> None:
        """Verify unparseable JSON payload returns 400 Bad Request with structured error."""
        response = self.client.post(
            "/v1/execute",
            content="{ invalid_json: [ unclosed ",
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data.get("code"), "MALFORMED_JSON")
        self.assertNotIn("Traceback", response.text)

    def test_02_empty_post_body_safety(self) -> None:
        """Verify empty POST body to /v1/execute returns 400 cleanly."""
        response = self.client.post(
            "/v1/execute",
            content="",
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("Traceback", response.text)

    def test_03_invalid_schema_missing_required_fields(self) -> None:
        """Verify payload missing required execution request fields returns 400/422 error."""
        response = self.client.post(
            "/v1/execute",
            json={"unexpected_field": "val"},
        )
        self.assertIn(response.status_code, [400, 422])
        data = response.json()
        self.assertEqual(data.get("code"), "VALIDATION_ERROR")
        self.assertNotIn("Traceback", response.text)

    def test_04_path_traversal_execution_id_safety(self) -> None:
        """Verify path traversal sequences in execution ID (/v1/executions/../../../etc/passwd) fail safely."""
        response = self.client.get("/v1/executions/..%2F..%2Fetc%2Fpasswd")
        self.assertIn(response.status_code, [400, 404])
        self.assertNotIn("root:", response.text)
        self.assertNotIn("Traceback", response.text)

    def test_05_nonexistent_execution_id_returns_404(self) -> None:
        """Verify querying non-existent execution returns 404 without internal error."""
        response = self.client.get("/v1/executions/exec_nonexistent_phantom_9999")
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertEqual(data.get("code"), "NOT_FOUND")

    def test_06_event_ingestion_for_nonexistent_execution_returns_404(self) -> None:
        """Verify ingesting events into unknown execution returns 404 Not Found."""
        from datetime import datetime, timezone
        from infuse.contracts.events import EventType
        event_payload = {
            "event_id": "evt_test",
            "execution_id": "exec_unknown_9999",
            "type": EventType.TOKEN_OBSERVED.value,
            "source": "PROVIDER",
            "sequence": 1,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {"total_tokens": 50},
        }
        response = self.client.post("/v1/executions/exec_unknown_9999/events", json=event_payload)
        self.assertEqual(response.status_code, 404)

    def test_07_unhandled_exception_does_not_leak_stack_trace(self) -> None:
        """Verify middleware catches unhandled exceptions and hides internal stack traces."""
        # Create a broken app service that throws an unhandled RuntimeError
        class BrokenExecutionService(IExecutionService):
            def execute(self, request, correlation_id=None):
                raise RuntimeError("Critical internal database connection password=SecretDBPass failed!")
            def get_execution(self, execution_id, correlation_id=None):
                pass
            def list_executions(self, filter_params=None, limit=50, offset=0, correlation_id=None):
                pass

        broken_app = create_app(execution_service=BrokenExecutionService())
        broken_client = TestClient(broken_app, raise_server_exceptions=False)

        valid_request_dto = {
            "request_id": "req_sec_break_1",
            "task": {
                "task_id": "task_1",
                "description": "test",
                "policy_id": "pol_default",
            },
            "context": {
                "context_id": "ctx_1",
                "variables": {},
            },
            "request": {
                "messages": [{"role": "user", "content": "hello"}],
            },
        }

        response = broken_client.post("/v1/execute", json=valid_request_dto)
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertEqual(data.get("code"), "INTERNAL_ERROR")
        # Ensure secret and stack trace are NOT leaked
        self.assertNotIn("SecretDBPass", response.text)
        self.assertNotIn("Traceback", response.text)
        self.assertNotIn("BrokenExecutionService", response.text)

    def test_08_correlation_id_middleware_propagation(self) -> None:
        """Verify correlation identifier is sanitized and returned in response headers."""
        custom_corr_id = "corr_secure_trace_12345"
        response = self.client.get("/health", headers={"X-Correlation-ID": custom_corr_id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("X-Correlation-ID"), custom_corr_id)


if __name__ == "__main__":
    unittest.main()
