"""INFUSE Block 34 — Serialization Safety and Resource Exhaustion Security Suite.

Validates that:
- Models and contracts use safe serialization (Pydantic / standard JSON)
- Rapid event bursts are handled deterministically without deadlock or data race
- Oversized message structures and token counts are bounded and normalized
- Concurrent multi-threaded executions maintain thread safety
"""

import concurrent.futures
import json
import unittest
import uuid
from decimal import Decimal

from infuse.contracts.common import utc_now
from infuse.contracts.events import EventSource, EventType, ExecutionEvent
from infuse.contracts.execution import (
    ExecutionContext,
    ExecutionRequest,
    ExecutionRequirements,
    OperationRequest,
    TaskContext,
)
from infuse.contracts.policy import GovernancePolicy, PolicyActionBindings
from infuse.e2e.environment import EndToEndIntegrationEnvironment


class TestSerializationAndDosSecurity(unittest.TestCase):
    """Verifies safe data serialization, concurrency stability, and resource burst tolerance."""

    def setUp(self) -> None:
        self.env = EndToEndIntegrationEnvironment()

    def test_01_safe_serialization_roundtrip(self) -> None:
        """Verify models serialize to JSON and back safely using standard Pydantic serializers."""
        req = ExecutionRequest(
            request_id=f"req_ser_{uuid.uuid4().hex[:6]}",
            task=TaskContext(task_id="task_ser", description="Serialization safety check"),
            request=OperationRequest(
                messages=[{"role": "user", "content": "Safe content with special chars: <>&\"'\\/\b\f\n\r\t"}]
            ),
        )
        json_str = req.model_dump_json()
        self.assertIsInstance(json_str, str)

        parsed_dict = json.loads(json_str)
        reconstructed = ExecutionRequest.model_validate(parsed_dict)
        self.assertEqual(reconstructed.request_id, req.request_id)
        self.assertEqual(reconstructed.request.messages[0]["content"], req.request.messages[0]["content"])

    def test_02_rapid_event_burst_deterministic_consumption(self) -> None:
        """Verify rapid publishing of 200 events across threads without deadlocks or corruption."""
        exec_id = f"exec_burst_{uuid.uuid4().hex[:8]}"
        num_events = 200

        def publish_single_event(idx: int):
            evt = ExecutionEvent(
                event_id=f"evt_burst_{idx}_{uuid.uuid4().hex[:4]}",
                execution_id=exec_id,
                type=EventType.TOKEN_OBSERVED,
                source=EventSource.PROVIDER,
                sequence=idx + 1,
                payload={
                    "total_tokens": 10,
                    "input_tokens": 5,
                    "output_tokens": 5,
                    "provider": "mock",
                    "model": "mock-fast",
                },
            )
            self.env.emit_event(evt)

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(publish_single_event, i) for i in range(num_events)]
            for f in concurrent.futures.as_completed(futures):
                f.result()

        tok_obs = self.env.token_observer.get_observation(exec_id)
        self.assertIsNotNone(tok_obs)
        self.assertEqual(tok_obs.events_count, num_events)

    def test_03_oversized_message_payload_handling(self) -> None:
        """Verify handling execution request with large prompt payload (100KB) succeeds deterministically."""
        large_prompt = "x" * 100_000
        req = ExecutionRequest(
            request_id=f"req_large_{uuid.uuid4().hex[:6]}",
            task=TaskContext(task_id="task_large", description="Large payload test"),
            request=OperationRequest(messages=[{"role": "user", "content": large_prompt}]),
        )
        audit = self.env.execute_e2e(request=req)
        self.assertIsNotNone(audit.result)
        self.assertIn("COMPLETED", str(audit.result.status))

    def test_04_concurrency_race_condition_protection(self) -> None:
        """Verify multiple simultaneous executions do not race on policy retrieval or state tracking."""
        def run_isolated(i: int):
            req = ExecutionRequest(
                request_id=f"req_race_{i}_{uuid.uuid4().hex[:6]}",
                task=TaskContext(task_id=f"task_{i}", description="Race safety check"),
                request=OperationRequest(messages=[{"role": "user", "content": f"Prompt {i}"}]),
            )
            return self.env.execute_e2e(request=req)

        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            futures = [pool.submit(run_isolated, i) for i in range(12)]
            results = [f.result() for f in futures]

        self.assertEqual(len(results), 12)
        exec_ids = [r.execution_id for r in results]
        self.assertEqual(len(set(exec_ids)), 12)


if __name__ == "__main__":
    unittest.main()
