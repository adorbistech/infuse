"""Comprehensive Unit, Integration, and Isolation Test Suite for Block 16 Economics Engine."""

import inspect
import sys
import threading
import unittest
from decimal import Decimal
from typing import Optional

from infuse.contracts.events import EventSource, EventType, ExecutionEvent
from infuse.economics.calculator import (
    calculate_dimension_cost,
    calculate_execution_economics,
)
from infuse.economics.engine import EconomicsEngine
from infuse.economics.errors import InvalidPricingRateError
from infuse.economics.models import (
    EconomicCompleteness,
    ModelPricingRate,
    PricingUnit,
)
from infuse.economics.pricing_registry import InMemoryPricingRegistry
from infuse.events.bus import InMemoryEventBus
from infuse.observer.models import ExecutionTokenSummary, TokenObservationSource
from infuse.observer.observer import TokenObserver


class TestEconomicsEngine(unittest.TestCase):
    """Test suite verifying exact Decimal economics calculation, unit normalization, completeness, and isolation."""

    def setUp(self) -> None:
        self.pricing_registry = InMemoryPricingRegistry()
        self.engine = EconomicsEngine(pricing_registry=self.pricing_registry)

    def _sample_summary(
        self,
        execution_id: str = "exec_econ_01",
        provider_id: str = "openai",
        model_id: str = "gpt-4o",
        input_tokens: Optional[int] = 1000,
        output_tokens: Optional[int] = 500,
        cached_tokens: Optional[int] = None,
        total_tokens: Optional[int] = 1500,
        is_authoritative: bool = True,
        is_finalized: bool = False
    ) -> ExecutionTokenSummary:
        return ExecutionTokenSummary(
            execution_id=execution_id,
            provider_id=provider_id,
            model_id=model_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=cached_tokens,
            total_tokens=total_tokens,
            is_authoritative=is_authoritative,
            is_finalized=is_finalized,
            events_count=1,
            last_sequence=1
        )

    # 1. Calculation & Unit Normalization
    def test_01_input_and_output_token_cost_per_1m_tokens(self) -> None:
        """Verify cost calculation with PER_1M_TOKENS rates."""
        # 1,000 input tokens at $5.00/1M = 0.005
        # 500 output tokens at $15.00/1M = 0.0075
        # Total = 0.0125
        self.pricing_registry.register_rate(ModelPricingRate(
            provider_id="openai",
            model_id="gpt-4o",
            input_rate=Decimal("5.00"),
            output_rate=Decimal("15.00"),
            unit=PricingUnit.PER_1M_TOKENS,
            currency="USD"
        ))

        summary = self._sample_summary(input_tokens=1000, output_tokens=500)
        econ = self.engine.calculate(summary)

        self.assertEqual(econ.input_cost, Decimal("0.0050000"))
        self.assertEqual(econ.output_cost, Decimal("0.0075000"))
        self.assertEqual(econ.total_cost, Decimal("0.0125000"))
        self.assertEqual(econ.currency, "USD")
        self.assertEqual(econ.completeness, EconomicCompleteness.COMPLETE)

    def test_02_cost_normalization_per_1k_tokens(self) -> None:
        """Verify cost calculation with PER_1K_TOKENS rates."""
        # 2,000 input tokens at $0.01/1K = 0.02
        # 1,000 output tokens at $0.03/1K = 0.03
        # Total = 0.05
        self.pricing_registry.register_rate(ModelPricingRate(
            provider_id="anthropic",
            model_id="claude-3-haiku",
            input_rate=Decimal("0.01"),
            output_rate=Decimal("0.03"),
            unit=PricingUnit.PER_1K_TOKENS,
            currency="USD"
        ))

        summary = self._sample_summary(
            provider_id="anthropic",
            model_id="claude-3-haiku",
            input_tokens=2000,
            output_tokens=1000
        )
        econ = self.engine.calculate(summary)

        self.assertEqual(econ.input_cost, Decimal("0.0200"))
        self.assertEqual(econ.output_cost, Decimal("0.0300"))
        self.assertEqual(econ.total_cost, Decimal("0.0500"))
        self.assertEqual(econ.completeness, EconomicCompleteness.COMPLETE)

    def test_03_cost_normalization_per_token(self) -> None:
        """Verify cost calculation with PER_TOKEN rate."""
        # 100 tokens at $0.000002/token = 0.0002
        self.pricing_registry.register_rate(ModelPricingRate(
            provider_id="custom",
            model_id="tiny-llm",
            input_rate=Decimal("0.000002"),
            output_rate=Decimal("0.000005"),
            unit=PricingUnit.PER_TOKEN,
            currency="EUR"
        ))

        summary = self._sample_summary(
            provider_id="custom",
            model_id="tiny-llm",
            input_tokens=100,
            output_tokens=200
        )
        econ = self.engine.calculate(summary)

        self.assertEqual(econ.input_cost, Decimal("0.000200"))
        self.assertEqual(econ.output_cost, Decimal("0.001000"))
        self.assertEqual(econ.total_cost, Decimal("0.001200"))
        self.assertEqual(econ.currency, "EUR")

    def test_04_exact_decimal_arithmetic_no_binary_float_drift(self) -> None:
        """Verify arithmetic retains exact precision without floating point inaccuracies."""
        self.pricing_registry.register_rate(ModelPricingRate(
            provider_id="test",
            model_id="precision-test",
            input_rate=Decimal("0.1"),
            output_rate=Decimal("0.2"),
            unit=PricingUnit.PER_1K_TOKENS,
            currency="USD"
        ))

        # 1000 input at 0.1/1k = 0.1, 2000 output at 0.2/1k = 0.4 -> sum is 0.5 exactly (not 0.5000000000000001)
        summary = self._sample_summary(
            provider_id="test",
            model_id="precision-test",
            input_tokens=1000,
            output_tokens=2000
        )
        econ = self.engine.calculate(summary)

        self.assertEqual(econ.input_cost, Decimal("0.100"))
        self.assertEqual(econ.output_cost, Decimal("0.400"))
        self.assertEqual(econ.total_cost, Decimal("0.500"))

    def test_05_cached_tokens_cost_calculation(self) -> None:
        """Verify cached prompt token cost calculation."""
        self.pricing_registry.register_rate(ModelPricingRate(
            provider_id="anthropic",
            model_id="claude-3-5-sonnet",
            input_rate=Decimal("3.00"),
            output_rate=Decimal("15.00"),
            cached_rate=Decimal("0.30"),
            unit=PricingUnit.PER_1M_TOKENS,
            currency="USD"
        ))

        summary = self._sample_summary(
            provider_id="anthropic",
            model_id="claude-3-5-sonnet",
            input_tokens=10000,
            output_tokens=1000,
            cached_tokens=50000
        )
        econ = self.engine.calculate(summary)

        self.assertEqual(econ.input_cost, Decimal("0.030000"))
        self.assertEqual(econ.output_cost, Decimal("0.015000"))
        self.assertEqual(econ.cached_cost, Decimal("0.015000"))
        self.assertEqual(econ.total_cost, Decimal("0.060000"))
        self.assertEqual(econ.completeness, EconomicCompleteness.COMPLETE)

    # 2. Currency Handling
    def test_06_unspecified_currency_is_none(self) -> None:
        """Verify missing currency in rate is preserved as None rather than defaulted to USD."""
        self.pricing_registry.register_rate(ModelPricingRate(
            provider_id="local",
            model_id="llama-3",
            input_rate=Decimal("1.00"),
            output_rate=Decimal("2.00"),
            unit=PricingUnit.PER_1M_TOKENS,
            currency=None
        ))

        summary = self._sample_summary(provider_id="local", model_id="llama-3")
        econ = self.engine.calculate(summary)

        self.assertIsNone(econ.currency)
        self.assertEqual(econ.completeness, EconomicCompleteness.COMPLETE)

    # 3. Missing Data & Economic Completeness
    def test_07_missing_pricing_rate_returns_unknown_completeness(self) -> None:
        """Verify unregistered model pricing results in UNKNOWN completeness and None costs."""
        summary = self._sample_summary(provider_id="unknown_provider", model_id="unknown_model")
        econ = self.engine.calculate(summary)

        self.assertEqual(econ.completeness, EconomicCompleteness.UNKNOWN)
        self.assertIsNone(econ.input_cost)
        self.assertIsNone(econ.output_cost)
        self.assertIsNone(econ.total_cost)
        self.assertIsNone(econ.currency)

    def test_08_partial_pricing_rate_dimensions(self) -> None:
        """Verify partial pricing rate (e.g. only input rate declared) yields PARTIAL completeness."""
        self.pricing_registry.register_rate(ModelPricingRate(
            provider_id="provider_partial",
            model_id="model_partial",
            input_rate=Decimal("5.00"),
            output_rate=None,
            unit=PricingUnit.PER_1M_TOKENS,
            currency="USD"
        ))

        summary = self._sample_summary(
            provider_id="provider_partial",
            model_id="model_partial",
            input_tokens=1000,
            output_tokens=500
        )
        econ = self.engine.calculate(summary)

        self.assertEqual(econ.completeness, EconomicCompleteness.PARTIAL)
        self.assertEqual(econ.input_cost, Decimal("0.0050000"))
        self.assertIsNone(econ.output_cost)
        self.assertEqual(econ.total_cost, Decimal("0.0050000"))

    def test_09_unknown_cost_is_never_silently_converted_to_zero(self) -> None:
        """Verify unknown dimensions remain None and are not fabricated as 0.0."""
        self.pricing_registry.register_rate(ModelPricingRate(
            provider_id="p1",
            model_id="m1",
            input_rate=Decimal("1.00"),
            output_rate=None,
            unit=PricingUnit.PER_1M_TOKENS
        ))

        summary = self._sample_summary(provider_id="p1", model_id="m1", input_tokens=None, output_tokens=500)
        econ = self.engine.calculate(summary)

        self.assertIsNone(econ.input_cost)
        self.assertIsNone(econ.output_cost)
        self.assertIsNone(econ.total_cost)
        self.assertEqual(econ.completeness, EconomicCompleteness.UNKNOWN)

    # 4. Idempotency & Cumulative Updates
    def test_10_cumulative_usage_updates_recalculate_cleanly(self) -> None:
        """Verify calculating updated cumulative usage snapshots recalculates exact costs without double-counting."""
        self.pricing_registry.register_rate(ModelPricingRate(
            provider_id="openai",
            model_id="gpt-4o",
            input_rate=Decimal("10.00"),
            output_rate=Decimal("20.00"),
            unit=PricingUnit.PER_1M_TOKENS,
            currency="USD"
        ))

        # Snapshot 1: 1,000 input, 100 output -> 0.01 + 0.002 = 0.012
        s1 = self._sample_summary(input_tokens=1000, output_tokens=100)
        econ1 = self.engine.calculate(s1)
        self.assertEqual(econ1.total_cost, Decimal("0.0120000"))

        # Snapshot 2: 1,000 input, 200 output -> 0.01 + 0.004 = 0.014 (recalculated, not 0.012 + 0.014)
        s2 = self._sample_summary(input_tokens=1000, output_tokens=200)
        econ2 = self.engine.calculate(s2)
        self.assertEqual(econ2.total_cost, Decimal("0.0140000"))

    def test_11_repeated_calculation_is_deterministic_and_idempotent(self) -> None:
        """Verify calling calculate repeatedly on the same summary produces identical results."""
        self.pricing_registry.register_rate(ModelPricingRate(
            provider_id="openai",
            model_id="gpt-4o",
            input_rate=Decimal("5.00"),
            output_rate=Decimal("15.00"),
            unit=PricingUnit.PER_1M_TOKENS
        ))

        summary = self._sample_summary(input_tokens=1000, output_tokens=500)
        r1 = self.engine.calculate(summary)
        r2 = self.engine.calculate(summary)

        self.assertEqual(r1.total_cost, r2.total_cost)
        self.assertEqual(r1.input_cost, r2.input_cost)
        self.assertEqual(r1.output_cost, r2.output_cost)

    # 5. Finalization & Execution State Propagation
    def test_12_finalization_status_propagated(self) -> None:
        """Verify completion and finalization flags are preserved from token summary."""
        self.pricing_registry.register_rate(ModelPricingRate(
            provider_id="openai",
            model_id="gpt-4o",
            input_rate=Decimal("5.00"),
            output_rate=Decimal("15.00"),
            unit=PricingUnit.PER_1M_TOKENS
        ))

        summary = self._sample_summary(is_finalized=True)
        econ = self.engine.calculate(summary)

        self.assertTrue(econ.is_finalized)
        self.assertTrue(econ.is_authoritative)

    # 6. Multiple Executions Isolation
    def test_13_multiple_executions_isolation(self) -> None:
        """Verify multiple executions are cached and calculated independently."""
        self.pricing_registry.register_rate(ModelPricingRate(
            provider_id="openai",
            model_id="gpt-4o",
            input_rate=Decimal("10.00"),
            output_rate=Decimal("30.00"),
            unit=PricingUnit.PER_1M_TOKENS,
            currency="USD"
        ))

        s1 = self._sample_summary(execution_id="exec_1", input_tokens=1000, output_tokens=1000)
        s2 = self._sample_summary(execution_id="exec_2", input_tokens=5000, output_tokens=5000)

        e1 = self.engine.calculate(s1)
        e2 = self.engine.calculate(s2)

        self.assertEqual(e1.total_cost, Decimal("0.040000"))
        self.assertEqual(e2.total_cost, Decimal("0.200000"))
        self.assertEqual(len(self.engine.list_summaries()), 2)

    # 7. Pricing Registry Validation
    def test_14_pricing_registry_invalid_rate_validation(self) -> None:
        """Verify registering negative rates raises InvalidPricingRateError."""
        with self.assertRaises(InvalidPricingRateError):
            self.pricing_registry.register_rate(ModelPricingRate(
                provider_id="p1",
                model_id="m1",
                input_rate=Decimal("-1.00")
            ))

    # 8. Token Observer Integration
    def test_15_integration_with_token_observer(self) -> None:
        """Verify TokenObserver produces summaries that calculate cleanly in EconomicsEngine."""
        observer = TokenObserver()
        self.pricing_registry.register_rate(ModelPricingRate(
            provider_id="anthropic",
            model_id="claude-3-5-sonnet",
            input_rate=Decimal("3.00"),
            output_rate=Decimal("15.00"),
            unit=PricingUnit.PER_1M_TOKENS,
            currency="USD"
        ))

        # Deliver events to TokenObserver
        observer.handle_event(ExecutionEvent(
            event_id="evt_start",
            execution_id="exec_flow_01",
            type=EventType.EXECUTION_STARTED,
            sequence=0,
            payload={"provider_id": "anthropic", "model_id": "claude-3-5-sonnet"}
        ))
        observer.handle_event(ExecutionEvent(
            event_id="evt_usage",
            execution_id="exec_flow_01",
            type=EventType.TOKEN_OBSERVED,
            sequence=1,
            payload={
                "provider": "anthropic",
                "model": "claude-3-5-sonnet",
                "input_tokens": 10000,
                "output_tokens": 2000,
                "is_authoritative": True
            }
        ))

        token_summary = observer.get_observation("exec_flow_01")
        self.assertIsNotNone(token_summary)

        # Process in EconomicsEngine
        econ_summary = self.engine.calculate(token_summary)
        self.assertEqual(econ_summary.input_cost, Decimal("0.030000"))
        self.assertEqual(econ_summary.output_cost, Decimal("0.030000"))
        self.assertEqual(econ_summary.total_cost, Decimal("0.060000"))
        self.assertEqual(econ_summary.currency, "USD")
        self.assertEqual(econ_summary.completeness, EconomicCompleteness.COMPLETE)

    # 9. Architectural Isolation Checks
    def test_16_zero_database_imports_in_economics_package(self) -> None:
        """Verify economics package contains zero database library imports."""
        import infuse.economics
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.economics")]

        forbidden = ["sqlite3", "psycopg2", "asyncpg", "sqlalchemy", "redis", "qdrant_client", "motor", "pymongo"]
        for mod in modules:
            src = inspect.getsource(mod)
            for f in forbidden:
                self.assertNotIn(f"import {f}", src)
                self.assertNotIn(f"from {f}", src)

    def test_17_zero_provider_and_broker_sdk_imports(self) -> None:
        """Verify economics package contains zero provider or message broker SDK imports."""
        import infuse.economics
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.economics")]

        forbidden = [
            "openai", "anthropic", "google.generativeai", "cohere", "langchain", "crewai", "autogen",
            "kafka", "pika", "nats", "redis", "aioredis", "celery", "kombu"
        ]
        for mod in modules:
            src = inspect.getsource(mod)
            for f in forbidden:
                self.assertNotIn(f"import {f}", src)
                self.assertNotIn(f"from {f}", src)

    def test_18_zero_billing_policy_or_governor_logic(self) -> None:
        """Verify economics package contains zero billing, markup, budget policy, or Governor decision logic."""
        import infuse.economics
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.economics")]

        forbidden_patterns = [
            "invoice",
            "create_bill",
            "apply_markup",
            "calculate_margin",
            "tax_rate",
            "issue_action",
            "apply_governance",
            "stop_execution",
            "throttle",
            "route_request"
        ]
        for mod in modules:
            src = inspect.getsource(mod)
            for p in forbidden_patterns:
                self.assertNotIn(p, src)


if __name__ == "__main__":
    unittest.main()
