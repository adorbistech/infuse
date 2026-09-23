"""Comprehensive Unit, Integration, and Isolation Test Suite for Block 19 Web Activity Observer."""

import inspect
import sys
import threading
import unittest
from datetime import datetime, timedelta, timezone
from typing import Optional

from infuse.contracts.events import EventSource, EventType, ExecutionEvent
from infuse.events.bus import InMemoryEventBus
from infuse.web.models import (
    ExecutionWebSummary,
    WebActivityRecord,
    WebActivityStatus,
    WebObservationCompleteness,
)
from infuse.web.observer import WebActivityObserver


class TestWebActivityObserver(unittest.TestCase):
    """Test suite verifying web activity event consumption, correlation, aggregation, and isolation."""

    def setUp(self) -> None:
        self.observer = WebActivityObserver()

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

    # 1. Single WebRequest
    def test_01_single_web_request(self) -> None:
        """Verify single WebRequest records URL, method, and marks status as REQUESTED/incomplete."""
        ev = self._event(
            event_id="req_01",
            execution_id="exec_01",
            event_type=EventType.WEB_REQUEST,
            sequence=1,
            payload={"url": "https://api.example.com/v1/data", "method": "GET", "request_id": "r_01"}
        )
        res = self.observer.handle_event(ev)
        self.assertIsNotNone(res)
        self.assertEqual(res.total_requests, 1)
        self.assertEqual(res.incomplete_requests, 1)
        self.assertEqual(res.completed_requests, 0)
        self.assertEqual(res.unique_targets, ["https://api.example.com/v1/data"])
        self.assertEqual(res.completeness, WebObservationCompleteness.PARTIAL)

        act = self.observer.get_activity("exec_01", "r_01")
        self.assertIsNotNone(act)
        self.assertEqual(act.url, "https://api.example.com/v1/data")
        self.assertEqual(act.method, "GET")
        self.assertEqual(act.status, WebActivityStatus.REQUESTED)
        self.assertIsNone(act.status_code)
        self.assertIsNone(act.duration_ms)
        self.assertIsNone(act.success)

    # 2. Single WebRequest + WebResponse
    def test_02_web_request_and_response_lifecycle(self) -> None:
        """Verify WebRequest and WebResponse lifecycle correlation and metrics completion."""
        t1 = datetime.now(timezone.utc)
        self.observer.handle_event(self._event(
            event_id="req_02",
            execution_id="exec_02",
            event_type=EventType.WEB_REQUEST,
            timestamp=t1,
            payload={"url": "https://api.example.com/items", "method": "POST", "request_id": "r_02"}
        ))
        t2 = t1 + timedelta(milliseconds=120)
        res = self.observer.handle_event(self._event(
            event_id="resp_02",
            execution_id="exec_02",
            event_type=EventType.WEB_RESPONSE,
            timestamp=t2,
            payload={"url": "https://api.example.com/items", "request_id": "r_02", "status_code": 201, "duration_ms": 120.0}
        ))
        self.assertEqual(res.total_requests, 1)
        self.assertEqual(res.completed_requests, 1)
        self.assertEqual(res.successful_requests, 1)
        self.assertEqual(res.failed_requests, 0)
        self.assertEqual(res.incomplete_requests, 0)
        self.assertEqual(res.total_duration_ms, 120.0)
        self.assertEqual(res.avg_duration_ms, 120.0)
        self.assertEqual(res.completeness, WebObservationCompleteness.COMPLETE)

    # 3. Successful Response
    def test_03_successful_response_200_ok(self) -> None:
        """Verify HTTP 200 response is marked as COMPLETED and success=True."""
        self.observer.handle_event(self._event(
            event_id="req_03", execution_id="ex_03", event_type=EventType.WEB_REQUEST,
            payload={"url": "https://service.org/status", "request_id": "r_03"}
        ))
        res = self.observer.handle_event(self._event(
            event_id="resp_03", execution_id="ex_03", event_type=EventType.WEB_RESPONSE,
            payload={"url": "https://service.org/status", "request_id": "r_03", "status_code": 200}
        ))
        self.assertEqual(res.successful_requests, 1)
        self.assertEqual(res.failed_requests, 0)
        act = self.observer.get_activity("ex_03", "r_03")
        self.assertTrue(act.success)
        self.assertEqual(act.status, WebActivityStatus.COMPLETED)

    # 4. Explicit Failed Response (HTTP 500)
    def test_04_explicit_failed_response_500(self) -> None:
        """Verify HTTP 500 status code marks activity as FAILED and success=False."""
        self.observer.handle_event(self._event(
            event_id="req_04", execution_id="ex_04", event_type=EventType.WEB_REQUEST,
            payload={"url": "https://api.test/fail", "request_id": "r_04"}
        ))
        res = self.observer.handle_event(self._event(
            event_id="resp_04", execution_id="ex_04", event_type=EventType.WEB_RESPONSE,
            payload={"url": "https://api.test/fail", "request_id": "r_04", "status_code": 500}
        ))
        self.assertEqual(res.failed_requests, 1)
        self.assertEqual(res.successful_requests, 0)
        act = self.observer.get_activity("ex_04", "r_04")
        self.assertFalse(act.success)
        self.assertEqual(act.status, WebActivityStatus.FAILED)
        self.assertIn("500", act.error)

    # 5. Response containing error payload
    def test_05_response_containing_error_payload(self) -> None:
        """Verify response with explicit error field is marked as FAILED with error captured."""
        self.observer.handle_event(self._event(
            event_id="req_05", execution_id="ex_05", event_type=EventType.WEB_REQUEST,
            payload={"url": "https://api.test/timeout", "request_id": "r_05"}
        ))
        res = self.observer.handle_event(self._event(
            event_id="resp_05", execution_id="ex_05", event_type=EventType.WEB_RESPONSE,
            payload={"url": "https://api.test/timeout", "request_id": "r_05", "error": "Connection timed out"}
        ))
        self.assertEqual(res.failed_requests, 1)
        act = self.observer.get_activity("ex_05", "r_05")
        self.assertFalse(act.success)
        self.assertEqual(act.error, "Connection timed out")

    # 6. Missing Response
    def test_06_missing_response_remains_incomplete(self) -> None:
        """Verify request with no matching response remains in REQUESTED status and never assumed failed."""
        res = self.observer.handle_event(self._event(
            event_id="req_06", execution_id="ex_06", event_type=EventType.WEB_REQUEST,
            payload={"url": "https://api.test/pending", "request_id": "r_06"}
        ))
        self.assertEqual(res.incomplete_requests, 1)
        self.assertEqual(res.failed_requests, 0)
        self.assertEqual(res.completeness, WebObservationCompleteness.PARTIAL)

    # 7. Explicit duration in payload
    def test_07_explicit_duration_preferred(self) -> None:
        """Verify explicit duration_ms from payload is preferred over timestamp math."""
        t1 = datetime(2026, 9, 23, 10, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 9, 23, 10, 0, 5, tzinfo=timezone.utc)  # 5000ms delta

        self.observer.handle_event(self._event(
            event_id="req_07", execution_id="ex_07", event_type=EventType.WEB_REQUEST,
            timestamp=t1, payload={"url": "https://api.test/fast", "request_id": "r_07"}
        ))
        self.observer.handle_event(self._event(
            event_id="resp_07", execution_id="ex_07", event_type=EventType.WEB_RESPONSE,
            timestamp=t2, payload={"url": "https://api.test/fast", "request_id": "r_07", "status_code": 200, "duration_ms": 42.5}
        ))
        act = self.observer.get_activity("ex_07", "r_07")
        self.assertEqual(act.duration_ms, 42.5)

    # 8. Timestamp-derived duration
    def test_08_timestamp_derived_duration(self) -> None:
        """Verify duration is derived from timestamps when payload duration_ms is omitted."""
        t1 = datetime(2026, 9, 23, 10, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 9, 23, 10, 0, 1, 500000, tzinfo=timezone.utc)  # 1500ms

        self.observer.handle_event(self._event(
            event_id="req_08", execution_id="ex_08", event_type=EventType.WEB_REQUEST,
            timestamp=t1, payload={"url": "https://api.test/calc", "request_id": "r_08"}
        ))
        self.observer.handle_event(self._event(
            event_id="resp_08", execution_id="ex_08", event_type=EventType.WEB_RESPONSE,
            timestamp=t2, payload={"url": "https://api.test/calc", "request_id": "r_08", "status_code": 200}
        ))
        act = self.observer.get_activity("ex_08", "r_08")
        self.assertEqual(act.duration_ms, 1500.0)

    # 9. Missing duration
    def test_09_missing_duration_preserved_as_none(self) -> None:
        """Verify unobservable duration remains None and is never fabricated as 0.0."""
        self.observer.handle_event(self._event(
            event_id="req_09", execution_id="ex_09", event_type=EventType.WEB_REQUEST,
            payload={"url": "https://api.test/nodur", "request_id": "r_09"}
        ))
        act = self.observer.get_activity("ex_09", "r_09")
        self.assertIsNone(act.duration_ms)

    # 10. Invalid / negative duration
    def test_10_negative_duration_handled_safely(self) -> None:
        """Verify invalid negative duration is treated as unobservable None."""
        self.observer.handle_event(self._event(
            event_id="req_10", execution_id="ex_10", event_type=EventType.WEB_REQUEST,
            payload={"url": "https://api.test/neg", "request_id": "r_10"}
        ))
        self.observer.handle_event(self._event(
            event_id="resp_10", execution_id="ex_10", event_type=EventType.WEB_RESPONSE,
            payload={"url": "https://api.test/neg", "request_id": "r_10", "status_code": 200, "duration_ms": -50.0}
        ))
        act = self.observer.get_activity("ex_10", "r_10")
        self.assertIsNone(act.duration_ms)

    # 11. Response-before-request (out-of-order)
    def test_11_response_before_request_out_of_order(self) -> None:
        """Verify WebResponse arriving before WebRequest is preserved and merged without fact loss."""
        # Response arrives first
        self.observer.handle_event(self._event(
            event_id="resp_11", execution_id="ex_11", event_type=EventType.WEB_RESPONSE,
            sequence=2, payload={"url": "https://api.test/ooo", "request_id": "r_11", "status_code": 200, "duration_ms": 75.0}
        ))
        # Delayed request arrives second
        self.observer.handle_event(self._event(
            event_id="req_11", execution_id="ex_11", event_type=EventType.WEB_REQUEST,
            sequence=1, payload={"url": "https://api.test/ooo", "method": "GET", "request_id": "r_11"}
        ))

        act = self.observer.get_activity("ex_11", "r_11")
        self.assertEqual(act.status, WebActivityStatus.COMPLETED)
        self.assertEqual(act.status_code, 200)
        self.assertEqual(act.duration_ms, 75.0)
        self.assertEqual(act.method, "GET")

    # 12. Request-before-response (standard order)
    def test_12_request_before_response_standard_order(self) -> None:
        """Verify standard request then response order."""
        self.observer.handle_event(self._event(
            event_id="req_12", execution_id="ex_12", event_type=EventType.WEB_REQUEST,
            payload={"url": "https://api.test/std", "request_id": "r_12"}
        ))
        self.observer.handle_event(self._event(
            event_id="resp_12", execution_id="ex_12", event_type=EventType.WEB_RESPONSE,
            payload={"url": "https://api.test/std", "request_id": "r_12", "status_code": 200}
        ))
        act = self.observer.get_activity("ex_12", "r_12")
        self.assertEqual(act.status, WebActivityStatus.COMPLETED)

    # 13. Duplicate WebRequest
    def test_13_duplicate_web_request_idempotent(self) -> None:
        """Verify duplicate WebRequest event delivery does not double count requests."""
        ev = self._event(
            event_id="req_13", execution_id="ex_13", event_type=EventType.WEB_REQUEST,
            payload={"url": "https://api.test/dup", "request_id": "r_13"}
        )
        self.observer.handle_event(ev)
        self.observer.handle_event(ev)

        summary = self.observer.get_execution_summary("ex_13")
        self.assertEqual(summary.total_requests, 1)
        self.assertEqual(summary.events_count, 1)

    # 14. Duplicate WebResponse
    def test_14_duplicate_web_response_idempotent(self) -> None:
        """Verify duplicate WebResponse event delivery does not double count responses or duration."""
        self.observer.handle_event(self._event(
            event_id="req_14", execution_id="ex_14", event_type=EventType.WEB_REQUEST,
            payload={"url": "https://api.test/dup_resp", "request_id": "r_14"}
        ))
        ev_resp = self._event(
            event_id="resp_14", execution_id="ex_14", event_type=EventType.WEB_RESPONSE,
            payload={"url": "https://api.test/dup_resp", "request_id": "r_14", "status_code": 200, "duration_ms": 100.0}
        )
        self.observer.handle_event(ev_resp)
        self.observer.handle_event(ev_resp)

        summary = self.observer.get_execution_summary("ex_14")
        self.assertEqual(summary.total_requests, 1)
        self.assertEqual(summary.completed_requests, 1)
        self.assertEqual(summary.total_duration_ms, 100.0)

    # 15. Duplicate event across delivery
    def test_15_duplicate_event_across_delivery(self) -> None:
        """Verify repeated delivery of same event_id produces unchanged immutable summary."""
        ev = self._event(
            event_id="evt_same", execution_id="ex_same", event_type=EventType.WEB_REQUEST,
            payload={"url": "https://api.test/x", "request_id": "r_same"}
        )
        res1 = self.observer.handle_event(ev)
        res2 = self.observer.handle_event(ev)
        self.assertEqual(res1.model_dump(), res2.model_dump())

    # 16. Conflicting event identity / Deduplication
    def test_16_conflicting_event_identity(self) -> None:
        """Verify event_id deduplication takes precedence over payload contents."""
        ev1 = self._event(
            event_id="ev_fixed", execution_id="ex_conflict", event_type=EventType.WEB_REQUEST,
            payload={"url": "https://api.test/first", "request_id": "r_conf"}
        )
        ev2 = self._event(
            event_id="ev_fixed", execution_id="ex_conflict", event_type=EventType.WEB_REQUEST,
            payload={"url": "https://api.test/second", "request_id": "r_conf"}
        )
        self.observer.handle_event(ev1)
        self.observer.handle_event(ev2)
        summary = self.observer.get_execution_summary("ex_conflict")
        self.assertEqual(summary.unique_targets, ["https://api.test/first"])

    # 17. Concurrent requests
    def test_17_concurrent_requests(self) -> None:
        """Verify multiple concurrent requests are tracked independently."""
        self.observer.handle_event(self._event(
            event_id="req_a", execution_id="ex_con", event_type=EventType.WEB_REQUEST,
            payload={"url": "https://api.test/a", "request_id": "r_a"}
        ))
        self.observer.handle_event(self._event(
            event_id="req_b", execution_id="ex_con", event_type=EventType.WEB_REQUEST,
            payload={"url": "https://api.test/b", "request_id": "r_b"}
        ))
        summary = self.observer.get_execution_summary("ex_con")
        self.assertEqual(summary.total_requests, 2)
        self.assertEqual(summary.incomplete_requests, 2)

    # 18. Interleaved responses
    def test_18_interleaved_responses(self) -> None:
        """Verify interleaved responses match accurately by request_id (Req A, Req B, Resp B, Resp A)."""
        self.observer.handle_event(self._event(
            event_id="qa", execution_id="ex_intl", event_type=EventType.WEB_REQUEST,
            payload={"url": "https://api.test/a", "request_id": "id_a"}
        ))
        self.observer.handle_event(self._event(
            event_id="qb", execution_id="ex_intl", event_type=EventType.WEB_REQUEST,
            payload={"url": "https://api.test/b", "request_id": "id_b"}
        ))
        self.observer.handle_event(self._event(
            event_id="sb", execution_id="ex_intl", event_type=EventType.WEB_RESPONSE,
            payload={"url": "https://api.test/b", "request_id": "id_b", "status_code": 200, "duration_ms": 30.0}
        ))
        self.observer.handle_event(self._event(
            event_id="sa", execution_id="ex_intl", event_type=EventType.WEB_RESPONSE,
            payload={"url": "https://api.test/a", "request_id": "id_a", "status_code": 201, "duration_ms": 70.0}
        ))

        act_a = self.observer.get_activity("ex_intl", "id_a")
        act_b = self.observer.get_activity("ex_intl", "id_b")
        self.assertEqual(act_a.duration_ms, 70.0)
        self.assertEqual(act_b.duration_ms, 30.0)
        self.assertEqual(self.observer.get_execution_summary("ex_intl").total_duration_ms, 100.0)

    # 19. Multiple executions
    def test_19_multiple_executions(self) -> None:
        """Verify multiple executions are tracked simultaneously in memory."""
        self.observer.handle_event(self._event(
            event_id="r1", execution_id="run_1", event_type=EventType.WEB_REQUEST,
            payload={"url": "https://one.com", "request_id": "r1"}
        ))
        self.observer.handle_event(self._event(
            event_id="r2", execution_id="run_2", event_type=EventType.WEB_REQUEST,
            payload={"url": "https://two.com", "request_id": "r2"}
        ))
        summaries = self.observer.list_execution_summaries()
        self.assertEqual(len(summaries), 2)

    # 20. Execution isolation
    def test_20_execution_isolation(self) -> None:
        """Verify events from Execution A never mutate Execution B."""
        self.observer.handle_event(self._event(
            event_id="ea1", execution_id="exec_A", event_type=EventType.WEB_REQUEST,
            payload={"url": "https://a.com", "request_id": "r_a"}
        ))
        self.observer.handle_event(self._event(
            event_id="eb1", execution_id="exec_B", event_type=EventType.WEB_REQUEST,
            payload={"url": "https://b.com", "request_id": "r_b"}
        ))
        sum_a = self.observer.get_execution_summary("exec_A")
        sum_b = self.observer.get_execution_summary("exec_B")
        self.assertEqual(sum_a.unique_targets, ["https://a.com"])
        self.assertEqual(sum_b.unique_targets, ["https://b.com"])
        self.assertIsNone(self.observer.get_activity("exec_A", "r_b"))

    # 21. Multiple unique targets
    def test_21_multiple_unique_targets(self) -> None:
        """Verify unique_targets contains sorted distinct target URLs."""
        for i, url in enumerate(["https://z.com", "https://a.com", "https://m.com"]):
            self.observer.handle_event(self._event(
                event_id=f"u_{i}", execution_id="ex_uniq", event_type=EventType.WEB_REQUEST,
                payload={"url": url, "request_id": f"rq_{i}"}
            ))
        summary = self.observer.get_execution_summary("ex_uniq")
        self.assertEqual(summary.unique_targets, ["https://a.com", "https://m.com", "https://z.com"])

    # 22. Repeated same target
    def test_22_repeated_same_target_deduplicated_in_summary(self) -> None:
        """Verify multiple calls to same URL only produce a single entry in unique_targets."""
        for i in range(3):
            self.observer.handle_event(self._event(
                event_id=f"rep_{i}", execution_id="ex_rep", event_type=EventType.WEB_REQUEST,
                payload={"url": "https://api.test/same", "request_id": f"req_{i}"}
            ))
        summary = self.observer.get_execution_summary("ex_rep")
        self.assertEqual(summary.total_requests, 3)
        self.assertEqual(summary.unique_targets, ["https://api.test/same"])

    # 23. HTTP Method capture
    def test_23_http_method_capture(self) -> None:
        """Verify various HTTP methods are recorded accurately."""
        methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]
        for i, m in enumerate(methods):
            self.observer.handle_event(self._event(
                event_id=f"m_{i}", execution_id="ex_methods", event_type=EventType.WEB_REQUEST,
                payload={"url": f"https://api.test/{m.lower()}", "method": m, "request_id": f"req_{m}"}
            ))
            act = self.observer.get_activity("ex_methods", f"req_{m}")
            self.assertEqual(act.method, m)

    # 24. Status code capture
    def test_24_status_code_capture(self) -> None:
        """Verify status codes (404, 429, 503) are captured and categorized as failures."""
        codes = [404, 429, 503]
        for c in codes:
            self.observer.handle_event(self._event(
                event_id=f"req_{c}", execution_id="ex_codes", event_type=EventType.WEB_REQUEST,
                payload={"url": f"https://api.test/{c}", "request_id": f"r_{c}"}
            ))
            self.observer.handle_event(self._event(
                event_id=f"resp_{c}", execution_id="ex_codes", event_type=EventType.WEB_RESPONSE,
                payload={"url": f"https://api.test/{c}", "request_id": f"r_{c}", "status_code": c}
            ))
            act = self.observer.get_activity("ex_codes", f"r_{c}")
            self.assertEqual(act.status_code, c)
            self.assertFalse(act.success)
            self.assertEqual(act.status, WebActivityStatus.FAILED)

    # 25. Bytes transferred accumulation
    def test_25_bytes_transferred_accumulation(self) -> None:
        """Verify total_bytes_transferred correctly sums payload byte counts."""
        self.observer.handle_event(self._event(
            event_id="rq1", execution_id="ex_bytes", event_type=EventType.WEB_REQUEST,
            payload={"url": "https://a.com", "request_id": "r1"}
        ))
        self.observer.handle_event(self._event(
            event_id="rs1", execution_id="ex_bytes", event_type=EventType.WEB_RESPONSE,
            payload={"url": "https://a.com", "request_id": "r1", "status_code": 200, "bytes_transferred": 1024}
        ))
        self.observer.handle_event(self._event(
            event_id="rq2", execution_id="ex_bytes", event_type=EventType.WEB_REQUEST,
            payload={"url": "https://b.com", "request_id": "r2"}
        ))
        self.observer.handle_event(self._event(
            event_id="rs2", execution_id="ex_bytes", event_type=EventType.WEB_RESPONSE,
            payload={"url": "https://b.com", "request_id": "r2", "status_code": 200, "bytes_transferred": 2048}
        ))
        summary = self.observer.get_execution_summary("ex_bytes")
        self.assertEqual(summary.total_bytes_transferred, 3072)

    # 26. Unknown / Optional fields
    def test_26_unknown_optional_fields_graceful_fallback(self) -> None:
        """Verify events with empty/sparse payloads don't crash and default safely."""
        self.observer.handle_event(self._event(
            event_id="sparse_req", execution_id="ex_sparse", event_type=EventType.WEB_REQUEST,
            payload={}
        ))
        self.observer.handle_event(self._event(
            event_id="sparse_resp", execution_id="ex_sparse", event_type=EventType.WEB_RESPONSE,
            payload={}
        ))
        summary = self.observer.get_execution_summary("ex_sparse")
        self.assertEqual(summary.total_requests, 1)

    # 27. Incomplete observation state
    def test_27_incomplete_observation_state(self) -> None:
        """Verify completeness is PARTIAL when some requests remain unanswered."""
        self.observer.handle_event(self._event(
            event_id="q1", execution_id="ex_part", event_type=EventType.WEB_REQUEST,
            payload={"url": "https://a.com", "request_id": "r1"}
        ))
        self.observer.handle_event(self._event(
            event_id="s1", execution_id="ex_part", event_type=EventType.WEB_RESPONSE,
            payload={"url": "https://a.com", "request_id": "r1", "status_code": 200}
        ))
        self.observer.handle_event(self._event(
            event_id="q2", execution_id="ex_part", event_type=EventType.WEB_REQUEST,
            payload={"url": "https://b.com", "request_id": "r2"}
        ))
        summary = self.observer.get_execution_summary("ex_part")
        self.assertEqual(summary.completeness, WebObservationCompleteness.PARTIAL)

    # 28. Deterministic aggregation
    def test_28_deterministic_aggregation(self) -> None:
        """Verify repeated calls to summary calculations yield identical results."""
        self.observer.handle_event(self._event(
            event_id="ra", execution_id="ex_det", event_type=EventType.WEB_REQUEST,
            payload={"url": "https://a.com", "request_id": "ra"}
        ))
        self.observer.handle_event(self._event(
            event_id="sa", execution_id="ex_det", event_type=EventType.WEB_RESPONSE,
            payload={"url": "https://a.com", "request_id": "ra", "status_code": 200, "duration_ms": 50.0}
        ))
        s1 = self.observer.get_execution_summary("ex_det")
        s2 = self.observer.get_execution_summary("ex_det")
        self.assertEqual(s1.model_dump(), s2.model_dump())

    # 29. Average duration calculation
    def test_29_average_duration_calculation(self) -> None:
        """Verify average duration computes correctly and handles missing durations properly."""
        self.observer.handle_event(self._event(
            event_id="r1", execution_id="ex_avg", event_type=EventType.WEB_REQUEST,
            payload={"url": "https://a.com", "request_id": "r1"}
        ))
        self.observer.handle_event(self._event(
            event_id="s1", execution_id="ex_avg", event_type=EventType.WEB_RESPONSE,
            payload={"url": "https://a.com", "request_id": "r1", "duration_ms": 100.0}
        ))
        self.observer.handle_event(self._event(
            event_id="r2", execution_id="ex_avg", event_type=EventType.WEB_REQUEST,
            payload={"url": "https://b.com", "request_id": "r2"}
        ))
        self.observer.handle_event(self._event(
            event_id="s2", execution_id="ex_avg", event_type=EventType.WEB_RESPONSE,
            payload={"url": "https://b.com", "request_id": "r2", "duration_ms": 200.0}
        ))
        summary = self.observer.get_execution_summary("ex_avg")
        self.assertEqual(summary.total_duration_ms, 300.0)
        self.assertEqual(summary.avg_duration_ms, 150.0)

    # 30. Thread safety under concurrent ingestion
    def test_30_thread_safety_concurrent_ingestion(self) -> None:
        """Verify thread-safe event handling during concurrent multi-threaded ingestion."""
        threads = []
        for i in range(12):
            ev = self._event(
                event_id=f"th_req_{i}",
                execution_id=f"exec_th_{i}",
                event_type=EventType.WEB_REQUEST,
                payload={"url": f"https://api.th/{i}", "request_id": f"r_{i}"}
            )
            t = threading.Thread(target=self.observer.handle_event, args=(ev,))
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(self.observer.list_execution_summaries()), 12)

    # 31. Event Bus integration
    def test_31_event_bus_integration(self) -> None:
        """Verify WebActivityObserver attaches to and detaches from EventBus cleanly."""
        bus = InMemoryEventBus()
        sub_ids = self.observer.attach_to_bus(bus)
        self.assertEqual(len(sub_ids), 2)

        bus.publish(self._event(
            event_id="bus_req", execution_id="exec_bus", event_type=EventType.WEB_REQUEST,
            payload={"url": "https://bus.test", "request_id": "b1"}
        ))
        bus.publish(self._event(
            event_id="bus_resp", execution_id="exec_bus", event_type=EventType.WEB_RESPONSE,
            payload={"url": "https://bus.test", "request_id": "b1", "status_code": 200, "duration_ms": 15.0}
        ))

        summary = self.observer.get_execution_summary("exec_bus")
        self.assertIsNotNone(summary)
        self.assertEqual(summary.completed_requests, 1)

        self.observer.detach_from_bus(bus)
        self.assertEqual(len(self.observer._subscription_ids), 0)

    # 32. Zero web request / network calls
    def test_32_zero_web_request_and_network_calls(self) -> None:
        """Verify web package contains zero HTTP clients or network sockets."""
        import infuse.web
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.web")]

        forbidden = [
            "requests.get", "requests.post", "urllib.request", "httpx.get", "httpx.post",
            "aiohttp", "socket.socket", "http.client"
        ]
        for mod in modules:
            src = inspect.getsource(mod)
            for f in forbidden:
                self.assertNotIn(f, src)

    # 33. Zero provider SDK imports
    def test_33_zero_provider_sdk_imports(self) -> None:
        """Verify web package contains zero provider SDK imports."""
        import infuse.web
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.web")]

        forbidden = ["openai", "anthropic", "google.generativeai", "cohere", "langchain", "crewai", "autogen"]
        for mod in modules:
            src = inspect.getsource(mod)
            for f in forbidden:
                self.assertNotIn(f"import {f}", src)
                self.assertNotIn(f"from {f}", src)

    # 34. Zero database imports
    def test_34_zero_database_imports(self) -> None:
        """Verify web package contains zero database library imports."""
        import infuse.web
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.web")]

        forbidden = ["sqlite3", "psycopg2", "asyncpg", "sqlalchemy", "redis", "qdrant_client", "motor", "pymongo"]
        for mod in modules:
            src = inspect.getsource(mod)
            for f in forbidden:
                self.assertNotIn(f"import {f}", src)
                self.assertNotIn(f"from {f}", src)

    # 35. Zero MCP, policy, or Governor logic
    def test_35_zero_mcp_policy_or_governor_logic(self) -> None:
        """Verify web package contains zero MCP server, policy evaluation, or Governor actions."""
        import infuse.web
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.web")]

        forbidden_patterns = [
            "subprocess",
            "mcp.server",
            "authorize_web",
            "deny_web",
            "apply_governance",
            "stop_execution",
            "throttle_execution"
        ]
        for mod in modules:
            src = inspect.getsource(mod)
            for p in forbidden_patterns:
                self.assertNotIn(p, src)


if __name__ == "__main__":
    unittest.main()
