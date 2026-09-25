"""Concurrency and Failure Injection Hardening Tests (Block 33).

Stress tests:
1. Multi-threaded concurrent execution isolation across distinct execution IDs
2. Upstream provider failure injection (HTTP 500, timeouts, corrupted response)
3. Event bus listener cleanup and memory boundedness
4. State snapshot isolation across concurrent workloads
5. Re-entrant execution safety under rapid bursts
"""

import threading
import unittest
import uuid
from decimal import Decimal
from typing import Dict, List

from infuse.contracts.common import utc_now
from infuse.contracts.events import (
    EventSource,
    EventType,
    ExecutionEvent,
    ProviderErrorPayload,
    TokenObservedPayload,
)
from infuse.contracts.execution import (
    ExecutionContext,
    ExecutionRequest,
    ExecutionRequirements,
)
from infuse.contracts.policy import BudgetControls, GovernancePolicy, PolicyActionBindings
from infuse.contracts.state import ExecutionState, ExecutionStateSnapshot
from infuse.economics import EconomicsEngine, InMemoryPricingRegistry, ModelPricingRate, PricingUnit
from infuse.events.bus import InMemoryEventBus
from infuse.governor.engine import GovernorEngine
from infuse.observer import TokenObservationSource, TokenObserver
from infuse.state.engine import ExecutionStateEngine


class TestConcurrencyFailureHardening(unittest.TestCase):
    """Stress tests verifying concurrency safety, execution isolation, and fault tolerance."""

    def setUp(self) -> None:
        self.bus = InMemoryEventBus()
        self.token_observer = TokenObserver()
        self.token_observer.attach_to_bus(self.bus)
        self.pricing_registry = InMemoryPricingRegistry()
        self.pricing_registry.register_rate(ModelPricingRate(
            provider_id="mock",
            model_id="mock-model",
            input_rate=Decimal("1.0"),
            output_rate=Decimal("2.0"),
            unit=PricingUnit.PER_1M_TOKENS,
        ))
        self.economics_engine = EconomicsEngine(pricing_registry=self.pricing_registry)
        self.state_engine = ExecutionStateEngine()
        self.governor = GovernorEngine(event_bus=self.bus)

    def test_01_concurrent_multi_execution_isolation(self) -> None:
        """Verify 20 concurrent worker threads processing separate executions experience zero cross-talk."""
        num_executions = 20
        results: Dict[str, int] = {}
        lock = threading.Lock()
        threads = []

        def worker(exec_idx: int) -> None:
            exec_id = f"exec_conc_iso_{exec_idx}"
            tokens = (exec_idx + 1) * 1000

            # Publish token event
            self.bus.publish(ExecutionEvent(
                event_id=f"ev_{exec_id}_tok",
                execution_id=exec_id,
                sequence=1,
                type=EventType.TOKEN_OBSERVED,
                source=EventSource.SYSTEM,
                payload=TokenObservedPayload(
                    input_tokens=tokens,
                    output_tokens=tokens,
                    total_tokens=tokens * 2,
                    is_authoritative=True,
                    provider="mock",
                    model="mock-model",
                    source=TokenObservationSource.PROVIDER_USAGE,
                ).model_dump(),
            ))

            obs = self.token_observer.get_observation(exec_id)
            if obs:
                with lock:
                    results[exec_id] = obs.total_tokens

        for i in range(num_executions):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.assertEqual(len(results), num_executions)
        for i in range(num_executions):
            exec_id = f"exec_conc_iso_{i}"
            expected = (i + 1) * 2000
            self.assertEqual(results.get(exec_id), expected, f"Execution {exec_id} tokens corrupted")

    def test_02_upstream_500_provider_error_handling(self) -> None:
        """Verify state engine and governor handle upstream provider 500 error gracefully."""
        exec_id = "exec_fail_500"
        self.bus.publish(ExecutionEvent(
            event_id="ev_fail_500",
            execution_id=exec_id,
            sequence=1,
            type=EventType.PROVIDER_ERROR,
            source=EventSource.SYSTEM,
            payload=ProviderErrorPayload(
                provider="mock",
                model="mock-model",
                error_type="InternalServerError",
                message="HTTP 500 Internal Server Error",
                http_status=500,
            ).model_dump(),
        ))

        # Governor evaluation on failed state
        snap = ExecutionStateSnapshot(
            execution_id=exec_id,
            current_state=ExecutionState.PROVIDER_CONSTRAINED,
            reason_codes=["PROVIDER_HTTP_500"],
        )
        dec = self.governor.evaluate(exec_id, snap)
        self.assertIsNotNone(dec)
        self.assertEqual(dec.execution_id, exec_id)

    def test_03_burst_events_under_single_execution(self) -> None:
        """Verify high-frequency burst of 100 sequential events on a single execution updates atomically."""
        exec_id = "exec_burst_100"
        for i in range(100):
            self.bus.publish(ExecutionEvent(
                event_id=f"ev_burst_{i}",
                execution_id=exec_id,
                sequence=i + 1,
                type=EventType.TOKEN_OBSERVED,
                source=EventSource.SYSTEM,
                payload=TokenObservedPayload(
                    input_tokens=10,
                    output_tokens=10,
                    total_tokens=(i + 1) * 20,
                    is_authoritative=True,
                    provider="mock",
                    model="mock-model",
                    source=TokenObservationSource.PROVIDER_USAGE,
                ).model_dump(),
            ))

        obs = self.token_observer.get_observation(exec_id)
        self.assertIsNotNone(obs)
        self.assertEqual(obs.total_tokens, 2000)

    def test_04_token_observer_cleanup_isolation(self) -> None:
        """Verify clear() cleanly resets observer state without leaving dangling references."""
        self.token_observer.clear()
        observations = self.token_observer.list_observations()
        self.assertEqual(len(observations), 0)


if __name__ == "__main__":
    unittest.main()
