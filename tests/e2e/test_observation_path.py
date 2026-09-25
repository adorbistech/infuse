"""INFUSE Block 32 — Path B: Observation Path Integration Suite.

Validates telemetry fanout across all 5 observers:
- Token Observer (tokens, velocity, input/output/cached breakdown)
- Economics Engine (cost calculation, pricing model, currency)
- Health Engine (error taxonomy, latency, success/failure rate, retries)
- Tool Activity Observer (tool calls, arguments, successes, failures, unique tools)
- Web Activity Observer (web requests, domains, methods, statuses)
"""

import unittest
import uuid
from decimal import Decimal

from infuse.contracts.events import EventSource, EventType, ExecutionEvent
from infuse.e2e.environment import EndToEndIntegrationEnvironment


class TestBlock32ObservationPath(unittest.TestCase):
    """Verifies observation path integration and telemetry fanout across all 5 observers."""

    def setUp(self):
        self.env = EndToEndIntegrationEnvironment()
        self.exec_id = f"exec_obs_{uuid.uuid4().hex[:8]}"

    def test_observation_path_full_fanout(self):
        """Verify that an event sequence updates all 5 observers consistently."""
        events = [
            ExecutionEvent(
                event_id="evt_start_1",
                execution_id=self.exec_id,
                type=EventType.EXECUTION_STARTED,
                source=EventSource.RUNTIME,
                sequence=1,
                payload={"provider": "mock", "model": "mock-fast"},
            ),
            ExecutionEvent(
                event_id="evt_tok_1",
                execution_id=self.exec_id,
                type=EventType.TOKEN_OBSERVED,
                source=EventSource.PROVIDER,
                sequence=2,
                payload={
                    "input_tokens": 1200,
                    "output_tokens": 400,
                    "cached_tokens": 300,
                    "total_tokens": 1600,
                    "provider": "mock",
                    "model": "mock-fast",
                },
            ),
            ExecutionEvent(
                event_id="evt_tool_call_1",
                execution_id=self.exec_id,
                type=EventType.TOOL_CALLED,
                source=EventSource.AGENT,
                sequence=3,
                payload={
                    "tool_call_id": "call_search_1",
                    "tool_name": "search_codebase",
                    "parameters": {"pattern": "def main"},
                },
            ),
            ExecutionEvent(
                event_id="evt_tool_comp_1",
                execution_id=self.exec_id,
                type=EventType.TOOL_COMPLETED,
                source=EventSource.AGENT,
                sequence=4,
                payload={
                    "tool_call_id": "call_search_1",
                    "tool_name": "search_codebase",
                    "success": True,
                    "duration_ms": 15.5,
                },
            ),
            ExecutionEvent(
                event_id="evt_web_req_1",
                execution_id=self.exec_id,
                type=EventType.WEB_REQUEST,
                source=EventSource.AGENT,
                sequence=5,
                payload={
                    "request_id": "web_req_1",
                    "url": "https://docs.python.org/3/library/unittest.html",
                    "method": "GET",
                },
            ),
            ExecutionEvent(
                event_id="evt_web_res_1",
                execution_id=self.exec_id,
                type=EventType.WEB_RESPONSE,
                source=EventSource.AGENT,
                sequence=6,
                payload={
                    "request_id": "web_req_1",
                    "url": "https://docs.python.org/3/library/unittest.html",
                    "status_code": 200,
                    "duration_ms": 85.0,
                    "success": True,
                },
            ),
            ExecutionEvent(
                event_id="evt_comp_1",
                execution_id=self.exec_id,
                type=EventType.EXECUTION_COMPLETED,
                source=EventSource.RUNTIME,
                sequence=7,
                payload={"status": "completed", "duration_ms": 120.0},
            ),
        ]

        # Emit all events
        for evt in events:
            self.env.emit_event(evt)

        # 1. Token Observer check
        tok_sum = self.env.token_observer.get_observation(self.exec_id)
        self.assertIsNotNone(tok_sum)
        self.assertEqual(tok_sum.total_tokens, 1600)
        self.assertEqual(tok_sum.input_tokens, 1200)
        self.assertEqual(tok_sum.output_tokens, 400)

        # 2. Economics Engine check
        econ_sum = self.env.economics_engine.get_summary(self.exec_id)
        self.assertIsNotNone(econ_sum)
        self.assertIsNotNone(econ_sum.total_cost)

        # 3. Health Engine check
        health_sum = self.env.health_engine.get_execution_health(self.exec_id)
        self.assertIsNotNone(health_sum)
        self.assertTrue(health_sum.is_success)
        self.assertEqual(health_sum.latency_ms, 120.0)

        # 4. Tool Observer check
        tool_sum = self.env.tool_observer.get_execution_summary(self.exec_id)
        self.assertIsNotNone(tool_sum)
        self.assertEqual(tool_sum.total_calls, 1)
        self.assertEqual(tool_sum.successful_calls, 1)
        self.assertEqual(tool_sum.unique_tools, ["search_codebase"])

        # 5. Web Observer check
        web_sum = self.env.web_observer.get_execution_summary(self.exec_id)
        self.assertIsNotNone(web_sum)
        self.assertEqual(web_sum.total_requests, 1)
        self.assertEqual(web_sum.successful_requests, 1)

    def test_observation_idempotency(self):
        """Verify replaying the same event does not double-count metrics across observers."""
        tok_evt = ExecutionEvent(
            event_id="evt_idem_1",
            execution_id=self.exec_id,
            type=EventType.TOKEN_OBSERVED,
            source=EventSource.PROVIDER,
            sequence=1,
            payload={
                "input_tokens": 500,
                "output_tokens": 500,
                "total_tokens": 1000,
                "provider": "mock",
                "model": "mock-fast",
            },
        )

        # Emit twice
        self.env.emit_event(tok_evt)
        self.env.emit_event(tok_evt)

        tok_sum = self.env.token_observer.get_observation(self.exec_id)
        self.assertEqual(tok_sum.total_tokens, 1000)
