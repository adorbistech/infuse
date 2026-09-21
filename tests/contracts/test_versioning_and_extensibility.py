"""Tests for Contract Versioning, Additive Evolution, and Extensibility."""

import unittest
from infuse.contracts.common import InfuseBaseModel
from infuse.contracts.execution import ExecutionRequest, TaskContext, OperationRequest
from infuse.contracts.policy import GovernancePolicy
from infuse.contracts.events import ExecutionEvent, EventType, EventSource


class TestVersioningAndExtensibility(unittest.TestCase):
    """Test schema versioning and additive non-breaking evolution rules."""

    def test_schema_version_default_presence(self):
        req = ExecutionRequest(
            request_id="req_ver_1",
            task=TaskContext(task_id="t1"),
            request=OperationRequest(messages=[])
        )
        self.assertEqual(req.schema_version, "1.0.0")

        pol = GovernancePolicy(policy_id="pol_1")
        self.assertEqual(pol.schema_version, "1.0.0")

    def test_forward_compatible_extra_fields(self):
        # Emulate receiving a future payload with extra/unrecognized fields
        future_payload_json = """
        {
            "schema_version": "1.1.0",
            "request_id": "req_future_99",
            "task": {
                "task_id": "t_future",
                "quantum_priority": 999
            },
            "request": {
                "messages": [{"role": "user", "content": "hello"}],
                "hologram_format": "v3"
            },
            "future_experimental_flag": true,
            "extensions": {
                "custom_trace_id": "trace_xyz"
            }
        }
        """
        req = ExecutionRequest.model_validate_json(future_payload_json)
        self.assertEqual(req.request_id, "req_future_99")
        self.assertEqual(req.schema_version, "1.1.0")
        self.assertEqual(req.extensions.get("custom_trace_id"), "trace_xyz")
        # Extra fields preserved without throwing error
        self.assertTrue(hasattr(req, "future_experimental_flag") or "future_experimental_flag" in req.__pydantic_extra__)

    def test_event_envelope_extensibility(self):
        event_json = """
        {
            "event_id": "evt_custom_001",
            "execution_id": "exec_001",
            "type": "ExecutionStarted",
            "source": "AGENT",
            "sequence": 1,
            "payload": {
                "custom_metric_1": 42,
                "custom_metric_2": "active"
            },
            "schema_version": "1.0.0",
            "extensions": {
                "telemetry_cluster": "eu-central"
            }
        }
        """
        event = ExecutionEvent.model_validate_json(event_json)
        self.assertEqual(event.event_id, "evt_custom_001")
        self.assertEqual(event.payload["custom_metric_1"], 42)
        self.assertEqual(event.extensions["telemetry_cluster"], "eu-central")


if __name__ == "__main__":
    unittest.main()
