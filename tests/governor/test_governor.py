"""Comprehensive Unit, Integration, and Boundary Test Suite for Block 21 Governor Engine."""

import inspect
import sys
import threading
import unittest
from typing import List, Optional

from infuse.contracts.events import EventType
from infuse.contracts.governor import GovernorAction, GovernorDecisionRecord
from infuse.contracts.policy import (
    AnomalyProtection,
    BudgetControls,
    GovernancePolicy,
    PolicyActionBindings,
    RequestControls,
    RuntimeControls,
    TokenControls,
    ToolAccessControls,
)
from infuse.contracts.state import ExecutionState, ExecutionStateSnapshot
from infuse.events.bus import InMemoryEventBus
from infuse.governor.engine import GovernorEngine


class TestGovernorEngine(unittest.TestCase):
    """Test suite verifying Governor decision evaluation, action mappings, auditability, and isolation."""

    def setUp(self) -> None:
        self.engine = GovernorEngine()

    def _state(
        self,
        execution_id: str = "exec_01",
        state: ExecutionState = ExecutionState.NORMAL,
        reasons: Optional[List[str]] = None,
        signals: Optional[dict] = None,
    ) -> ExecutionStateSnapshot:
        return ExecutionStateSnapshot(
            execution_id=execution_id,
            current_state=state,
            reason_codes=reasons or [],
            signals=signals or {},
        )

    def _policy(
        self,
        policy_id: str = "pol_01",
        version: str = "1.0.0",
        budget_action: GovernorAction = GovernorAction.OPTIMIZE,
        token_action: GovernorAction = GovernorAction.OPTIMIZE,
        request_action: GovernorAction = GovernorAction.THROTTLE,
        runtime_action: GovernorAction = GovernorAction.STOP,
        provider_failure_action: GovernorAction = GovernorAction.SWITCH,
        anomaly_action: GovernorAction = GovernorAction.STOP,
    ) -> GovernancePolicy:
        return GovernancePolicy(
            policy_id=policy_id,
            version=version,
            actions=PolicyActionBindings(
                budget_action=budget_action,
                token_action=token_action,
                request_action=request_action,
                runtime_action=runtime_action,
                provider_failure_action=provider_failure_action,
                anomaly_action=anomaly_action,
            ),
        )

    # 1. Governor initialization
    def test_01_governor_initialization(self) -> None:
        """Verify Governor engine initializes cleanly with empty caches."""
        self.assertEqual(len(self.engine.list_decisions()), 0)
        self.assertIsNone(self.engine.get_latest_decision("nonexistent"))

    # 2. Effective policy consumption
    def test_02_effective_policy_consumption(self) -> None:
        """Verify policy metadata and rules are consumed and recorded in decision audit."""
        policy = self._policy(policy_id="pol_custom", version="2.1.0")
        state = self._state(execution_id="ex_02", state=ExecutionState.NORMAL)
        decision = self.engine.evaluate("ex_02", state, policy)

        self.assertEqual(decision.effective_policy_id, "pol_custom")
        self.assertEqual(decision.metadata.get("policy_version"), "2.1.0")
        self.assertTrue(decision.metadata.get("has_explicit_policy"))

    # 3. Execution state consumption
    def test_03_execution_state_consumption(self) -> None:
        """Verify execution state from snapshot is recorded in decision record."""
        state = self._state(execution_id="ex_03", state=ExecutionState.NORMAL, reasons=["NORMAL_EXECUTION"])
        decision = self.engine.evaluate("ex_03", state)

        self.assertEqual(decision.evaluated_state, "NORMAL")
        self.assertIn("NORMAL_EXECUTION", decision.reason_codes)

    # 4. NORMAL state -> CONTINUE
    def test_04_normal_state_maps_to_continue(self) -> None:
        """Verify NORMAL state always produces CONTINUE action."""
        state = self._state(execution_id="ex_04", state=ExecutionState.NORMAL)
        decision = self.engine.evaluate("ex_04", state)

        self.assertEqual(decision.action, GovernorAction.CONTINUE)
        self.assertIn("operating within normal policy boundaries", decision.message)

    # 5. COST_PRESSURE policy mapping (budget -> OPTIMIZE/custom)
    def test_05_cost_pressure_budget_action_mapping(self) -> None:
        """Verify COST_PRESSURE with budget reason applies policy budget_action."""
        policy = self._policy(budget_action=GovernorAction.THROTTLE)
        state = self._state(
            execution_id="ex_05",
            state=ExecutionState.COST_PRESSURE,
            reasons=["BUDGET_EXCEEDED"],
        )
        decision = self.engine.evaluate("ex_05", state, policy)

        self.assertEqual(decision.action, GovernorAction.THROTTLE)
        self.assertEqual(decision.metadata.get("triggering_policy_field"), "actions.budget_action")

    # 6. COST_PRESSURE policy mapping (token -> OPTIMIZE/custom)
    def test_06_cost_pressure_token_action_mapping(self) -> None:
        """Verify COST_PRESSURE with token ceiling reason applies policy token_action."""
        policy = self._policy(token_action=GovernorAction.OPTIMIZE)
        state = self._state(
            execution_id="ex_06",
            state=ExecutionState.COST_PRESSURE,
            reasons=["TOKEN_CEILING_EXCEEDED"],
        )
        decision = self.engine.evaluate("ex_06", state, policy)

        self.assertEqual(decision.action, GovernorAction.OPTIMIZE)
        self.assertEqual(decision.metadata.get("triggering_policy_field"), "actions.token_action")

    # 7. RUNAWAY policy mapping (runtime -> STOP/custom)
    def test_07_runaway_runtime_action_mapping(self) -> None:
        """Verify RUNAWAY with execution time exceeded applies runtime_action."""
        policy = self._policy(runtime_action=GovernorAction.STOP)
        state = self._state(
            execution_id="ex_07",
            state=ExecutionState.RUNAWAY,
            reasons=["EXECUTION_TIME_EXCEEDED"],
        )
        decision = self.engine.evaluate("ex_07", state, policy)

        self.assertEqual(decision.action, GovernorAction.STOP)
        self.assertEqual(decision.metadata.get("triggering_policy_field"), "actions.runtime_action")

    # 8. RUNAWAY policy mapping (requests -> THROTTLE/custom)
    def test_08_runaway_requests_action_mapping(self) -> None:
        """Verify RUNAWAY with request ceiling exceeded applies request_action."""
        policy = self._policy(request_action=GovernorAction.THROTTLE)
        state = self._state(
            execution_id="ex_08",
            state=ExecutionState.RUNAWAY,
            reasons=["MAX_WEB_REQUESTS_EXCEEDED"],
        )
        decision = self.engine.evaluate("ex_08", state, policy)

        self.assertEqual(decision.action, GovernorAction.THROTTLE)
        self.assertEqual(decision.metadata.get("triggering_policy_field"), "actions.request_action")

    # 9. RUNAWAY policy mapping (tools/anomaly -> STOP/custom)
    def test_09_runaway_anomaly_action_mapping(self) -> None:
        """Verify RUNAWAY with anomaly/tool ceiling applies anomaly_action."""
        policy = self._policy(anomaly_action=GovernorAction.STOP)
        state = self._state(
            execution_id="ex_09",
            state=ExecutionState.RUNAWAY,
            reasons=["MAX_TOOL_CALLS_EXCEEDED"],
        )
        decision = self.engine.evaluate("ex_09", state, policy)

        self.assertEqual(decision.action, GovernorAction.STOP)
        self.assertEqual(decision.metadata.get("triggering_policy_field"), "actions.anomaly_action")

    # 10. PROVIDER_CONSTRAINED policy mapping (provider failure -> SWITCH/custom)
    def test_10_provider_constrained_action_mapping(self) -> None:
        """Verify PROVIDER_CONSTRAINED applies provider_failure_action."""
        policy = self._policy(provider_failure_action=GovernorAction.SWITCH)
        state = self._state(
            execution_id="ex_10",
            state=ExecutionState.PROVIDER_CONSTRAINED,
            reasons=["PROVIDER_RATE_LIMIT"],
        )
        decision = self.engine.evaluate("ex_10", state, policy)

        self.assertEqual(decision.action, GovernorAction.SWITCH)
        self.assertEqual(decision.metadata.get("triggering_policy_field"), "actions.provider_failure_action")

    # 11. QUALITY_DEGRADED policy mapping
    def test_11_quality_degraded_action_mapping(self) -> None:
        """Verify QUALITY_DEGRADED applies provider_failure_action."""
        policy = self._policy(provider_failure_action=GovernorAction.SWITCH)
        state = self._state(
            execution_id="ex_11",
            state=ExecutionState.QUALITY_DEGRADED,
            reasons=["EXECUTION_FAILURE"],
        )
        decision = self.engine.evaluate("ex_11", state, policy)

        self.assertEqual(decision.action, GovernorAction.SWITCH)
        self.assertEqual(decision.metadata.get("triggering_policy_field"), "actions.provider_failure_action")

    # 12. Action: CONTINUE verification
    def test_12_action_continue(self) -> None:
        """Verify CONTINUE action can be emitted cleanly."""
        state = self._state(state=ExecutionState.NORMAL)
        decision = self.engine.evaluate("ex_12", state)
        self.assertEqual(decision.action, GovernorAction.CONTINUE)

    # 13. Action: OPTIMIZE verification
    def test_13_action_optimize(self) -> None:
        """Verify OPTIMIZE action is emitted when bound by policy."""
        policy = self._policy(budget_action=GovernorAction.OPTIMIZE)
        state = self._state(state=ExecutionState.COST_PRESSURE, reasons=["BUDGET_EXCEEDED"])
        decision = self.engine.evaluate("ex_13", state, policy)
        self.assertEqual(decision.action, GovernorAction.OPTIMIZE)

    # 14. Action: ESCALATE verification
    def test_14_action_escalate(self) -> None:
        """Verify ESCALATE action is emitted when bound by policy."""
        policy = self._policy(budget_action=GovernorAction.ESCALATE)
        state = self._state(state=ExecutionState.COST_PRESSURE, reasons=["BUDGET_EXCEEDED"])
        decision = self.engine.evaluate("ex_14", state, policy)
        self.assertEqual(decision.action, GovernorAction.ESCALATE)

    # 15. Action: DOWNGRADE verification
    def test_15_action_downgrade(self) -> None:
        """Verify DOWNGRADE action is emitted when bound by policy."""
        policy = self._policy(budget_action=GovernorAction.DOWNGRADE)
        state = self._state(state=ExecutionState.COST_PRESSURE, reasons=["BUDGET_EXCEEDED"])
        decision = self.engine.evaluate("ex_15", state, policy)
        self.assertEqual(decision.action, GovernorAction.DOWNGRADE)

    # 16. Action: SWITCH verification
    def test_16_action_switch(self) -> None:
        """Verify SWITCH action is emitted when bound by policy."""
        policy = self._policy(provider_failure_action=GovernorAction.SWITCH)
        state = self._state(state=ExecutionState.PROVIDER_CONSTRAINED, reasons=["PROVIDER_UNAVAILABLE"])
        decision = self.engine.evaluate("ex_16", state, policy)
        self.assertEqual(decision.action, GovernorAction.SWITCH)

    # 17. Action: THROTTLE verification
    def test_17_action_throttle(self) -> None:
        """Verify THROTTLE action is emitted when bound by policy."""
        policy = self._policy(request_action=GovernorAction.THROTTLE)
        state = self._state(state=ExecutionState.RUNAWAY, reasons=["MAX_REQUESTS_EXCEEDED"])
        decision = self.engine.evaluate("ex_17", state, policy)
        self.assertEqual(decision.action, GovernorAction.THROTTLE)

    # 18. Action: STOP verification
    def test_18_action_stop(self) -> None:
        """Verify STOP action is emitted when bound by policy."""
        policy = self._policy(anomaly_action=GovernorAction.STOP)
        state = self._state(state=ExecutionState.RUNAWAY, reasons=["REPETITIVE_LOOP_DETECTED"])
        decision = self.engine.evaluate("ex_18", state, policy)
        self.assertEqual(decision.action, GovernorAction.STOP)

    # 19. Policy-defined action dynamic mapping
    def test_19_policy_defined_action_dynamic_mapping(self) -> None:
        """Verify changing policy action bindings dynamically alters Governor decisions."""
        state = self._state(state=ExecutionState.COST_PRESSURE, reasons=["BUDGET_EXCEEDED"])

        p1 = self._policy(budget_action=GovernorAction.OPTIMIZE)
        d1 = self.engine.evaluate("ex_19", state, p1)
        self.assertEqual(d1.action, GovernorAction.OPTIMIZE)

        p2 = self._policy(budget_action=GovernorAction.STOP)
        d2 = self.engine.evaluate("ex_19", state, p2)
        self.assertEqual(d2.action, GovernorAction.STOP)

    # 20. Missing policy (safe default fallback behavior)
    def test_20_missing_policy_safe_default_behavior(self) -> None:
        """Verify Governor evaluates cleanly with default bindings when policy is omitted."""
        state = self._state(state=ExecutionState.COST_PRESSURE, reasons=["BUDGET_EXCEEDED"])
        decision = self.engine.evaluate("ex_20", state, policy=None)

        self.assertIsNone(decision.effective_policy_id)
        self.assertEqual(decision.action, GovernorAction.OPTIMIZE)
        self.assertFalse(decision.metadata.get("has_explicit_policy"))

    # 21. Incomplete policy (empty bindings)
    def test_21_incomplete_policy_uses_default_bindings(self) -> None:
        """Verify policy with default action bindings applies default action."""
        policy = GovernancePolicy(policy_id="empty_pol")
        state = self._state(state=ExecutionState.PROVIDER_CONSTRAINED, reasons=["PROVIDER_RATE_LIMIT"])
        decision = self.engine.evaluate("ex_21", state, policy)

        self.assertEqual(decision.action, GovernorAction.SWITCH)

    # 22. Unknown state (safe continuation fallback)
    def test_22_unknown_state_fallback(self) -> None:
        """Verify unexpected execution state falls back to CONTINUE without crashing."""
        snapshot = ExecutionStateSnapshot(
            execution_id="ex_22",
            current_state=ExecutionState.NORMAL,
        )
        # Manually alter current_state string to simulate unknown state
        snapshot.__dict__["current_state"] = "NON_STANDARD_STATE"

        decision = self.engine.evaluate("ex_22", snapshot)
        self.assertEqual(decision.action, GovernorAction.CONTINUE)

    # 23. Incomplete state (empty reason codes)
    def test_23_incomplete_state_empty_reasons(self) -> None:
        """Verify state with empty reasons resolves default state action."""
        state = self._state(state=ExecutionState.COST_PRESSURE, reasons=[])
        decision = self.engine.evaluate("ex_23", state)
        self.assertEqual(decision.action, GovernorAction.OPTIMIZE)

    # 24. Missing cost evidence (handled gracefully)
    def test_24_missing_cost_evidence(self) -> None:
        """Verify absent cost signals do not crash Governor."""
        state = self._state(state=ExecutionState.NORMAL, signals={})
        decision = self.engine.evaluate("ex_24", state)
        self.assertEqual(decision.action, GovernorAction.CONTINUE)

    # 25. Missing token evidence (handled gracefully)
    def test_25_missing_token_evidence(self) -> None:
        """Verify absent token signals evaluate cleanly."""
        state = self._state(state=ExecutionState.NORMAL, signals={"latency_ms": 120.0})
        decision = self.engine.evaluate("ex_25", state)
        self.assertEqual(decision.action, GovernorAction.CONTINUE)

    # 26. Missing health evidence (handled gracefully)
    def test_26_missing_health_evidence(self) -> None:
        """Verify absent health errors evaluate cleanly."""
        state = self._state(state=ExecutionState.NORMAL, signals={"tokens": 100})
        decision = self.engine.evaluate("ex_26", state)
        self.assertEqual(decision.action, GovernorAction.CONTINUE)

    # 27. Simultaneous state conditions (precedence from state snapshot respected)
    def test_27_simultaneous_state_conditions_precedence_respected(self) -> None:
        """Verify Governor enforces action corresponding to the canonical state snapshot."""
        # State engine already resolved RUNAWAY as canonical state
        state = self._state(
            execution_id="ex_27",
            state=ExecutionState.RUNAWAY,
            reasons=["MAX_TOOL_CALLS_EXCEEDED"],
            signals={"budget_exceeded": True, "max_tool_calls_exceeded": True},
        )
        policy = self._policy(
            budget_action=GovernorAction.OPTIMIZE,
            anomaly_action=GovernorAction.STOP,
        )
        decision = self.engine.evaluate("ex_27", state, policy)

        self.assertEqual(decision.action, GovernorAction.STOP)
        self.assertEqual(decision.metadata.get("triggering_policy_field"), "actions.anomaly_action")

    # 28. Explicit policy precedence
    def test_28_explicit_policy_precedence(self) -> None:
        """Verify policy action bindings dictate the exact control action selected."""
        policy = self._policy(provider_failure_action=GovernorAction.ESCALATE)
        state = self._state(state=ExecutionState.PROVIDER_CONSTRAINED, reasons=["PROVIDER_RATE_LIMIT"])
        decision = self.engine.evaluate("ex_28", state, policy)

        self.assertEqual(decision.action, GovernorAction.ESCALATE)

    # 29. No applicable rule (safe fallback)
    def test_29_no_applicable_rule_safe_continuation(self) -> None:
        """Verify NORMAL state with no explicit triggers resolves CONTINUE."""
        state = self._state(state=ExecutionState.NORMAL)
        decision = self.engine.evaluate("ex_29", state)
        self.assertEqual(decision.action, GovernorAction.CONTINUE)

    # 30. Insufficient evidence handling
    def test_30_insufficient_evidence_handling(self) -> None:
        """Verify Governor does not infer failure when signals are absent."""
        state = self._state(state=ExecutionState.NORMAL, signals={})
        decision = self.engine.evaluate("ex_30", state)
        self.assertEqual(decision.action, GovernorAction.CONTINUE)

    # 31. Deterministic decision (same inputs = same decision)
    def test_31_deterministic_decision(self) -> None:
        """Verify identical inputs produce identical action and reason codes."""
        policy = self._policy(budget_action=GovernorAction.OPTIMIZE)
        state = self._state(state=ExecutionState.COST_PRESSURE, reasons=["BUDGET_EXCEEDED"])

        d1 = self.engine.evaluate("ex_31", state, policy)
        d2 = self.engine.evaluate("ex_31", state, policy)

        self.assertEqual(d1.action, d2.action)
        self.assertEqual(d1.reason_codes, d2.reason_codes)

    # 32. Repeated identical evaluation (idempotency)
    def test_32_repeated_evaluation_preserves_state(self) -> None:
        """Verify repeated evaluations maintain stability in latest decision retrieval."""
        state = self._state(state=ExecutionState.NORMAL)
        for _ in range(3):
            self.engine.evaluate("ex_32", state)

        latest = self.engine.get_latest_decision("ex_32")
        self.assertEqual(latest.action, GovernorAction.CONTINUE)

    # 33. Execution isolation
    def test_33_execution_isolation(self) -> None:
        """Verify decisions for Execution A never mutate Execution B."""
        state_a = self._state(execution_id="exec_A", state=ExecutionState.RUNAWAY, reasons=["EXECUTION_TIME_EXCEEDED"])
        state_b = self._state(execution_id="exec_B", state=ExecutionState.NORMAL)

        dec_a = self.engine.evaluate("exec_A", state_a)
        dec_b = self.engine.evaluate("exec_B", state_b)

        self.assertEqual(dec_a.action, GovernorAction.STOP)
        self.assertEqual(dec_b.action, GovernorAction.CONTINUE)
        self.assertEqual(self.engine.get_latest_decision("exec_A").action, GovernorAction.STOP)
        self.assertEqual(self.engine.get_latest_decision("exec_B").action, GovernorAction.CONTINUE)

    # 34. Multiple concurrent executions
    def test_34_multiple_concurrent_executions_tracked(self) -> None:
        """Verify engine tracks latest decisions across multiple executions."""
        for i in range(8):
            st = self._state(execution_id=f"sim_{i}")
            self.engine.evaluate(f"sim_{i}", st)

        self.assertEqual(len(self.engine.list_decisions()), 8)

    # 35. Decision history tracking
    def test_35_decision_history_tracking(self) -> None:
        """Verify decision history captures all sequential evaluations for an execution."""
        state_1 = self._state(execution_id="ex_35", state=ExecutionState.NORMAL)
        self.engine.evaluate("ex_35", state_1)

        state_2 = self._state(execution_id="ex_35", state=ExecutionState.COST_PRESSURE, reasons=["BUDGET_EXCEEDED"])
        self.engine.evaluate("ex_35", state_2)

        history = self.engine.get_decision_history("ex_35")
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0].action, GovernorAction.CONTINUE)
        self.assertEqual(history[1].action, GovernorAction.OPTIMIZE)

    # 36. Chronological decision history
    def test_36_chronological_decision_history(self) -> None:
        """Verify history entries are in chronological order."""
        state = self._state(execution_id="ex_36")
        self.engine.evaluate("ex_36", state)
        self.engine.evaluate("ex_36", state)

        history = self.engine.get_decision_history("ex_36")
        self.assertLessEqual(history[0].evaluated_at, history[1].evaluated_at)

    # 37. Policy version tracking in audit metadata
    def test_37_policy_version_tracking(self) -> None:
        """Verify policy revision version is stored in decision metadata."""
        policy = self._policy(version="3.5.1")
        state = self._state(execution_id="ex_37")
        decision = self.engine.evaluate("ex_37", state, policy)

        self.assertEqual(decision.metadata.get("policy_version"), "3.5.1")

    # 38. State version / evaluation sequence tracking
    def test_38_evaluation_sequence_tracking(self) -> None:
        """Verify evaluation sequence counter increments monotonically per execution."""
        state = self._state(execution_id="ex_38")
        d1 = self.engine.evaluate("ex_38", state)
        d2 = self.engine.evaluate("ex_38", state)

        self.assertEqual(d1.metadata.get("evaluation_sequence"), 1)
        self.assertEqual(d2.metadata.get("evaluation_sequence"), 2)

    # 39. Reason codes fidelity
    def test_39_reason_codes_fidelity(self) -> None:
        """Verify snapshot reason codes are preserved faithfully in decision record."""
        state = self._state(
            execution_id="ex_39",
            state=ExecutionState.PROVIDER_CONSTRAINED,
            reasons=["PROVIDER_RATE_LIMIT", "HTTP_429_TOO_MANY_REQUESTS"],
        )
        decision = self.engine.evaluate("ex_39", state)
        self.assertIn("PROVIDER_RATE_LIMIT", decision.reason_codes)
        self.assertIn("HTTP_429_TOO_MANY_REQUESTS", decision.reason_codes)

    # 40. Structured evidence and metadata
    def test_40_structured_evidence_and_signals(self) -> None:
        """Verify signals from state and additional signals are combined in decision record."""
        state = self._state(
            execution_id="ex_40",
            signals={"token_count": 500},
        )
        decision = self.engine.evaluate("ex_40", state, additional_signals={"caller": "test_harness"})

        self.assertEqual(decision.signals.get("token_count"), 500)
        self.assertEqual(decision.signals.get("caller"), "test_harness")

    # 41. Auditability (decision record contains full context)
    def test_41_decision_record_auditability(self) -> None:
        """Verify GovernorDecisionRecord has all required audit fields."""
        state = self._state(execution_id="ex_41")
        decision = self.engine.evaluate("ex_41", state)

        self.assertTrue(decision.decision_id.startswith("gov_dec_ex_41_"))
        self.assertEqual(decision.execution_id, "ex_41")
        self.assertIsNotNone(decision.evaluated_at)
        self.assertIsNotNone(decision.evaluated_state)
        self.assertIsInstance(decision.metadata, dict)

    # 42. No lifecycle mutation
    def test_42_no_lifecycle_mutation(self) -> None:
        """Verify governor engine does not mutate lifecycle states or import lifecycle transition APIs."""
        import infuse.governor
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.governor")]
        for mod in modules:
            src = inspect.getsource(mod)
            self.assertNotIn("transition_lifecycle", src)
            self.assertNotIn("set_lifecycle_state", src)

    # 43. No router invocation
    def test_43_no_router_invocation(self) -> None:
        """Verify governor engine does not invoke Router or select providers."""
        import infuse.governor
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.governor")]
        for mod in modules:
            src = inspect.getsource(mod)
            self.assertNotIn("route_request", src)
            self.assertNotIn("select_provider", src)

    # 44. No provider invocation
    def test_44_no_provider_invocation(self) -> None:
        """Verify governor engine contains zero provider adapter invocations."""
        import infuse.governor
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.governor")]
        for mod in modules:
            src = inspect.getsource(mod)
            self.assertNotIn("execute_adapter", src)
            self.assertNotIn("invoke_provider", src)

    # 45. No retry execution
    def test_45_no_retry_execution(self) -> None:
        """Verify governor engine does not schedule or execute retries."""
        import infuse.governor
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.governor")]
        for mod in modules:
            src = inspect.getsource(mod)
            self.assertNotIn("execute_retry", src)
            self.assertNotIn("schedule_retry", src)

    # 46. No control boundary execution
    def test_46_no_control_boundary_execution(self) -> None:
        """Verify governor engine does not physically throttle, stop, or mutate runtime."""
        import infuse.governor
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.governor")]
        for mod in modules:
            src = inspect.getsource(mod)
            self.assertNotIn("time.sleep", src)
            self.assertNotIn("kill_process", src)

    # 47. No network access or sockets
    def test_47_no_network_access(self) -> None:
        """Verify governor package contains zero network or socket operations."""
        import infuse.governor
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.governor")]
        forbidden = ["requests", "urllib", "http.client", "aiohttp", "socket", "httpx"]
        for mod in modules:
            src = inspect.getsource(mod)
            for f in forbidden:
                self.assertNotIn(f"import {f}", src)
                self.assertNotIn(f"from {f}", src)

    # 48. No provider SDK imports
    def test_48_zero_provider_sdk_imports(self) -> None:
        """Verify governor package contains zero provider SDK imports."""
        import infuse.governor
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.governor")]
        forbidden = ["openai", "anthropic", "google.generativeai", "cohere", "langchain"]
        for mod in modules:
            src = inspect.getsource(mod)
            for f in forbidden:
                self.assertNotIn(f"import {f}", src)
                self.assertNotIn(f"from {f}", src)

    # 49. Thread-safe evaluation
    def test_49_thread_safe_evaluation(self) -> None:
        """Verify thread-safe concurrent evaluations across multiple threads."""
        threads = []
        state = self._state()
        for i in range(16):
            t = threading.Thread(
                target=self.engine.evaluate,
                args=(f"th_exec_{i}", state),
            )
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(self.engine.list_decisions()), 16)

    # 50. Event integration (publishes EventType.GOVERNOR_DECISION to EventBus)
    def test_50_event_bus_governor_decision_publication(self) -> None:
        """Verify GovernorDecision event is published to EventBus on evaluation."""
        bus = InMemoryEventBus()
        engine_with_bus = GovernorEngine(event_bus=bus)

        events_received = []
        bus.subscribe(lambda ev: events_received.append(ev))

        state = self._state(execution_id="ex_50", state=ExecutionState.COST_PRESSURE, reasons=["BUDGET_EXCEEDED"])
        policy = self._policy(budget_action=GovernorAction.OPTIMIZE)
        engine_with_bus.evaluate("ex_50", state, policy)

        self.assertEqual(len(events_received), 1)
        self.assertEqual(events_received[0].type, EventType.GOVERNOR_DECISION)
        self.assertEqual(events_received[0].payload["action"], "OPTIMIZE")


if __name__ == "__main__":
    unittest.main()
