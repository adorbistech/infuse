"""Comprehensive Unit, Integration, and Isolation Test Suite for Block 17 Health Engine."""

import inspect
import sys
import threading
import unittest
from typing import Optional

from infuse.contracts.events import EventSource, EventType, ExecutionEvent
from infuse.events.bus import InMemoryEventBus
from infuse.health.classifier import classify_error_category
from infuse.health.engine import HealthEngine
from infuse.health.models import (
    ErrorCategory,
    ExecutionHealthSummary,
    HealthCompleteness,
)


class TestHealthEngine(unittest.TestCase):
    """Test suite verifying health event consumption, latency capture, aggregation, and isolation."""

    def setUp(self) -> None:
        self.engine = HealthEngine()

    def _event(
        self,
        event_id: str,
        execution_id: str,
        event_type: EventType,
        sequence: int = 1,
        payload: Optional[dict] = None
    ) -> ExecutionEvent:
        return ExecutionEvent(
            event_id=event_id,
            execution_id=execution_id,
            type=event_type,
            source=EventSource.SYSTEM,
            sequence=sequence,
            payload=payload or {}
        )

    # 1. Lifecycle & Latency Observation
    def test_01_execution_started_observation(self) -> None:
        """Verify ExecutionStarted records provider/model and sets STARTED status."""
        ev = self._event(
            event_id="evt_start_01",
            execution_id="exec_01",
            event_type=EventType.EXECUTION_STARTED,
            payload={"provider_id": "openai", "model_id": "gpt-4o"}
        )
        res = self.engine.handle_event(ev)
        self.assertIsNotNone(res)
        self.assertEqual(res.status, "STARTED")
        self.assertEqual(res.provider_id, "openai")
        self.assertEqual(res.model_id, "gpt-4o")
        self.assertIsNone(res.is_success)
        self.assertFalse(res.is_finalized)
        self.assertEqual(res.completeness, HealthCompleteness.PARTIAL)

    def test_02_execution_completed_success_and_latency(self) -> None:
        """Verify ExecutionCompleted records success, latency, and marks finalized."""
        self.engine.handle_event(self._event(
            event_id="evt_start_02",
            execution_id="exec_02",
            event_type=EventType.EXECUTION_STARTED,
            sequence=0,
            payload={"provider_id": "anthropic", "model_id": "claude-3-5-sonnet"}
        ))
        res = self.engine.handle_event(self._event(
            event_id="evt_comp_02",
            execution_id="exec_02",
            event_type=EventType.EXECUTION_COMPLETED,
            sequence=1,
            payload={"provider_id": "anthropic", "model_id": "claude-3-5-sonnet", "duration_ms": 250.5}
        ))
        self.assertTrue(res.is_success)
        self.assertTrue(res.is_finalized)
        self.assertEqual(res.status, "COMPLETED")
        self.assertEqual(res.latency_ms, 250.5)
        self.assertEqual(res.completeness, HealthCompleteness.COMPLETE)

    def test_03_execution_failed_observation(self) -> None:
        """Verify ExecutionFailed records failure and extracts error category."""
        self.engine.handle_event(self._event(
            event_id="evt_start_03",
            execution_id="exec_03",
            event_type=EventType.EXECUTION_STARTED,
            sequence=0,
            payload={"provider_id": "google", "model_id": "gemini-2.0-flash"}
        ))
        res = self.engine.handle_event(self._event(
            event_id="evt_fail_03",
            execution_id="exec_03",
            event_type=EventType.EXECUTION_FAILED,
            sequence=1,
            payload={
                "provider_id": "google",
                "model_id": "gemini-2.0-flash",
                "duration_ms": 120.0,
                "error_type": "RateLimitError",
                "error_message": "Resource exhausted 429",
                "http_status": 429
            }
        ))
        self.assertFalse(res.is_success)
        self.assertTrue(res.is_finalized)
        self.assertEqual(res.status, "FAILED")
        self.assertEqual(len(res.errors), 1)
        self.assertEqual(res.errors[0].error_category, ErrorCategory.RATE_LIMIT)
        self.assertEqual(res.errors[0].http_status, 429)

    def test_04_missing_latency_preserved_as_none(self) -> None:
        """Verify missing latency in completed event is preserved as None rather than fabricated as 0.0."""
        res = self.engine.handle_event(self._event(
            event_id="evt_comp_04",
            execution_id="exec_04",
            event_type=EventType.EXECUTION_COMPLETED,
            payload={"provider_id": "openai", "model_id": "gpt-4o"}
        ))
        self.assertIsNone(res.latency_ms)
        self.assertEqual(res.completeness, HealthCompleteness.PARTIAL)

    # 2. Error Categorization & Provider Errors
    def test_05_error_category_classification_matrix(self) -> None:
        """Verify deterministic categorization across HTTP status codes and error keywords."""
        self.assertEqual(classify_error_category(http_status=429), ErrorCategory.RATE_LIMIT)
        self.assertEqual(classify_error_category(http_status=401), ErrorCategory.AUTHENTICATION)
        self.assertEqual(classify_error_category(http_status=403), ErrorCategory.AUTHENTICATION)
        self.assertEqual(classify_error_category(http_status=504), ErrorCategory.TIMEOUT)
        self.assertEqual(classify_error_category(http_status=503), ErrorCategory.UNAVAILABLE)
        self.assertEqual(classify_error_category(http_status=400), ErrorCategory.INVALID_REQUEST)
        self.assertEqual(classify_error_category(http_status=500), ErrorCategory.PROVIDER_ERROR)

        self.assertEqual(classify_error_category(message="Request timed out after 30s"), ErrorCategory.TIMEOUT)
        self.assertEqual(classify_error_category(message="quota exceeded for organization"), ErrorCategory.RATE_LIMIT)
        self.assertEqual(classify_error_category(message="Invalid API Key provided"), ErrorCategory.AUTHENTICATION)
        self.assertEqual(classify_error_category(message="Service overloaded, please retry"), ErrorCategory.UNAVAILABLE)
        self.assertEqual(classify_error_category(error_type="RESOLUTION_ERROR"), ErrorCategory.EXECUTION_ERROR)
        self.assertEqual(classify_error_category(message="something random"), ErrorCategory.UNKNOWN)

    def test_06_provider_error_event_observation(self) -> None:
        """Verify ProviderError events are recorded on execution and in provider aggregate."""
        res = self.engine.handle_event(self._event(
            event_id="evt_perr_06",
            execution_id="exec_06",
            event_type=EventType.PROVIDER_ERROR,
            payload={
                "provider": "anthropic",
                "model": "claude-3-opus",
                "error_code": "overloaded_error",
                "error_type": "PROVIDER_ERROR",
                "message": "Anthropic API overloaded",
                "is_retryable": True,
                "http_status": 529
            }
        ))
        self.assertEqual(len(res.errors), 1)
        self.assertEqual(res.errors[0].error_category, ErrorCategory.UNAVAILABLE)
        self.assertTrue(res.errors[0].is_retryable)

        p_agg = self.engine.get_provider_aggregate("anthropic")
        self.assertIsNotNone(p_agg)
        self.assertEqual(p_agg.provider_error_count, 1)
        self.assertEqual(p_agg.error_counts_by_category.get(ErrorCategory.UNAVAILABLE.value), 1)

    # 3. Retry Observation
    def test_07_retry_started_observation_no_execution(self) -> None:
        """Verify RetryStarted records attempt evidence without triggering an active retry."""
        res = self.engine.handle_event(self._event(
            event_id="evt_retry_07",
            execution_id="exec_07",
            event_type=EventType.RETRY_STARTED,
            payload={
                "provider": "openai",
                "model": "gpt-4o",
                "attempt": 1,
                "reason": "transient timeout"
            }
        ))
        self.assertEqual(len(res.retries), 1)
        self.assertEqual(res.retries[0].attempt_number, 1)
        self.assertEqual(res.retries[0].reason, "transient timeout")

        p_agg = self.engine.get_provider_aggregate("openai")
        self.assertIsNotNone(p_agg)
        self.assertEqual(p_agg.retry_count, 1)

    # 4. Deduplication & Out-of-Order Handling
    def test_08_duplicate_events_are_idempotent(self) -> None:
        """Verify duplicate events with identical event_id do not double count in summary or aggregates."""
        ev = self._event(
            event_id="evt_dup_08",
            execution_id="exec_08",
            event_type=EventType.EXECUTION_COMPLETED,
            payload={"provider_id": "openai", "model_id": "gpt-4o", "duration_ms": 100.0}
        )
        self.engine.handle_event(ev)
        self.engine.handle_event(ev)

        summary = self.engine.get_execution_health("exec_08")
        self.assertEqual(summary.events_count, 1)

        p_agg = self.engine.get_provider_aggregate("openai")
        self.assertEqual(p_agg.total_executions, 1)
        self.assertEqual(p_agg.successful_executions, 1)
        self.assertEqual(p_agg.total_latency_ms, 100.0)

    def test_09_out_of_order_events_handled_deterministically(self) -> None:
        """Verify receiving execution completed before execution started handles facts deterministically."""
        # Completed event arriving first (e.g. race/out of order)
        self.engine.handle_event(self._event(
            event_id="evt_comp_09",
            execution_id="exec_09",
            event_type=EventType.EXECUTION_COMPLETED,
            sequence=2,
            payload={"provider_id": "openai", "model_id": "gpt-4o", "duration_ms": 150.0}
        ))
        # Started event arriving delayed
        self.engine.handle_event(self._event(
            event_id="evt_start_09",
            execution_id="exec_09",
            event_type=EventType.EXECUTION_STARTED,
            sequence=1,
            payload={"provider_id": "openai", "model_id": "gpt-4o"}
        ))

        summary = self.engine.get_execution_health("exec_09")
        self.assertEqual(summary.status, "COMPLETED")
        self.assertTrue(summary.is_success)
        self.assertEqual(summary.last_sequence, 2)
        self.assertEqual(summary.events_count, 2)

    # 5. Aggregate Metrics
    def test_10_provider_and_model_aggregates_calculation(self) -> None:
        """Verify multi-execution aggregation across provider and model scopes."""
        # Execution 1: 100ms success
        self.engine.handle_event(self._event(
            event_id="e1", execution_id="ex1", event_type=EventType.EXECUTION_COMPLETED,
            payload={"provider_id": "openai", "model_id": "gpt-4o", "duration_ms": 100.0}
        ))
        # Execution 2: 300ms success
        self.engine.handle_event(self._event(
            event_id="e2", execution_id="ex2", event_type=EventType.EXECUTION_COMPLETED,
            payload={"provider_id": "openai", "model_id": "gpt-4o", "duration_ms": 300.0}
        ))
        # Execution 3: 200ms failure
        self.engine.handle_event(self._event(
            event_id="e3", execution_id="ex3", event_type=EventType.EXECUTION_FAILED,
            payload={"provider_id": "openai", "model_id": "gpt-4o-mini", "duration_ms": 200.0, "error_type": "timeout"}
        ))

        p_agg = self.engine.get_provider_aggregate("openai")
        self.assertEqual(p_agg.total_executions, 3)
        self.assertEqual(p_agg.successful_executions, 2)
        self.assertEqual(p_agg.failed_executions, 1)
        self.assertEqual(p_agg.min_latency_ms, 100.0)
        self.assertEqual(p_agg.max_latency_ms, 300.0)
        self.assertEqual(p_agg.avg_latency_ms, 200.0)

        m_agg_4o = self.engine.get_model_aggregate("openai", "gpt-4o")
        self.assertEqual(m_agg_4o.total_executions, 2)
        self.assertEqual(m_agg_4o.successful_executions, 2)
        self.assertEqual(m_agg_4o.avg_latency_ms, 200.0)

        m_agg_mini = self.engine.get_model_aggregate("openai", "gpt-4o-mini")
        self.assertEqual(m_agg_mini.total_executions, 1)
        self.assertEqual(m_agg_mini.failed_executions, 1)

    # 6. Event Bus Integration & Isolation
    def test_11_event_bus_integration(self) -> None:
        """Verify HealthEngine attaches to and detaches from EventBus cleanly."""
        bus = InMemoryEventBus()
        sub_ids = self.engine.attach_to_bus(bus)
        self.assertEqual(len(sub_ids), len(self.engine.HEALTH_EVENT_TYPES))

        bus.publish(self._event(
            event_id="bus_evt_01",
            execution_id="exec_bus_01",
            event_type=EventType.EXECUTION_COMPLETED,
            payload={"provider_id": "anthropic", "model_id": "claude-3-haiku", "duration_ms": 80.0}
        ))

        summary = self.engine.get_execution_health("exec_bus_01")
        self.assertIsNotNone(summary)
        self.assertTrue(summary.is_success)

        self.engine.detach_from_bus(bus)
        self.assertEqual(len(self.engine._subscription_ids), 0)

    def test_12_thread_safe_concurrent_event_processing(self) -> None:
        """Verify HealthEngine handles concurrent multi-threaded event delivery safely."""
        threads = []
        for i in range(10):
            ev = self._event(
                event_id=f"evt_th_{i}",
                execution_id=f"exec_th_{i}",
                event_type=EventType.EXECUTION_COMPLETED,
                payload={"provider_id": "openai", "model_id": "gpt-4o", "duration_ms": float(10 * (i + 1))}
            )
            t = threading.Thread(target=self.engine.handle_event, args=(ev,))
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(self.engine.list_execution_health()), 10)
        p_agg = self.engine.get_provider_aggregate("openai")
        self.assertEqual(p_agg.total_executions, 10)

    # 7. Architectural Isolation Checks
    def test_13_zero_database_imports_in_health_package(self) -> None:
        """Verify health package contains zero database library imports."""
        import infuse.health
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.health")]

        forbidden = ["sqlite3", "psycopg2", "asyncpg", "sqlalchemy", "redis", "qdrant_client", "motor", "pymongo"]
        for mod in modules:
            src = inspect.getsource(mod)
            for f in forbidden:
                self.assertNotIn(f"import {f}", src)
                self.assertNotIn(f"from {f}", src)

    def test_14_zero_provider_and_broker_sdk_imports(self) -> None:
        """Verify health package contains zero provider or message broker SDK imports."""
        import infuse.health
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.health")]

        forbidden = [
            "openai", "anthropic", "google.generativeai", "cohere", "langchain", "crewai", "autogen",
            "kafka", "pika", "nats", "redis", "aioredis", "celery", "kombu"
        ]
        for mod in modules:
            src = inspect.getsource(mod)
            for f in forbidden:
                self.assertNotIn(f"import {f}", src)
                self.assertNotIn(f"from {f}", src)

    def test_15_zero_active_probing_routing_governor_or_lifecycle_control(self) -> None:
        """Verify health package contains zero active network probing, routing, Governor actions, or retries."""
        import infuse.health
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.health")]

        forbidden_patterns = [
            "requests.get",
            "httpx.get",
            "urllib.request",
            "socket.socket",
            "select_provider",
            "route_request",
            "execute_retry",
            "apply_governance",
            "stop_execution",
            "throttle",
            "mutate_lifecycle"
        ]
        for mod in modules:
            src = inspect.getsource(mod)
            for p in forbidden_patterns:
                self.assertNotIn(p, src)


if __name__ == "__main__":
    unittest.main()
