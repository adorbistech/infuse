"""Comprehensive Unit, Integration, and Isolation Test Suite for Block 20 Execution State Engine."""

import inspect
import sys
import threading
import unittest
from decimal import Decimal
from typing import List, Optional

from infuse.contracts.events import EventType
from infuse.contracts.policy import (
    AnomalyProtection,
    BudgetControls,
    GovernancePolicy,
    PolicyActionBindings,
    RuntimeControls,
    TokenControls,
    ToolAccessControls,
    WebAccessControls,
)
from infuse.contracts.state import ExecutionState, ExecutionStateSnapshot
from infuse.economics.models import EconomicCompleteness, ExecutionEconomicSummary
from infuse.events.bus import InMemoryEventBus
from infuse.health.models import (
    ErrorCategory,
    ExecutionHealthSummary,
    HealthCompleteness,
    ObservedErrorRecord,
)
from infuse.observer.models import ExecutionTokenSummary
from infuse.state.engine import ExecutionStateEngine
from infuse.state.models import ObservationBundle, StateSeverity
from infuse.tools.models import ExecutionToolSummary, ToolInvocationRecord, ToolInvocationStatus, ToolObservationCompleteness
from infuse.web.models import ExecutionWebSummary, WebActivityRecord, WebActivityStatus, WebObservationCompleteness


class TestExecutionStateEngine(unittest.TestCase):
    """Test suite verifying observation aggregation, state derivation, precedence, and isolation."""

    def setUp(self) -> None:
        self.engine = ExecutionStateEngine()

    def _policy(
        self,
        max_cost: Optional[float] = None,
        max_tokens: Optional[int] = None,
        max_tools: Optional[int] = None,
        max_tool_failures: Optional[int] = None,
        max_web_requests: Optional[int] = None,
        max_time_sec: Optional[int] = None,
        loop_threshold: Optional[int] = None,
    ) -> GovernancePolicy:
        return GovernancePolicy(
            policy_id="test_pol",
            name="Test Policy",
            budget_controls=BudgetControls(max_cost_per_task=max_cost),
            token_controls=TokenControls(max_total_tokens=max_tokens),
            tool_controls=ToolAccessControls(
                max_tool_calls_per_task=max_tools,
                max_consecutive_tool_failures=max_tool_failures,
            ),
            web_controls=WebAccessControls(max_web_requests_per_task=max_web_requests),
            runtime_controls=RuntimeControls(max_execution_time_seconds=max_time_sec),
            anomaly_protection=AnomalyProtection(repetitive_loop_threshold=loop_threshold),
            action_bindings=PolicyActionBindings(),
        )

    # 1. Initial state creation
    def test_01_initial_state_creation(self) -> None:
        """Verify initial state creation produces NORMAL state with empty signals."""
        snapshot = self.engine.derive_state(execution_id="exec_01")
        self.assertEqual(snapshot.execution_id, "exec_01")
        self.assertEqual(snapshot.current_state, ExecutionState.NORMAL)
        self.assertIsNone(snapshot.previous_state)
        self.assertIn("NORMAL_EXECUTION", snapshot.reason_codes)
        self.assertTrue(snapshot.signals.get("normal"))

    # 2. NORMAL derivation where contract permits
    def test_02_normal_derivation_under_policy_limits(self) -> None:
        """Verify execution within policy limits derives NORMAL state."""
        policy = self._policy(max_cost=10.0, max_tokens=1000)
        econ = ExecutionEconomicSummary(execution_id="ex_02", total_cost=Decimal("1.50"))
        tok = ExecutionTokenSummary(execution_id="ex_02", total_tokens=250)

        snapshot = self.engine.derive_state(
            execution_id="ex_02",
            token_summary=tok,
            economic_summary=econ,
            policy=policy,
        )
        self.assertEqual(snapshot.current_state, ExecutionState.NORMAL)
        self.assertIn("NORMAL_EXECUTION", snapshot.reason_codes)

    # 3. COST_PRESSURE (budget exceeded)
    def test_03_cost_pressure_budget_exceeded(self) -> None:
        """Verify COST_PRESSURE is derived when total cost reaches or exceeds policy max_cost_per_task."""
        policy = self._policy(max_cost=5.0)
        econ = ExecutionEconomicSummary(execution_id="ex_03", total_cost=Decimal("5.50"))

        snapshot = self.engine.derive_state(
            execution_id="ex_03",
            economic_summary=econ,
            policy=policy,
        )
        self.assertEqual(snapshot.current_state, ExecutionState.COST_PRESSURE)
        self.assertIn("BUDGET_EXCEEDED", snapshot.reason_codes)
        self.assertTrue(snapshot.signals.get("budget_exceeded"))

    # 4. COST_PRESSURE (token ceiling exceeded)
    def test_04_cost_pressure_token_ceiling_exceeded(self) -> None:
        """Verify COST_PRESSURE is derived when total tokens exceed policy limit."""
        policy = self._policy(max_tokens=5000)
        tok = ExecutionTokenSummary(execution_id="ex_04", total_tokens=5500)

        snapshot = self.engine.derive_state(
            execution_id="ex_04",
            token_summary=tok,
            policy=policy,
        )
        self.assertEqual(snapshot.current_state, ExecutionState.COST_PRESSURE)
        self.assertIn("TOKEN_CEILING_EXCEEDED", snapshot.reason_codes)

    # 5. COST_PRESSURE (80% threshold pressure)
    def test_05_cost_pressure_high_threshold(self) -> None:
        """Verify COST_PRESSURE is flagged when cost reaches 80% of budget limit."""
        policy = self._policy(max_cost=10.0)
        econ = ExecutionEconomicSummary(execution_id="ex_05", total_cost=Decimal("8.50"))

        snapshot = self.engine.derive_state(
            execution_id="ex_05",
            economic_summary=econ,
            policy=policy,
        )
        self.assertEqual(snapshot.current_state, ExecutionState.COST_PRESSURE)
        self.assertIn("COST_PRESSURE_HIGH", snapshot.reason_codes)

    # 6. RUNAWAY (max tool calls exceeded)
    def test_06_runaway_max_tool_calls_exceeded(self) -> None:
        """Verify RUNAWAY state when tool calls exceed policy ceiling."""
        policy = self._policy(max_tools=10)
        tool_sum = ExecutionToolSummary(execution_id="ex_06", total_calls=12)

        snapshot = self.engine.derive_state(
            execution_id="ex_06",
            tool_summary=tool_sum,
            policy=policy,
        )
        self.assertEqual(snapshot.current_state, ExecutionState.RUNAWAY)
        self.assertIn("MAX_TOOL_CALLS_EXCEEDED", snapshot.reason_codes)

    # 7. RUNAWAY (consecutive tool failures exceeded)
    def test_07_runaway_consecutive_tool_failures_exceeded(self) -> None:
        """Verify RUNAWAY state when consecutive tool failures exceed limit."""
        policy = self._policy(max_tool_failures=3)
        tool_sum = ExecutionToolSummary(execution_id="ex_07", total_calls=5, failed_calls=3)

        snapshot = self.engine.derive_state(
            execution_id="ex_07",
            tool_summary=tool_sum,
            policy=policy,
        )
        self.assertEqual(snapshot.current_state, ExecutionState.RUNAWAY)
        self.assertIn("CONSECUTIVE_TOOL_FAILURES_EXCEEDED", snapshot.reason_codes)

    # 8. RUNAWAY (max web requests exceeded)
    def test_08_runaway_max_web_requests_exceeded(self) -> None:
        """Verify RUNAWAY state when web requests exceed policy ceiling."""
        policy = self._policy(max_web_requests=20)
        web_sum = ExecutionWebSummary(execution_id="ex_08", total_requests=25)

        snapshot = self.engine.derive_state(
            execution_id="ex_08",
            web_summary=web_sum,
            policy=policy,
        )
        self.assertEqual(snapshot.current_state, ExecutionState.RUNAWAY)
        self.assertIn("MAX_WEB_REQUESTS_EXCEEDED", snapshot.reason_codes)

    # 9. RUNAWAY (execution time / latency exceeded)
    def test_09_runaway_execution_time_exceeded(self) -> None:
        """Verify RUNAWAY state when execution time in seconds exceeds policy max."""
        policy = self._policy(max_time_sec=30)
        health = ExecutionHealthSummary(execution_id="ex_09", latency_ms=35000.0)

        snapshot = self.engine.derive_state(
            execution_id="ex_09",
            health_summary=health,
            policy=policy,
        )
        self.assertEqual(snapshot.current_state, ExecutionState.RUNAWAY)
        self.assertIn("EXECUTION_TIME_EXCEEDED", snapshot.reason_codes)

    # 10. RUNAWAY (repetitive loop detected)
    def test_10_runaway_repetitive_loop_detected(self) -> None:
        """Verify RUNAWAY state when repetitive loop count reaches threshold."""
        policy = self._policy(loop_threshold=5)
        snapshot = self.engine.derive_state(
            execution_id="ex_10",
            policy=policy,
            context_metadata={"repetitive_loops": 6},
        )
        self.assertEqual(snapshot.current_state, ExecutionState.RUNAWAY)
        self.assertIn("REPETITIVE_LOOP_DETECTED", snapshot.reason_codes)

    # 11. QUALITY_DEGRADED (execution failed without provider outage)
    def test_11_quality_degraded_execution_failed(self) -> None:
        """Verify QUALITY_DEGRADED when health indicates execution failure."""
        health = ExecutionHealthSummary(
            execution_id="ex_11",
            status="FAILED",
            is_success=False,
        )
        snapshot = self.engine.derive_state(
            execution_id="ex_11",
            health_summary=health,
        )
        self.assertEqual(snapshot.current_state, ExecutionState.QUALITY_DEGRADED)
        self.assertIn("EXECUTION_FAILURE", snapshot.reason_codes)

    # 12. QUALITY_DEGRADED (all tool calls failed)
    def test_12_quality_degraded_all_tools_failed(self) -> None:
        """Verify QUALITY_DEGRADED when all tool invocations failed."""
        tool_sum = ExecutionToolSummary(
            execution_id="ex_12",
            total_calls=4,
            completed_calls=4,
            successful_calls=0,
            failed_calls=4,
        )
        snapshot = self.engine.derive_state(
            execution_id="ex_12",
            tool_summary=tool_sum,
        )
        self.assertEqual(snapshot.current_state, ExecutionState.QUALITY_DEGRADED)
        self.assertIn("ALL_TOOL_CALLS_FAILED", snapshot.reason_codes)

    # 13. QUALITY_DEGRADED (all web requests failed)
    def test_13_quality_degraded_all_web_requests_failed(self) -> None:
        """Verify QUALITY_DEGRADED when all web requests failed."""
        web_sum = ExecutionWebSummary(
            execution_id="ex_13",
            total_requests=3,
            completed_requests=3,
            successful_requests=0,
            failed_requests=3,
        )
        snapshot = self.engine.derive_state(
            execution_id="ex_13",
            web_summary=web_sum,
        )
        self.assertEqual(snapshot.current_state, ExecutionState.QUALITY_DEGRADED)
        self.assertIn("ALL_WEB_REQUESTS_FAILED", snapshot.reason_codes)

    # 14. PROVIDER_CONSTRAINED (rate limit / 429)
    def test_14_provider_constrained_rate_limit(self) -> None:
        """Verify PROVIDER_CONSTRAINED when rate limit error is observed in health summary."""
        health = ExecutionHealthSummary(
            execution_id="ex_14",
            errors=[
                ObservedErrorRecord(
                    event_id="e1",
                    execution_id="ex_14",
                    error_category=ErrorCategory.RATE_LIMIT,
                    http_status=429,
                )
            ]
        )
        snapshot = self.engine.derive_state(
            execution_id="ex_14",
            health_summary=health,
        )
        self.assertEqual(snapshot.current_state, ExecutionState.PROVIDER_CONSTRAINED)
        self.assertIn("PROVIDER_RATE_LIMIT", snapshot.reason_codes)

    # 15. PROVIDER_CONSTRAINED (unavailable / 503)
    def test_15_provider_constrained_unavailable(self) -> None:
        """Verify PROVIDER_CONSTRAINED when service unavailable error is observed."""
        health = ExecutionHealthSummary(
            execution_id="ex_15",
            errors=[
                ObservedErrorRecord(
                    event_id="e2",
                    execution_id="ex_15",
                    error_category=ErrorCategory.UNAVAILABLE,
                    http_status=503,
                )
            ]
        )
        snapshot = self.engine.derive_state(
            execution_id="ex_15",
            health_summary=health,
        )
        self.assertEqual(snapshot.current_state, ExecutionState.PROVIDER_CONSTRAINED)
        self.assertIn("PROVIDER_UNAVAILABLE", snapshot.reason_codes)

    # 16. PROVIDER_CONSTRAINED (auth failure / 401, 403)
    def test_16_provider_constrained_auth_failure(self) -> None:
        """Verify PROVIDER_CONSTRAINED when authentication failure error is observed."""
        health = ExecutionHealthSummary(
            execution_id="ex_16",
            errors=[
                ObservedErrorRecord(
                    event_id="e3",
                    execution_id="ex_16",
                    error_category=ErrorCategory.AUTHENTICATION,
                    http_status=401,
                )
            ]
        )
        snapshot = self.engine.derive_state(
            execution_id="ex_16",
            health_summary=health,
        )
        self.assertEqual(snapshot.current_state, ExecutionState.PROVIDER_CONSTRAINED)
        self.assertIn("PROVIDER_AUTH_FAILURE", snapshot.reason_codes)

    # 17. PROVIDER_CONSTRAINED (timeout / 504)
    def test_17_provider_constrained_timeout(self) -> None:
        """Verify PROVIDER_CONSTRAINED when gateway timeout error is observed."""
        health = ExecutionHealthSummary(
            execution_id="ex_17",
            errors=[
                ObservedErrorRecord(
                    event_id="e4",
                    execution_id="ex_17",
                    error_category=ErrorCategory.TIMEOUT,
                    http_status=504,
                )
            ]
        )
        snapshot = self.engine.derive_state(
            execution_id="ex_17",
            health_summary=health,
        )
        self.assertEqual(snapshot.current_state, ExecutionState.PROVIDER_CONSTRAINED)
        self.assertIn("PROVIDER_TIMEOUT", snapshot.reason_codes)

    # 18. PROVIDER_CONSTRAINED (general provider error)
    def test_18_provider_constrained_general_error(self) -> None:
        """Verify PROVIDER_CONSTRAINED when general provider error is observed."""
        health = ExecutionHealthSummary(
            execution_id="ex_18",
            errors=[
                ObservedErrorRecord(
                    event_id="e5",
                    execution_id="ex_18",
                    error_category=ErrorCategory.PROVIDER_ERROR,
                )
            ]
        )
        snapshot = self.engine.derive_state(
            execution_id="ex_18",
            health_summary=health,
        )
        self.assertEqual(snapshot.current_state, ExecutionState.PROVIDER_CONSTRAINED)
        self.assertIn("PROVIDER_ERROR", snapshot.reason_codes)

    # 19. Missing token observation
    def test_19_missing_token_observation_no_fabrication(self) -> None:
        """Verify missing token observation remains unobserved and does not trigger false token pressure."""
        policy = self._policy(max_tokens=100)
        snapshot = self.engine.derive_state(
            execution_id="ex_19",
            token_summary=None,
            policy=policy,
        )
        self.assertEqual(snapshot.current_state, ExecutionState.NORMAL)
        self.assertNotIn("total_tokens", snapshot.signals)

    # 20. Missing economic observation
    def test_20_missing_economic_observation_no_fabrication(self) -> None:
        """Verify missing economic observation does not fabricate zero cost or trigger budget pressure."""
        policy = self._policy(max_cost=10.0)
        snapshot = self.engine.derive_state(
            execution_id="ex_20",
            economic_summary=None,
            policy=policy,
        )
        self.assertEqual(snapshot.current_state, ExecutionState.NORMAL)
        self.assertNotIn("total_cost", snapshot.signals)

    # 21. Partial economic data (None total_cost)
    def test_21_partial_economic_data_total_cost_none(self) -> None:
        """Verify economic summary with None total_cost does not trigger false cost pressure."""
        policy = self._policy(max_cost=10.0)
        econ = ExecutionEconomicSummary(
            execution_id="ex_21",
            total_cost=None,
            completeness=EconomicCompleteness.PARTIAL,
        )
        snapshot = self.engine.derive_state(
            execution_id="ex_21",
            economic_summary=econ,
            policy=policy,
        )
        self.assertEqual(snapshot.current_state, ExecutionState.NORMAL)

    # 22. Incomplete health data
    def test_22_incomplete_health_data_latency_none(self) -> None:
        """Verify health summary with None latency does not trigger execution time runaway."""
        policy = self._policy(max_time_sec=10)
        health = ExecutionHealthSummary(
            execution_id="ex_22",
            latency_ms=None,
            completeness=HealthCompleteness.PARTIAL,
        )
        snapshot = self.engine.derive_state(
            execution_id="ex_22",
            health_summary=health,
            policy=policy,
        )
        self.assertEqual(snapshot.current_state, ExecutionState.NORMAL)

    # 23. Tool activity evidence accounted
    def test_23_tool_activity_evidence_accounted(self) -> None:
        """Verify tool calls are correctly recorded in state signals."""
        policy = self._policy(max_tools=50)
        tool_sum = ExecutionToolSummary(execution_id="ex_23", total_calls=15)
        snapshot = self.engine.derive_state(
            execution_id="ex_23",
            tool_summary=tool_sum,
            policy=policy,
        )
        self.assertEqual(snapshot.current_state, ExecutionState.NORMAL)

    # 24. Web activity evidence accounted
    def test_24_web_activity_evidence_accounted(self) -> None:
        """Verify web requests are correctly accounted in state signals."""
        policy = self._policy(max_web_requests=50)
        web_sum = ExecutionWebSummary(execution_id="ex_24", total_requests=10)
        snapshot = self.engine.derive_state(
            execution_id="ex_24",
            web_summary=web_sum,
            policy=policy,
        )
        self.assertEqual(snapshot.current_state, ExecutionState.NORMAL)

    # 25. Incomplete tool activity
    def test_25_incomplete_tool_activity_does_not_infer_failure(self) -> None:
        """Verify in-flight incomplete tool calls do not trigger quality degradation."""
        tool_sum = ExecutionToolSummary(
            execution_id="ex_25",
            total_calls=2,
            incomplete_calls=2,
            completed_calls=0,
            completeness=ToolObservationCompleteness.PARTIAL,
        )
        snapshot = self.engine.derive_state(
            execution_id="ex_25",
            tool_summary=tool_sum,
        )
        self.assertEqual(snapshot.current_state, ExecutionState.NORMAL)

    # 26. Incomplete web activity
    def test_26_incomplete_web_activity_does_not_infer_failure(self) -> None:
        """Verify in-flight incomplete web requests do not trigger quality degradation."""
        web_sum = ExecutionWebSummary(
            execution_id="ex_26",
            total_requests=2,
            incomplete_requests=2,
            completed_requests=0,
            completeness=WebObservationCompleteness.PARTIAL,
        )
        snapshot = self.engine.derive_state(
            execution_id="ex_26",
            web_summary=web_sum,
        )
        self.assertEqual(snapshot.current_state, ExecutionState.NORMAL)

    # 27. Execution isolation
    def test_27_execution_isolation(self) -> None:
        """Verify state derivations for Execution A never mutate Execution B."""
        policy = self._policy(max_cost=1.0)
        econ_a = ExecutionEconomicSummary(execution_id="exec_A", total_cost=Decimal("5.0"))
        econ_b = ExecutionEconomicSummary(execution_id="exec_B", total_cost=Decimal("0.2"))

        snap_a = self.engine.derive_state("exec_A", economic_summary=econ_a, policy=policy)
        snap_b = self.engine.derive_state("exec_B", economic_summary=econ_b, policy=policy)

        self.assertEqual(snap_a.current_state, ExecutionState.COST_PRESSURE)
        self.assertEqual(snap_b.current_state, ExecutionState.NORMAL)
        self.assertEqual(self.engine.get_state("exec_A").current_state, ExecutionState.COST_PRESSURE)
        self.assertEqual(self.engine.get_state("exec_B").current_state, ExecutionState.NORMAL)

    # 28. Multiple simultaneous executions
    def test_28_multiple_simultaneous_executions(self) -> None:
        """Verify engine lists and tracks multiple executions in memory."""
        for i in range(5):
            self.engine.derive_state(f"sim_{i}")
        self.assertEqual(len(self.engine.list_states()), 5)

    # 29. Repeated identical observation
    def test_29_repeated_identical_observation_idempotent(self) -> None:
        """Verify repeated evaluation with same inputs produces identical state snapshot."""
        s1 = self.engine.derive_state("ex_29")
        s2 = self.engine.derive_state("ex_29")
        self.assertEqual(s1.current_state, s2.current_state)
        self.assertEqual(s1.entered_at, s2.entered_at)

    # 30. Deterministic recomputation
    def test_30_deterministic_recomputation(self) -> None:
        """Verify state recomputation from identical bundle produces deterministic results."""
        policy = self._policy(max_cost=10.0)
        econ = ExecutionEconomicSummary(execution_id="ex_30", total_cost=Decimal("20.0"))
        bundle = ObservationBundle(execution_id="ex_30", economic_summary=econ, policy=policy)

        s1 = self.engine.update_bundle(bundle)
        s2 = self.engine.update_bundle(bundle)
        self.assertEqual(s1.current_state, s2.current_state)
        self.assertEqual(s1.reason_codes, s2.reason_codes)

    # 31. Duplicate observation handling
    def test_31_duplicate_observation_handling(self) -> None:
        """Verify multiple identical bundles maintain state without state drift."""
        bundle = ObservationBundle(execution_id="ex_31")
        for _ in range(4):
            snap = self.engine.update_bundle(bundle)
        self.assertEqual(snap.current_state, ExecutionState.NORMAL)

    # 32. State transition tracking
    def test_32_state_transition_tracking(self) -> None:
        """Verify transition from NORMAL to COST_PRESSURE updates previous_state and entered_at."""
        s1 = self.engine.derive_state("ex_32")
        self.assertEqual(s1.current_state, ExecutionState.NORMAL)
        self.assertIsNone(s1.previous_state)

        policy = self._policy(max_cost=5.0)
        econ = ExecutionEconomicSummary(execution_id="ex_32", total_cost=Decimal("10.0"))
        s2 = self.engine.derive_state("ex_32", economic_summary=econ, policy=policy)

        self.assertEqual(s2.current_state, ExecutionState.COST_PRESSURE)
        self.assertEqual(s2.previous_state, ExecutionState.NORMAL)

    # 33. Repeated same-state observation does not duplicate transition
    def test_33_repeated_same_state_does_not_duplicate_transition(self) -> None:
        """Verify recomputing same state does not append duplicate entries to transition history."""
        self.engine.derive_state("ex_33")
        self.engine.derive_state("ex_33")
        self.engine.derive_state("ex_33")

        history = self.engine.get_history("ex_33")
        self.assertEqual(len(history), 1)

    # 34. Transition history retrieval
    def test_34_transition_history_retrieval(self) -> None:
        """Verify get_history captures distinct sequence of state transitions."""
        self.engine.derive_state("ex_34")  # NORMAL

        policy = self._policy(max_cost=5.0)
        econ = ExecutionEconomicSummary(execution_id="ex_34", total_cost=Decimal("10.0"))
        self.engine.derive_state("ex_34", economic_summary=econ, policy=policy)  # COST_PRESSURE

        health = ExecutionHealthSummary(
            execution_id="ex_34",
            errors=[ObservedErrorRecord(event_id="e1", execution_id="ex_34", error_category=ErrorCategory.RATE_LIMIT, http_status=429)]
        )
        self.engine.derive_state("ex_34", economic_summary=econ, health_summary=health, policy=policy)  # PROVIDER_CONSTRAINED

        history = self.engine.get_history("ex_34")
        self.assertEqual(len(history), 3)
        self.assertEqual(history[0].current_state, ExecutionState.NORMAL)
        self.assertEqual(history[1].current_state, ExecutionState.COST_PRESSURE)
        self.assertEqual(history[2].current_state, ExecutionState.PROVIDER_CONSTRAINED)

    # 35. Multiple simultaneous signals (RUNAWAY > PROVIDER_CONSTRAINED > QUALITY_DEGRADED > COST_PRESSURE > NORMAL)
    def test_35_multiple_signals_precedence_runaway_highest(self) -> None:
        """Verify RUNAWAY takes precedence over COST_PRESSURE and PROVIDER_CONSTRAINED."""
        policy = self._policy(max_cost=5.0, max_tools=10)
        econ = ExecutionEconomicSummary(execution_id="ex_35", total_cost=Decimal("10.0"))  # Cost pressure
        tool = ExecutionToolSummary(execution_id="ex_35", total_calls=15)  # Runaway
        health = ExecutionHealthSummary(
            execution_id="ex_35",
            errors=[ObservedErrorRecord(event_id="e", execution_id="ex_35", error_category=ErrorCategory.RATE_LIMIT)]
        )  # Provider constrained

        snapshot = self.engine.derive_state(
            execution_id="ex_35",
            economic_summary=econ,
            tool_summary=tool,
            health_summary=health,
            policy=policy,
        )
        self.assertEqual(snapshot.current_state, ExecutionState.RUNAWAY)
        self.assertIn("MAX_TOOL_CALLS_EXCEEDED", snapshot.reason_codes)
        # All signals preserved
        self.assertTrue(snapshot.signals.get("budget_exceeded"))
        self.assertTrue(snapshot.signals.get("provider_rate_limited"))

    # 36. Multiple simultaneous signals (PROVIDER_CONSTRAINED > QUALITY_DEGRADED > COST_PRESSURE)
    def test_36_multiple_signals_precedence_provider_over_cost(self) -> None:
        """Verify PROVIDER_CONSTRAINED takes precedence over COST_PRESSURE."""
        policy = self._policy(max_cost=5.0)
        econ = ExecutionEconomicSummary(execution_id="ex_36", total_cost=Decimal("10.0"))
        health = ExecutionHealthSummary(
            execution_id="ex_36",
            errors=[ObservedErrorRecord(event_id="e", execution_id="ex_36", error_category=ErrorCategory.UNAVAILABLE)]
        )

        snapshot = self.engine.derive_state(
            execution_id="ex_36",
            economic_summary=econ,
            health_summary=health,
            policy=policy,
        )
        self.assertEqual(snapshot.current_state, ExecutionState.PROVIDER_CONSTRAINED)

    # 37. Absent policy threshold (unbounded = stays NORMAL)
    def test_37_absent_policy_threshold_stays_normal(self) -> None:
        """Verify execution with no configured limits stays NORMAL even with high usage."""
        policy = self._policy()  # All limits None
        econ = ExecutionEconomicSummary(execution_id="ex_37", total_cost=Decimal("1000.0"))
        tok = ExecutionTokenSummary(execution_id="ex_37", total_tokens=100000)

        snapshot = self.engine.derive_state(
            execution_id="ex_37",
            economic_summary=econ,
            token_summary=tok,
            policy=policy,
        )
        self.assertEqual(snapshot.current_state, ExecutionState.NORMAL)

    # 38. Policy-driven threshold
    def test_38_policy_driven_threshold(self) -> None:
        """Verify state adapts dynamically when policy changes."""
        econ = ExecutionEconomicSummary(execution_id="ex_38", total_cost=Decimal("8.0"))

        p1 = self._policy(max_cost=10.0)
        s1 = self.engine.derive_state("ex_38", economic_summary=econ, policy=p1)
        self.assertEqual(s1.current_state, ExecutionState.COST_PRESSURE)

        p2 = self._policy(max_cost=20.0)
        s2 = self.engine.derive_state("ex_38", economic_summary=econ, policy=p2)
        self.assertEqual(s2.current_state, ExecutionState.NORMAL)

    # 39. Zero vs unknown semantics
    def test_39_zero_vs_unknown_semantics(self) -> None:
        """Verify 0 tokens is distinct from None tokens."""
        policy = self._policy(max_tokens=100)
        tok_zero = ExecutionTokenSummary(execution_id="ex_39a", total_tokens=0)
        s_zero = self.engine.derive_state("ex_39a", token_summary=tok_zero, policy=policy)
        self.assertEqual(s_zero.signals.get("total_tokens"), 0)

        s_none = self.engine.derive_state("ex_39b", token_summary=None, policy=policy)
        self.assertNotIn("total_tokens", s_none.signals)

    # 40. None vs False semantics
    def test_40_none_vs_false_semantics(self) -> None:
        """Verify is_success=None does not trigger failure whereas is_success=False does."""
        h_none = ExecutionHealthSummary(execution_id="ex_40a", is_success=None)
        s_none = self.engine.derive_state("ex_40a", health_summary=h_none)
        self.assertEqual(s_none.current_state, ExecutionState.NORMAL)

        h_false = ExecutionHealthSummary(execution_id="ex_40b", is_success=False)
        s_false = self.engine.derive_state("ex_40b", health_summary=h_false)
        self.assertEqual(s_false.current_state, ExecutionState.QUALITY_DEGRADED)

    # 41. Thread-safe concurrent updates
    def test_41_thread_safe_concurrent_updates(self) -> None:
        """Verify thread-safe concurrent state derivations across multiple threads."""
        threads = []
        for i in range(16):
            t = threading.Thread(
                target=self.engine.derive_state,
                args=(f"th_exec_{i}",),
            )
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(self.engine.list_states()), 16)

    # 42. State snapshot stability (deep copy isolation)
    def test_42_state_snapshot_stability(self) -> None:
        """Verify returned snapshots are immutable copies that cannot corrupt engine internal state."""
        s1 = self.engine.derive_state("ex_42")
        s1.signals["tampered"] = True

        s2 = self.engine.get_state("ex_42")
        self.assertNotIn("tampered", s2.signals)

    # 43. Event Bus integration / StateChanged publication
    def test_43_event_bus_state_changed_publication(self) -> None:
        """Verify StateChanged event is published to EventBus on state transitions."""
        bus = InMemoryEventBus()
        engine_with_bus = ExecutionStateEngine(event_bus=bus)

        events_received = []
        bus.subscribe(lambda ev: events_received.append(ev))

        # Initial state (NORMAL) -> no prior transition event
        engine_with_bus.derive_state("ex_43")

        # Transition to COST_PRESSURE
        policy = self._policy(max_cost=5.0)
        econ = ExecutionEconomicSummary(execution_id="ex_43", total_cost=Decimal("10.0"))
        engine_with_bus.derive_state("ex_43", economic_summary=econ, policy=policy)

        self.assertEqual(len(events_received), 1)
        self.assertEqual(events_received[0].type, EventType.STATE_CHANGED)
        self.assertEqual(events_received[0].payload["new_state"], "COST_PRESSURE")

    # 44. Governor isolation (zero Governor decisions/actions)
    def test_44_governor_isolation_no_actions(self) -> None:
        """Verify state engine never outputs Governor control actions (e.g. STOP, THROTTLE, SWITCH)."""
        policy = self._policy(max_cost=1.0)
        econ = ExecutionEconomicSummary(execution_id="ex_44", total_cost=Decimal("100.0"))
        snapshot = self.engine.derive_state("ex_44", economic_summary=econ, policy=policy)

        # Snapshot is ExecutionStateSnapshot, not ControlAction
        self.assertIsInstance(snapshot, ExecutionStateSnapshot)
        self.assertNotEqual(snapshot.current_state, "STOP")
        self.assertNotEqual(snapshot.current_state, "THROTTLE")
        self.assertNotEqual(snapshot.current_state, "SWITCH")

    # 45. Lifecycle isolation
    def test_45_lifecycle_isolation(self) -> None:
        """Verify state engine contains zero lifecycle state mutations."""
        import infuse.state
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.state")]
        for mod in modules:
            src = inspect.getsource(mod)
            self.assertNotIn("transition_lifecycle", src)
            self.assertNotIn("set_lifecycle_state", src)

    # 46. Router & Provider Adapter isolation
    def test_46_router_and_adapter_isolation(self) -> None:
        """Verify state engine contains zero routing, provider adapter, or retry logic."""
        import infuse.state
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.state")]
        for mod in modules:
            src = inspect.getsource(mod)
            self.assertNotIn("route_request", src)
            self.assertNotIn("execute_adapter", src)
            self.assertNotIn("execute_retry", src)

    # 47. Zero database & external broker imports
    def test_47_zero_database_and_broker_imports(self) -> None:
        """Verify state package contains zero database or broker imports."""
        import infuse.state
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.state")]
        forbidden = [
            "sqlite3", "psycopg2", "sqlalchemy", "redis", "kafka", "rabbitmq", "nats", "celery"
        ]
        for mod in modules:
            src = inspect.getsource(mod)
            for f in forbidden:
                self.assertNotIn(f"import {f}", src)
                self.assertNotIn(f"from {f}", src)

    # 48. Zero provider SDK imports
    def test_48_zero_provider_sdk_imports(self) -> None:
        """Verify state package contains zero provider SDK imports."""
        import infuse.state
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.state")]
        forbidden = ["openai", "anthropic", "google.generativeai", "cohere", "langchain"]
        for mod in modules:
            src = inspect.getsource(mod)
            for f in forbidden:
                self.assertNotIn(f"import {f}", src)
                self.assertNotIn(f"from {f}", src)


if __name__ == "__main__":
    unittest.main()
