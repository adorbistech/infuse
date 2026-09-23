"""Comprehensive Unit, Integration, and Isolation Test Suite for Block 15 Token Observer."""

import inspect
import sys
import threading
import unittest
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from infuse.contracts.events import (
    EventSource,
    EventType,
    ExecutionEvent,
    TokenObservedPayload,
)
from infuse.contracts.execution import (
    ExecutionContext,
    ExecutionRequest,
    ExecutionRequirements,
    ExecutionStatus,
    OperationRequest,
    TaskContext,
)
from infuse.events.bus import InMemoryEventBus
from infuse.events.models import (
    ExecutionCompletedPayload,
    ExecutionFailedPayload,
    ExecutionStartedPayload,
)
from infuse.lifecycle.service import ExecutionLifecycleService
from infuse.observer.interfaces import ITokenObserver
from infuse.observer.models import (
    ExecutionTokenSummary,
    TokenObservationRecord,
    TokenObservationSource,
)
from infuse.observer.observer import TokenObserver


class TestTokenObserver(unittest.TestCase):
    """Test suite verifying TokenObserver aggregation, idempotency, event bus integration, and isolation."""

    def setUp(self) -> None:
        self.observer = TokenObserver()
        self.bus = InMemoryEventBus(isolate_handler_errors=True)

    def _sample_event(
        self,
        event_id: str = "evt_01",
        execution_id: str = "exec_01",
        event_type: EventType = EventType.TOKEN_OBSERVED,
        source: EventSource = EventSource.PROVIDER,
        sequence: int = 0,
        payload: Optional[Dict[str, Any]] = None
    ) -> ExecutionEvent:
        return ExecutionEvent(
            event_id=event_id,
            execution_id=execution_id,
            type=event_type,
            source=source,
            sequence=sequence,
            payload=payload or {}
        )

    # 1. Single TokenObserved and Dimensions
    def test_01_single_token_observed_event(self) -> None:
        """Verify basic handling of a single TokenObserved event."""
        evt = self._sample_event(
            payload={
                "input_tokens": 120,
                "output_tokens": 45,
                "cached_tokens": 10,
                "total_tokens": 165,
                "is_authoritative": True,
                "provider": "openai",
                "model": "gpt-4o"
            }
        )
        self.observer.handle_event(evt)

        obs = self.observer.get_observation("exec_01")
        self.assertIsNotNone(obs)
        self.assertEqual(obs.execution_id, "exec_01")
        self.assertEqual(obs.input_tokens, 120)
        self.assertEqual(obs.output_tokens, 45)
        self.assertEqual(obs.cached_tokens, 10)
        self.assertEqual(obs.total_tokens, 165)
        self.assertTrue(obs.is_authoritative)
        self.assertEqual(obs.source, TokenObservationSource.PROVIDER_USAGE)
        self.assertEqual(obs.provider_id, "openai")
        self.assertEqual(obs.model_id, "gpt-4o")
        self.assertEqual(obs.events_count, 1)

    def test_02_input_token_observation_only(self) -> None:
        """Verify observation with only input tokens present."""
        evt = self._sample_event(
            payload={
                "input_tokens": 80,
                "is_authoritative": False
            }
        )
        self.observer.handle_event(evt)

        obs = self.observer.get_observation("exec_01")
        self.assertIsNotNone(obs)
        self.assertEqual(obs.input_tokens, 80)
        self.assertIsNone(obs.output_tokens)
        self.assertEqual(obs.total_tokens, 80)  # derived total = input (80) + output (0/None)
        self.assertFalse(obs.is_authoritative)
        self.assertEqual(obs.source, TokenObservationSource.STREAM_ESTIMATE)

    def test_03_output_token_observation_only(self) -> None:
        """Verify observation with only output tokens present."""
        evt = self._sample_event(
            payload={
                "output_tokens": 50,
                "is_authoritative": False
            }
        )
        self.observer.handle_event(evt)

        obs = self.observer.get_observation("exec_01")
        self.assertIsNotNone(obs)
        self.assertIsNone(obs.input_tokens)
        self.assertEqual(obs.output_tokens, 50)
        self.assertEqual(obs.total_tokens, 50)

    def test_04_total_token_observation_and_derivation(self) -> None:
        """Verify total tokens is derived when absent but components exist."""
        evt = self._sample_event(
            payload={
                "input_tokens": 100,
                "output_tokens": 50,
                # total_tokens omitted
            }
        )
        self.observer.handle_event(evt)

        obs = self.observer.get_observation("exec_01")
        self.assertIsNotNone(obs)
        self.assertEqual(obs.total_tokens, 150)

    # 2. Sequential Streaming & Multiple Usage Observations
    def test_05_multiple_usage_observations_streaming_sequence(self) -> None:
        """Verify progressive streaming observations update counts and maintain history."""
        # Chunk 1
        self.observer.handle_event(self._sample_event(
            event_id="e1", sequence=0, payload={"input_tokens": 100, "output_tokens": 10, "is_authoritative": False}
        ))
        # Chunk 2
        self.observer.handle_event(self._sample_event(
            event_id="e2", sequence=1, payload={"input_tokens": 100, "output_tokens": 25, "is_authoritative": False}
        ))
        # Final Chunk
        self.observer.handle_event(self._sample_event(
            event_id="e3", sequence=2, payload={"input_tokens": 100, "output_tokens": 50, "is_authoritative": False}
        ))

        obs = self.observer.get_observation("exec_01")
        self.assertIsNotNone(obs)
        self.assertEqual(obs.events_count, 3)
        self.assertEqual(obs.input_tokens, 100)
        self.assertEqual(obs.output_tokens, 50)
        self.assertEqual(obs.total_tokens, 150)
        self.assertEqual(len(obs.history), 3)

    def test_06_authoritative_event_supersedes_stream_estimates(self) -> None:
        """Verify authoritative provider usage supersedes prior stream estimates."""
        # Non-authoritative estimate
        self.observer.handle_event(self._sample_event(
            event_id="e_est", sequence=0, payload={"input_tokens": 100, "output_tokens": 48, "is_authoritative": False}
        ))
        obs_pre = self.observer.get_observation("exec_01")
        self.assertFalse(obs_pre.is_authoritative)

        # Authoritative final usage
        self.observer.handle_event(self._sample_event(
            event_id="e_auth", sequence=1, payload={"input_tokens": 102, "output_tokens": 50, "total_tokens": 152, "is_authoritative": True}
        ))

        obs_post = self.observer.get_observation("exec_01")
        self.assertTrue(obs_post.is_authoritative)
        self.assertEqual(obs_post.source, TokenObservationSource.PROVIDER_USAGE)
        self.assertEqual(obs_post.input_tokens, 102)
        self.assertEqual(obs_post.output_tokens, 50)
        self.assertEqual(obs_post.total_tokens, 152)

    # 3. Missing Data and Partial Dimensions
    def test_07_partial_token_information(self) -> None:
        """Verify partial token information preserves explicit None for unobserved dimensions."""
        self.observer.handle_event(self._sample_event(
            payload={"cached_tokens": 20}
        ))
        obs = self.observer.get_observation("exec_01")
        self.assertIsNotNone(obs)
        self.assertIsNone(obs.input_tokens)
        self.assertIsNone(obs.output_tokens)
        self.assertEqual(obs.cached_tokens, 20)
        self.assertIsNone(obs.total_tokens)

    def test_08_missing_data_no_fabrication_of_zeros(self) -> None:
        """Verify observer does not fabricate 0 when dimensions are unknown."""
        self.observer.handle_event(self._sample_event(
            payload={}
        ))
        obs = self.observer.get_observation("exec_01")
        self.assertIsNotNone(obs)
        self.assertIsNone(obs.input_tokens)
        self.assertIsNone(obs.output_tokens)
        self.assertIsNone(obs.total_tokens)

    # 4. Duplicate Handling and Idempotency
    def test_09_duplicate_event_handling_idempotent(self) -> None:
        """Verify duplicate publication of identical event does not double-count."""
        evt = self._sample_event(
            event_id="dup_evt_01",
            payload={"input_tokens": 100, "output_tokens": 50, "is_authoritative": True}
        )
        self.observer.handle_event(evt)
        self.observer.handle_event(evt)

        obs = self.observer.get_observation("exec_01")
        self.assertEqual(obs.events_count, 1)
        self.assertEqual(len(obs.history), 1)
        self.assertEqual(obs.total_tokens, 150)

    # 5. Out of Order Events
    def test_10_out_of_order_stream_does_not_degrade_authoritative_summary(self) -> None:
        """Verify earlier sequence stream estimate arriving after authoritative completion is recorded in history but does not overwrite authoritative summary."""
        # 1. Authoritative event arrived first (e.g. sequence 2)
        self.observer.handle_event(self._sample_event(
            event_id="e_final", sequence=2, payload={"input_tokens": 100, "output_tokens": 50, "total_tokens": 150, "is_authoritative": True}
        ))
        # 2. Delayed stream chunk arrived late (sequence 1)
        self.observer.handle_event(self._sample_event(
            event_id="e_delayed", sequence=1, payload={"input_tokens": 100, "output_tokens": 20, "is_authoritative": False}
        ))

        obs = self.observer.get_observation("exec_01")
        self.assertTrue(obs.is_authoritative)
        self.assertEqual(obs.output_tokens, 50)
        self.assertEqual(obs.total_tokens, 150)
        self.assertEqual(len(obs.history), 2)

    # 6. Finalization (ExecutionCompleted & ExecutionFailed)
    def test_11_execution_completed_finalization(self) -> None:
        """Verify ExecutionCompleted finalizes the summary and sets final status."""
        self.observer.handle_event(self._sample_event(
            event_id="e_start",
            event_type=EventType.EXECUTION_STARTED,
            sequence=0,
            payload={"provider_id": "anthropic", "model_id": "claude-3-5-sonnet"}
        ))
        self.observer.handle_event(self._sample_event(
            event_id="e_comp",
            event_type=EventType.EXECUTION_COMPLETED,
            sequence=1,
            payload={
                "provider_id": "anthropic",
                "model_id": "claude-3-5-sonnet",
                "input_tokens": 200,
                "output_tokens": 100,
                "total_tokens": 300,
                "status": "COMPLETED"
            }
        ))

        obs = self.observer.get_observation("exec_01")
        self.assertTrue(obs.is_finalized)
        self.assertEqual(obs.final_status, "COMPLETED")
        self.assertEqual(obs.input_tokens, 200)
        self.assertEqual(obs.output_tokens, 100)
        self.assertEqual(obs.total_tokens, 300)
        self.assertEqual(obs.provider_id, "anthropic")
        self.assertEqual(obs.model_id, "claude-3-5-sonnet")
        self.assertTrue(self.observer.is_finalized("exec_01"))

    def test_12_execution_failed_finalization_without_usage_fabrication(self) -> None:
        """Verify ExecutionFailed finalizes execution without inventing token counts."""
        self.observer.handle_event(self._sample_event(
            event_id="e_fail",
            event_type=EventType.EXECUTION_FAILED,
            sequence=0,
            payload={
                "provider_id": "openai",
                "model_id": "gpt-4o",
                "status": "FAILED",
                "error_type": "RESOLUTION_ERROR"
            }
        ))

        obs = self.observer.get_observation("exec_01")
        self.assertTrue(obs.is_finalized)
        self.assertEqual(obs.final_status, "FAILED")
        self.assertIsNone(obs.input_tokens)
        self.assertIsNone(obs.output_tokens)
        self.assertIsNone(obs.total_tokens)
        self.assertEqual(obs.provider_id, "openai")

    # 7. Multiple Executions Isolation
    def test_13_multiple_executions_isolation(self) -> None:
        """Verify independent execution runs remain completely isolated."""
        self.observer.handle_event(self._sample_event(
            event_id="e_a", execution_id="exec_A", payload={"input_tokens": 10, "output_tokens": 20, "is_authoritative": True}
        ))
        self.observer.handle_event(self._sample_event(
            event_id="e_b", execution_id="exec_B", payload={"input_tokens": 100, "output_tokens": 200, "is_authoritative": True}
        ))

        obs_a = self.observer.get_observation("exec_A")
        obs_b = self.observer.get_observation("exec_B")

        self.assertEqual(obs_a.total_tokens, 30)
        self.assertEqual(obs_b.total_tokens, 300)
        self.assertEqual(len(self.observer.list_observations()), 2)

    # 8. Event Bus Integration
    def test_14_event_bus_attach_and_detach(self) -> None:
        """Verify attaching observer to Event Bus receives published events and detaching stops them."""
        tokens = self.observer.attach_to_bus(self.bus)
        self.assertGreater(len(tokens), 0)

        # Publish event on bus
        self.bus.publish(self._sample_event(
            event_id="eb_1",
            execution_id="exec_eb",
            event_type=EventType.TOKEN_OBSERVED,
            payload={"input_tokens": 50, "output_tokens": 25, "is_authoritative": True}
        ))

        obs = self.observer.get_observation("exec_eb")
        self.assertIsNotNone(obs)
        self.assertEqual(obs.total_tokens, 75)

        # Detach and publish again
        self.observer.detach_from_bus(self.bus)
        self.bus.publish(self._sample_event(
            event_id="eb_2",
            execution_id="exec_eb_2",
            event_type=EventType.TOKEN_OBSERVED,
            payload={"input_tokens": 100, "is_authoritative": True}
        ))

        self.assertIsNone(self.observer.get_observation("exec_eb_2"))

    # 9. Subscriber Immutability Isolation
    def test_15_returned_observation_is_deep_copy(self) -> None:
        """Verify modifying the returned observation summary does not corrupt internal state."""
        self.observer.handle_event(self._sample_event(
            payload={"input_tokens": 50, "output_tokens": 50, "is_authoritative": True}
        ))

        obs = self.observer.get_observation("exec_01")
        obs.input_tokens = 9999
        obs.history.clear()

        # Re-fetch and check
        fresh = self.observer.get_observation("exec_01")
        self.assertEqual(fresh.input_tokens, 50)
        self.assertEqual(len(fresh.history), 1)

    # 10. Thread Safety Under Concurrent Events
    def test_16_thread_safe_concurrent_event_delivery(self) -> None:
        """Verify observer maintains integrity under concurrent event processing across threads."""
        threads = []
        num_threads = 10
        events_per_thread = 20

        def worker(thread_idx: int):
            for i in range(events_per_thread):
                evt = self._sample_event(
                    event_id=f"evt_th_{thread_idx}_{i}",
                    execution_id=f"exec_th_{thread_idx}",
                    payload={"input_tokens": 10, "output_tokens": 5, "is_authoritative": True}
                )
                self.observer.handle_event(evt)

        for t_idx in range(num_threads):
            t = threading.Thread(target=worker, args=(t_idx,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.assertEqual(len(self.observer.list_observations()), num_threads)
        for t_idx in range(num_threads):
            obs = self.observer.get_observation(f"exec_th_{t_idx}")
            self.assertIsNotNone(obs)
            self.assertEqual(obs.events_count, events_per_thread)

    # 11. Lifecycle End-to-End Event Bus Observation
    def test_17_lifecycle_execution_observed_via_event_bus(self) -> None:
        """Verify ExecutionLifecycleService execution automatically generates observations on TokenObserver attached to bus."""
        self.observer.attach_to_bus(self.bus)
        service = ExecutionLifecycleService(event_bus=self.bus)

        req = ExecutionRequest(
            request_id="req_obs_test",
            task=TaskContext(task_id="task_obs_test"),
            request=OperationRequest(messages=[{"role": "user", "content": "Test observation"}]),
            execution_context=ExecutionContext(session_id="sess_obs_01")
        )

        result = service.execute(req, execution_id="exec_obs_e2e")
        self.assertEqual(result.status, ExecutionStatus.COMPLETED)

        # Check TokenObserver captured the events
        obs = self.observer.get_observation("exec_obs_e2e")
        self.assertIsNotNone(obs)
        self.assertTrue(obs.is_finalized)
        self.assertEqual(obs.final_status, "COMPLETED")
        self.assertEqual(obs.total_tokens, 195)
        self.assertEqual(obs.input_tokens, 150)
        self.assertEqual(obs.output_tokens, 45)

    # 12. Architectural Isolation Tests
    def test_18_zero_database_imports_in_observer_package(self) -> None:
        """Verify observer package contains zero database library imports."""
        import infuse.observer
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.observer")]

        forbidden = ["sqlite3", "psycopg2", "asyncpg", "sqlalchemy", "redis", "qdrant_client", "motor", "pymongo"]
        for mod in modules:
            src = inspect.getsource(mod)
            for f in forbidden:
                self.assertNotIn(f"import {f}", src)
                self.assertNotIn(f"from {f}", src)

    def test_19_zero_provider_and_broker_sdk_imports(self) -> None:
        """Verify observer package contains zero real provider or broker SDK imports."""
        import infuse.observer
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.observer")]

        forbidden = [
            "openai", "anthropic", "google.generativeai", "cohere", "langchain", "crewai", "autogen",
            "kafka", "pika", "nats", "redis", "aioredis", "celery", "kombu"
        ]
        for mod in modules:
            src = inspect.getsource(mod)
            for f in forbidden:
                self.assertNotIn(f"import {f}", src)
                self.assertNotIn(f"from {f}", src)

    def test_20_zero_pricing_routing_governor_or_lifecycle_mutation_logic(self) -> None:
        """Verify observer contains zero pricing, routing, Governor decisions, or lifecycle state machines."""
        import infuse.observer
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.observer")]

        forbidden_patterns = [
            "calculate_cost",
            "calculate_price",
            "calculate_margin",
            "issue_action",
            "apply_governance",
            "score_health",
            "detect_runaway",
            "detect_anomaly",
            "route_request",
            "update_state("
        ]
        for mod in modules:
            src = inspect.getsource(mod)
            for p in forbidden_patterns:
                self.assertNotIn(p, src)


if __name__ == "__main__":
    unittest.main()
