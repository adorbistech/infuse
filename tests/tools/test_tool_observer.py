"""Comprehensive Unit, Integration, and Isolation Test Suite for Block 18 Tool Activity Observer."""

import inspect
import sys
import threading
import unittest
from datetime import datetime, timedelta, timezone
from typing import Optional

from infuse.contracts.events import EventSource, EventType, ExecutionEvent
from infuse.events.bus import InMemoryEventBus
from infuse.tools.models import (
    ExecutionToolSummary,
    ToolInvocationRecord,
    ToolInvocationStatus,
    ToolObservationCompleteness,
)
from infuse.tools.observer import ToolActivityObserver


class TestToolActivityObserver(unittest.TestCase):
    """Test suite verifying tool activity event consumption, correlation, aggregation, and isolation."""

    def setUp(self) -> None:
        self.observer = ToolActivityObserver()

    def _event(
        self,
        event_id: str,
        execution_id: str,
        event_type: EventType,
        sequence: int = 1,
        timestamp: Optional[datetime] = None,
        payload: Optional[dict] = None
    ) -> ExecutionEvent:
        return ExecutionEvent(
            event_id=event_id,
            execution_id=execution_id,
            type=event_type,
            source=EventSource.SYSTEM,
            sequence=sequence,
            timestamp=timestamp or datetime.now(timezone.utc),
            payload=payload or {}
        )

    # 1. Call & Completed Observations
    def test_01_tool_called_observation(self) -> None:
        """Verify ToolCalled records tool name, arguments, call_id and sets CALLED status."""
        ev = self._event(
            event_id="evt_call_01",
            execution_id="exec_01",
            event_type=EventType.TOOL_CALLED,
            sequence=1,
            payload={"tool_name": "database_query", "call_id": "call_01", "arguments": {"query": "SELECT 1"}}
        )
        res = self.observer.handle_event(ev)
        self.assertIsNotNone(res)
        self.assertEqual(res.total_calls, 1)
        self.assertEqual(res.incomplete_calls, 1)
        self.assertEqual(res.completed_calls, 0)
        self.assertEqual(res.unique_tools, ["database_query"])
        self.assertEqual(res.completeness, ToolObservationCompleteness.PARTIAL)

        inv = self.observer.get_invocation("exec_01", "call_01")
        self.assertIsNotNone(inv)
        self.assertEqual(inv.tool_name, "database_query")
        self.assertEqual(inv.status, ToolInvocationStatus.CALLED)
        self.assertEqual(inv.arguments, {"query": "SELECT 1"})
        self.assertIsNone(inv.success)
        self.assertIsNone(inv.duration_ms)

    def test_02_tool_completed_success_and_duration(self) -> None:
        """Verify ToolCompleted correlates with call_id and records duration and success."""
        t_start = datetime.now(timezone.utc)
        self.observer.handle_event(self._event(
            event_id="evt_call_02",
            execution_id="exec_02",
            event_type=EventType.TOOL_CALLED,
            sequence=1,
            timestamp=t_start,
            payload={"tool_name": "web_search", "call_id": "call_02", "arguments": {"q": "weather"}}
        ))

        t_end = t_start + timedelta(milliseconds=150)
        res = self.observer.handle_event(self._event(
            event_id="evt_comp_02",
            execution_id="exec_02",
            event_type=EventType.TOOL_COMPLETED,
            sequence=2,
            timestamp=t_end,
            payload={"tool_name": "web_search", "call_id": "call_02", "success": True, "duration_ms": 150.0}
        ))

        self.assertEqual(res.total_calls, 1)
        self.assertEqual(res.completed_calls, 1)
        self.assertEqual(res.successful_calls, 1)
        self.assertEqual(res.failed_calls, 0)
        self.assertEqual(res.incomplete_calls, 0)
        self.assertEqual(res.total_duration_ms, 150.0)
        self.assertEqual(res.avg_duration_ms, 150.0)
        self.assertEqual(res.completeness, ToolObservationCompleteness.COMPLETE)

        inv = self.observer.get_invocation("exec_02", "call_02")
        self.assertEqual(inv.status, ToolInvocationStatus.COMPLETED)
        self.assertTrue(inv.success)
        self.assertEqual(inv.duration_ms, 150.0)

    def test_03_tool_completed_failure(self) -> None:
        """Verify ToolCompleted records failure and captures normalized error string."""
        self.observer.handle_event(self._event(
            event_id="evt_call_03",
            execution_id="exec_03",
            event_type=EventType.TOOL_CALLED,
            sequence=1,
            payload={"tool_name": "file_reader", "call_id": "call_03"}
        ))
        res = self.observer.handle_event(self._event(
            event_id="evt_comp_03",
            execution_id="exec_03",
            event_type=EventType.TOOL_COMPLETED,
            sequence=2,
            payload={"tool_name": "file_reader", "call_id": "call_03", "success": False, "error": "File not found"}
        ))
        self.assertEqual(res.total_calls, 1)
        self.assertEqual(res.failed_calls, 1)
        self.assertEqual(res.successful_calls, 0)

        inv = self.observer.get_invocation("exec_03", "call_03")
        self.assertEqual(inv.status, ToolInvocationStatus.FAILED)
        self.assertFalse(inv.success)
        self.assertEqual(inv.error, "File not found")

    def test_04_missing_completion_treated_as_incomplete(self) -> None:
        """Verify tool call without completion is marked CALLED/incomplete and never assumed failed."""
        res = self.observer.handle_event(self._event(
            event_id="evt_call_04",
            execution_id="exec_04",
            event_type=EventType.TOOL_CALLED,
            payload={"tool_name": "calculator", "call_id": "call_04"}
        ))
        self.assertEqual(res.incomplete_calls, 1)
        self.assertEqual(res.failed_calls, 0)
        self.assertEqual(res.completed_calls, 0)
        self.assertEqual(res.completeness, ToolObservationCompleteness.PARTIAL)

    def test_05_missing_duration_calculated_or_none(self) -> None:
        """Verify duration is computed from timestamps or preserved as None (never fabricated as 0.0)."""
        # Timestamp-derived duration
        t1 = datetime(2026, 9, 23, 12, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 9, 23, 12, 0, 1, tzinfo=timezone.utc)

        self.observer.handle_event(self._event(
            event_id="c1", execution_id="ex_dur", event_type=EventType.TOOL_CALLED,
            timestamp=t1, payload={"tool_name": "t1", "call_id": "call_t1"}
        ))
        self.observer.handle_event(self._event(
            event_id="c2", execution_id="ex_dur", event_type=EventType.TOOL_COMPLETED,
            timestamp=t2, payload={"tool_name": "t1", "call_id": "call_t1", "success": True}
        ))
        inv = self.observer.get_invocation("ex_dur", "call_t1")
        self.assertEqual(inv.duration_ms, 1000.0)

    # 2. Concurrent / Interleaved Tools
    def test_06_concurrent_interleaved_tools(self) -> None:
        """Verify concurrent tool calls are correlated accurately by call_id rather than arrival order."""
        # Call A, Call B, Comp B, Comp A
        self.observer.handle_event(self._event(
            event_id="ca", execution_id="ex_con", event_type=EventType.TOOL_CALLED,
            payload={"tool_name": "tool_A", "call_id": "id_A"}
        ))
        self.observer.handle_event(self._event(
            event_id="cb", execution_id="ex_con", event_type=EventType.TOOL_CALLED,
            payload={"tool_name": "tool_B", "call_id": "id_B"}
        ))
        self.observer.handle_event(self._event(
            event_id="eb", execution_id="ex_con", event_type=EventType.TOOL_COMPLETED,
            payload={"tool_name": "tool_B", "call_id": "id_B", "success": True, "duration_ms": 50.0}
        ))
        self.observer.handle_event(self._event(
            event_id="ea", execution_id="ex_con", event_type=EventType.TOOL_COMPLETED,
            payload={"tool_name": "tool_A", "call_id": "id_A", "success": True, "duration_ms": 120.0}
        ))

        inv_a = self.observer.get_invocation("ex_con", "id_A")
        inv_b = self.observer.get_invocation("ex_con", "id_B")

        self.assertEqual(inv_a.tool_name, "tool_A")
        self.assertEqual(inv_a.duration_ms, 120.0)
        self.assertEqual(inv_b.tool_name, "tool_B")
        self.assertEqual(inv_b.duration_ms, 50.0)

        summary = self.observer.get_execution_summary("ex_con")
        self.assertEqual(summary.total_calls, 2)
        self.assertEqual(summary.completed_calls, 2)
        self.assertEqual(summary.unique_tools, ["tool_A", "tool_B"])
        self.assertEqual(summary.total_duration_ms, 170.0)

    # 3. Deduplication & Out-of-Order Handling
    def test_07_duplicate_events_are_idempotent(self) -> None:
        """Verify duplicate events with identical event_id do not double count tool invocations."""
        ev = self._event(
            event_id="evt_dup",
            execution_id="ex_dup",
            event_type=EventType.TOOL_CALLED,
            payload={"tool_name": "search", "call_id": "call_dup"}
        )
        self.observer.handle_event(ev)
        self.observer.handle_event(ev)

        summary = self.observer.get_execution_summary("ex_dup")
        self.assertEqual(summary.total_calls, 1)
        self.assertEqual(summary.events_count, 1)

    def test_08_out_of_order_completion_before_call(self) -> None:
        """Verify ToolCompleted arriving before ToolCalled is merged safely without losing completion facts."""
        # Completed arrives first
        self.observer.handle_event(self._event(
            event_id="comp_ooo",
            execution_id="ex_ooo",
            event_type=EventType.TOOL_COMPLETED,
            sequence=2,
            payload={"tool_name": "fetch", "call_id": "call_ooo", "success": True, "duration_ms": 80.0}
        ))
        # Delayed call arrives second
        self.observer.handle_event(self._event(
            event_id="call_ooo",
            execution_id="ex_ooo",
            event_type=EventType.TOOL_CALLED,
            sequence=1,
            payload={"tool_name": "fetch", "call_id": "call_ooo", "arguments": {"url": "https://api.test"}}
        ))

        inv = self.observer.get_invocation("ex_ooo", "call_ooo")
        self.assertEqual(inv.status, ToolInvocationStatus.COMPLETED)
        self.assertTrue(inv.success)
        self.assertEqual(inv.duration_ms, 80.0)
        self.assertEqual(inv.arguments, {"url": "https://api.test"})

    # 4. Multi-Execution Isolation
    def test_09_multiple_executions_isolated(self) -> None:
        """Verify tool events from one execution do not mutate another execution's summaries."""
        self.observer.handle_event(self._event(
            event_id="e1", execution_id="exec_A", event_type=EventType.TOOL_CALLED,
            payload={"tool_name": "tool_1", "call_id": "c1"}
        ))
        self.observer.handle_event(self._event(
            event_id="e2", execution_id="exec_B", event_type=EventType.TOOL_CALLED,
            payload={"tool_name": "tool_2", "call_id": "c2"}
        ))

        sum_a = self.observer.get_execution_summary("exec_A")
        sum_b = self.observer.get_execution_summary("exec_B")

        self.assertEqual(sum_a.unique_tools, ["tool_1"])
        self.assertEqual(sum_b.unique_tools, ["tool_2"])
        self.assertIsNone(self.observer.get_invocation("exec_A", "c2"))
        self.assertIsNone(self.observer.get_invocation("exec_B", "c1"))

    # 5. Event Bus Integration & Thread Safety
    def test_10_event_bus_integration(self) -> None:
        """Verify ToolActivityObserver attaches to and detaches from EventBus cleanly."""
        bus = InMemoryEventBus()
        sub_ids = self.observer.attach_to_bus(bus)
        self.assertEqual(len(sub_ids), 2)

        bus.publish(self._event(
            event_id="bus_call",
            execution_id="exec_bus",
            event_type=EventType.TOOL_CALLED,
            payload={"tool_name": "bus_tool", "call_id": "b1"}
        ))
        bus.publish(self._event(
            event_id="bus_comp",
            execution_id="exec_bus",
            event_type=EventType.TOOL_COMPLETED,
            payload={"tool_name": "bus_tool", "call_id": "b1", "success": True, "duration_ms": 22.0}
        ))

        summary = self.observer.get_execution_summary("exec_bus")
        self.assertIsNotNone(summary)
        self.assertEqual(summary.completed_calls, 1)

        self.observer.detach_from_bus(bus)
        self.assertEqual(len(self.observer._subscription_ids), 0)

    def test_11_concurrent_thread_safety(self) -> None:
        """Verify thread-safe event handling during concurrent multi-threaded execution."""
        threads = []
        for i in range(10):
            ev = self._event(
                event_id=f"th_call_{i}",
                execution_id=f"exec_th_{i}",
                event_type=EventType.TOOL_CALLED,
                payload={"tool_name": "tool_th", "call_id": f"c_{i}"}
            )
            t = threading.Thread(target=self.observer.handle_event, args=(ev,))
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(self.observer.list_execution_summaries()), 10)

    # 6. Architectural Isolation Checks
    def test_12_zero_database_imports_in_tools_package(self) -> None:
        """Verify tools package contains zero database library imports."""
        import infuse.tools
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.tools")]

        forbidden = ["sqlite3", "psycopg2", "asyncpg", "sqlalchemy", "redis", "qdrant_client", "motor", "pymongo"]
        for mod in modules:
            src = inspect.getsource(mod)
            for f in forbidden:
                self.assertNotIn(f"import {f}", src)
                self.assertNotIn(f"from {f}", src)

    def test_13_zero_provider_and_broker_sdk_imports(self) -> None:
        """Verify tools package contains zero provider or message broker SDK imports."""
        import infuse.tools
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.tools")]

        forbidden = [
            "openai", "anthropic", "google.generativeai", "cohere", "langchain", "crewai", "autogen",
            "kafka", "pika", "nats", "redis", "aioredis", "celery", "kombu"
        ]
        for mod in modules:
            src = inspect.getsource(mod)
            for f in forbidden:
                self.assertNotIn(f"import {f}", src)
                self.assertNotIn(f"from {f}", src)

    def test_14_zero_tool_execution_mcp_policy_or_governor_logic(self) -> None:
        """Verify tools package contains zero tool execution, subprocesses, MCP server, policy, or Governor logic."""
        import infuse.tools
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.tools")]

        forbidden_patterns = [
            "subprocess",
            "eval(",
            "exec(",
            "requests.post",
            "httpx.post",
            "socket.socket",
            "mcp.server",
            "authorize_tool",
            "deny_tool",
            "execute_tool",
            "apply_governance",
            "stop_execution"
        ]
        for mod in modules:
            src = inspect.getsource(mod)
            for p in forbidden_patterns:
                self.assertNotIn(p, src)


if __name__ == "__main__":
    unittest.main()
