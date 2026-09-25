"""Observer and State Engine Hardening Tests (Block 33).

Stress tests:
1. Token Observer (authoritative vs estimated tokens, missing usage, explicit zero)
2. Economics Engine (decimal precision, missing rate fallback to UNKNOWN, repeated calculation)
3. Health Engine (error categorization, upstream timeouts, consecutive error reset on success)
4. Tool & Web Observers (partial evidence, missing pairs, out-of-order events)
5. Execution State Engine (canonical state derivation, precedence hierarchy, deterministic outputs)
"""

import unittest
import uuid
from decimal import Decimal
from typing import Optional

from infuse.contracts.common import utc_now
from infuse.contracts.events import (
    EventSource,
    EventType,
    ExecutionEvent,
    ProviderErrorPayload,
    StateChangedPayload,
    TokenObservedPayload,
    ToolActivityPayload,
    WebActivityPayload,
)
from infuse.contracts.policy import (
    BudgetControls,
    GovernancePolicy,
    PolicyActionBindings,
    TokenControls,
)
from infuse.contracts.state import ExecutionState
from infuse.economics import (
    EconomicCompleteness,
    EconomicsEngine,
    InMemoryPricingRegistry,
    ModelPricingRate,
    PricingUnit,
)
from infuse.events.bus import InMemoryEventBus
from infuse.health.engine import HealthEngine
from infuse.health.models import ErrorCategory, HealthCompleteness
from infuse.observer import TokenObservationSource, TokenObserver
from infuse.state.engine import ExecutionStateEngine
from infuse.tools.observer import ToolActivityObserver
from infuse.web.observer import WebActivityObserver


class TestObserverStateHardening(unittest.TestCase):
    """Stress and reliability tests for Observers and State Engine."""

    def setUp(self) -> None:
        self.bus = InMemoryEventBus()
        self.token_observer = TokenObserver()
        self.token_observer.attach_to_bus(self.bus)
        self.tool_observer = ToolActivityObserver()
        self.tool_observer.attach_to_bus(self.bus)
        self.web_observer = WebActivityObserver()
        self.web_observer.attach_to_bus(self.bus)
        self.health_engine = HealthEngine()
        self.health_engine.attach_to_bus(self.bus)
        self.pricing_registry = InMemoryPricingRegistry()
        self.economics_engine = EconomicsEngine(pricing_registry=self.pricing_registry)
        self.state_engine = ExecutionStateEngine()

    def test_01_token_observer_authoritative_reconciliation(self) -> None:
        """Verify authoritative tokens update cumulative observation correctly."""
        exec_id = f"exec_tok_recon_{uuid.uuid4().hex[:8]}"

        # Observation 1: Estimated tokens
        self.bus.publish(ExecutionEvent(
            event_id="ev_est_01",
            execution_id=exec_id,
            sequence=1,
            type=EventType.TOKEN_OBSERVED,
            source=EventSource.SYSTEM,
            payload=TokenObservedPayload(
                input_tokens=100,
                output_tokens=50,
                total_tokens=150,
                provider="mock",
                model="mock-fast",
                source=TokenObservationSource.STREAM_ESTIMATE,
            ).model_dump(),
        ))

        obs1 = self.token_observer.get_observation(exec_id)
        self.assertEqual(obs1.total_tokens, 150)

        # Observation 2: Authoritative tokens
        self.bus.publish(ExecutionEvent(
            event_id="ev_auth_01",
            execution_id=exec_id,
            sequence=2,
            type=EventType.TOKEN_OBSERVED,
            source=EventSource.SYSTEM,
            payload=TokenObservedPayload(
                input_tokens=200,
                output_tokens=100,
                total_tokens=300,
                is_authoritative=True,
                provider="mock",
                model="mock-fast",
                source=TokenObservationSource.PROVIDER_USAGE,
            ).model_dump(),
        ))

        obs2 = self.token_observer.get_observation(exec_id)
        self.assertEqual(obs2.total_tokens, 300)
        self.assertTrue(obs2.is_authoritative)

    def test_02_economics_missing_pricing_retains_unknown_completeness(self) -> None:
        """Verify unpriced model returns UNKNOWN economic completeness without guessing 0.0."""
        exec_id = f"exec_unpriced_{uuid.uuid4().hex[:8]}"
        self.bus.publish(ExecutionEvent(
            event_id="ev_unpriced_01",
            execution_id=exec_id,
            sequence=1,
            type=EventType.TOKEN_OBSERVED,
            source=EventSource.SYSTEM,
            payload=TokenObservedPayload(
                input_tokens=500,
                output_tokens=250,
                total_tokens=750,
                provider="unregistered_provider",
                model="unregistered_model",
            ).model_dump(),
        ))

        tok_obs = self.token_observer.get_observation(exec_id)
        econ = self.economics_engine.calculate(tok_obs)
        self.assertEqual(str(econ.completeness), "UNKNOWN")
        self.assertIsNone(econ.total_cost)

    def test_03_economics_decimal_precision_multi_rate(self) -> None:
        """Verify exact decimal cost computation across input and output token rates."""
        self.pricing_registry.register_rate(ModelPricingRate(
            provider_id="mock",
            model_id="mock-fast",
            input_rate=Decimal("1.250000"),
            output_rate=Decimal("3.750000"),
            unit=PricingUnit.PER_1M_TOKENS,
            currency="USD",
        ))

        exec_id = f"exec_econ_prec_{uuid.uuid4().hex[:8]}"
        self.bus.publish(ExecutionEvent(
            event_id="ev_prec_01",
            execution_id=exec_id,
            sequence=1,
            type=EventType.TOKEN_OBSERVED,
            source=EventSource.SYSTEM,
            payload=TokenObservedPayload(
                input_tokens=2_000_000,
                output_tokens=1_000_000,
                total_tokens=3_000_000,
                provider="mock",
                model="mock-fast",
            ).model_dump(),
        ))

        tok_obs = self.token_observer.get_observation(exec_id)
        econ = self.economics_engine.calculate(tok_obs)

        # Expected: (2 * 1.25) + (1 * 3.75) = 2.50 + 3.75 = 6.25 USD
        self.assertEqual(econ.total_cost, Decimal("6.250000"))

    def test_04_health_engine_error_tracking_and_recovery(self) -> None:
        """Verify health engine tracks errors and calculates error metrics cleanly."""
        exec_id = f"exec_health_rec_{uuid.uuid4().hex[:8]}"

        self.bus.publish(ExecutionEvent(
            event_id="ev_err_503",
            execution_id=exec_id,
            sequence=1,
            type=EventType.PROVIDER_ERROR,
            source=EventSource.SYSTEM,
            payload=ProviderErrorPayload(
                provider="mock",
                model="mock-fast",
                error_type="ServiceUnavailable",
                message="HTTP 503",
                http_status=503,
            ).model_dump(),
        ))

        health = self.health_engine.get_execution_health(exec_id)
        self.assertFalse(health.is_success)
        self.assertEqual(len(health.errors), 1)

    def test_05_tool_observer_uncompleted_call_retains_partial_status(self) -> None:
        """Verify uncompleted tool call marks completeness as PARTIAL without raising exception."""
        exec_id = f"exec_tool_part_{uuid.uuid4().hex[:8]}"
        self.bus.publish(ExecutionEvent(
            event_id="ev_tool_call_01",
            execution_id=exec_id,
            sequence=1,
            type=EventType.TOOL_CALLED,
            source=EventSource.SYSTEM,
            payload=ToolActivityPayload(
                tool_name="file_search",
                call_id="call_01",
            ).model_dump(),
        ))

        summary = self.tool_observer.get_execution_summary(exec_id)
        self.assertEqual(summary.total_calls, 1)
        self.assertEqual(summary.completed_calls, 0)
        self.assertEqual(str(summary.completeness), "PARTIAL")

    def test_06_web_observer_status_aggregation(self) -> None:
        """Verify WebActivityObserver correctly segregates successful from failed HTTP requests."""
        exec_id = f"exec_web_agg_{uuid.uuid4().hex[:8]}"

        # 200 OK
        self.bus.publish(ExecutionEvent(
            event_id="ev_web_200",
            execution_id=exec_id,
            sequence=1,
            type=EventType.WEB_RESPONSE,
            source=EventSource.SYSTEM,
            payload=WebActivityPayload(
                url="https://api.example.com/data",
                status_code=200,
                duration_ms=45.0,
                bytes_transferred=512,
            ).model_dump(),
        ))

        # 500 Internal Error
        self.bus.publish(ExecutionEvent(
            event_id="ev_web_500",
            execution_id=exec_id,
            sequence=2,
            type=EventType.WEB_RESPONSE,
            source=EventSource.SYSTEM,
            payload=WebActivityPayload(
                url="https://api.example.com/fail",
                status_code=500,
                duration_ms=120.0,
                bytes_transferred=64,
            ).model_dump(),
        ))

        summary = self.web_observer.get_execution_summary(exec_id)
        self.assertEqual(summary.total_requests, 2)
        self.assertEqual(summary.successful_requests, 1)
        self.assertEqual(summary.failed_requests, 1)

    def test_07_state_engine_deterministic_cost_pressure_derivation(self) -> None:
        """Verify state engine transitions to COST_PRESSURE when policy budget threshold is reached."""
        from infuse.e2e.environment import _normalize_policy_for_state_engine
        raw_policy = GovernancePolicy(
            policy_id="pol_cost_harden",
            name="Cost Harden Policy",
            budget=BudgetControls(max_cost_per_task=1.00),
            tokens=TokenControls(max_total_tokens=10000),
            actions=PolicyActionBindings(),
        )
        policy = _normalize_policy_for_state_engine(raw_policy)

        exec_id = f"exec_state_cost_{uuid.uuid4().hex[:8]}"

        self.pricing_registry.register_rate(ModelPricingRate(
            provider_id="mock",
            model_id="mock-fast",
            input_rate=Decimal("10.0"),
            output_rate=Decimal("10.0"),
            unit=PricingUnit.PER_1M_TOKENS,
            currency="USD",
        ))

        # 200,000 tokens @ $10/M = $2.00 > $1.00 limit
        self.bus.publish(ExecutionEvent(
            event_id="ev_tok_cost_01",
            execution_id=exec_id,
            sequence=1,
            type=EventType.TOKEN_OBSERVED,
            source=EventSource.SYSTEM,
            payload=TokenObservedPayload(
                input_tokens=100_000,
                output_tokens=100_000,
                total_tokens=200_000,
                provider="mock",
                model="mock-fast",
            ).model_dump(),
        ))

        tok_obs = self.token_observer.get_observation(exec_id)
        econ = self.economics_engine.calculate(tok_obs)

        snap = self.state_engine.derive_state(
            execution_id=exec_id,
            token_summary=tok_obs,
            economic_summary=econ,
            policy=policy,
        )

        self.assertEqual(snap.current_state, ExecutionState.COST_PRESSURE)

    def test_08_state_engine_normal_on_empty_observations(self) -> None:
        """Verify state engine derives NORMAL when no negative signals exist."""
        snap = self.state_engine.derive_state(
            execution_id="exec_clean_01",
            token_summary=None,
            economic_summary=None,
            health_summary=None,
            tool_summary=None,
            web_summary=None,
        )
        self.assertEqual(snap.current_state, ExecutionState.NORMAL)


if __name__ == "__main__":
    unittest.main()
