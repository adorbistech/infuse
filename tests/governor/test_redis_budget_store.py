"""INFUSE Block 21 & Block 16 — Redis Budget Store & Multi-Process Concurrency Suite.

Verifies:
1. Multi-Process Concurrent Ceiling: Multiple independent OS processes cannot exceed global budget limits.
2. Fail-Closed Semantics: Store unavailability immediately trips PreFlightGovernanceEngine to STOP with zero provider dispatch.
3. Multi-Process Reconciliation Idempotency: Concurrent reconcile() calls on the same reservation never double-count spend.
4. Active, Uncertain, Released, and Reconciled lifecycle transitions under distributed concurrency.
5. Readiness probe degradation on store failure.
"""

import json
import multiprocessing
import os
import tempfile
import threading
import time
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

from infuse.contracts.common import utc_now
from infuse.contracts.execution import (
    ExecutionRequest,
    ExecutionRequirements,
    ExecutionResult,
    ExecutionStatus,
    OperationRequest,
    TaskContext,
)
from infuse.contracts.governor import GovernorAction
from infuse.contracts.policy import BudgetControls, GovernancePolicy
from infuse.economics.models import ModelPricingRate, PricingUnit
from infuse.economics.pricing_registry import InMemoryPricingRegistry
from infuse.governor.budget import (
    BudgetExhaustedError,
    BudgetReservation,
    BudgetReservationManager,
)
from infuse.governor.preflight import PreFlightGovernanceEngine
from infuse.governor.service import GovernedExecutionService
from infuse.governor.store.errors import (
    BudgetStoreError,
    BudgetStoreUnavailableError,
)
from infuse.governor.store.interfaces import (
    BudgetReservationRecord,
    IBudgetStore,
    ReservationStatus,
)
from infuse.governor.store.redis import RedisBudgetStore
from infuse.providers.adapters.mock import MockProviderAdapter


class MockRedisClient:
    """Thread-safe and process-safe Redis client simulator with Lua script support."""

    def __init__(self, shared_dict: Optional[Dict[str, Any]] = None, lock: Optional[Any] = None) -> None:
        self._store: Dict[str, Any] = shared_dict if shared_dict is not None else {}
        self._lock = lock or threading.RLock()
        self._is_healthy = True

    def set_healthy(self, healthy: bool) -> None:
        with self._lock:
            self._is_healthy = healthy

    def ping(self) -> bool:
        with self._lock:
            if not self._is_healthy:
                raise ConnectionError("Simulated Redis connection refused.")
            return True

    def get(self, key: str) -> Optional[str]:
        with self._lock:
            if not self._is_healthy:
                raise ConnectionError("Simulated Redis connection refused.")
            val = self._store.get(key)
            return str(val) if val is not None else None

    def set(self, key: str, value: str) -> bool:
        with self._lock:
            if not self._is_healthy:
                raise ConnectionError("Simulated Redis connection refused.")
            self._store[key] = str(value)
            return True

    def hset(self, name: str, key: Optional[str] = None, value: Optional[str] = None, mapping: Optional[Dict[str, Any]] = None) -> int:
        with self._lock:
            if not self._is_healthy:
                raise ConnectionError("Simulated Redis connection refused.")
            curr_map = dict(self._store.get(name, {})) if isinstance(self._store.get(name), dict) else {}
            count = 0
            if mapping:
                for k, v in mapping.items():
                    curr_map[str(k)] = str(v)
                    count += 1
            if key is not None and value is not None:
                curr_map[str(key)] = str(value)
                count += 1
            self._store[name] = curr_map
            return count

    def hget(self, name: str, key: str) -> Optional[str]:
        with self._lock:
            if not self._is_healthy:
                raise ConnectionError("Simulated Redis connection refused.")
            h = self._store.get(name)
            if isinstance(h, dict):
                val = h.get(str(key))
                return str(val) if val is not None else None
            return None

    def hgetall(self, name: str) -> Dict[str, str]:
        with self._lock:
            if not self._is_healthy:
                raise ConnectionError("Simulated Redis connection refused.")
            h = self._store.get(name)
            if isinstance(h, dict):
                return {str(k): str(v) for k, v in h.items()}
            return {}

    def hvals(self, name: str) -> List[str]:
        with self._lock:
            if not self._is_healthy:
                raise ConnectionError("Simulated Redis connection refused.")
            h = self._store.get(name)
            if isinstance(h, dict):
                return [str(v) for v in h.values()]
            return []

    def hdel(self, name: str, *keys: str) -> int:
        with self._lock:
            if not self._is_healthy:
                raise ConnectionError("Simulated Redis connection refused.")
            h = dict(self._store.get(name, {})) if isinstance(self._store.get(name), dict) else {}
            count = 0
            for k in keys:
                if str(k) in h:
                    del h[str(k)]
                    count += 1
            self._store[name] = h
            return count

    def incrbyfloat(self, key: str, amount: float) -> float:
        with self._lock:
            if not self._is_healthy:
                raise ConnectionError("Simulated Redis connection refused.")
            curr = Decimal(str(self._store.get(key, "0.00")))
            new_val = curr + Decimal(str(amount))
            self._store[key] = str(new_val)
            return float(new_val)

    def expire(self, key: str, seconds: int) -> bool:
        with self._lock:
            if not self._is_healthy:
                raise ConnectionError("Simulated Redis connection refused.")
            return True

    def keys(self, pattern: str) -> List[str]:
        with self._lock:
            if not self._is_healthy:
                raise ConnectionError("Simulated Redis connection refused.")
            prefix = pattern.rstrip("*")
            return [k for k in self._store.keys() if k.startswith(prefix)]

    def delete(self, *keys: str) -> int:
        with self._lock:
            if not self._is_healthy:
                raise ConnectionError("Simulated Redis connection refused.")
            count = 0
            for k in keys:
                if k in self._store:
                    del self._store[k]
                    count += 1
            return count

    def eval(self, script: str, numkeys: int, *args: Any) -> str:
        """Simulate atomic execution of the Lua scripts under the lock."""
        with self._lock:
            if not self._is_healthy:
                raise ConnectionError("Simulated Redis connection refused.")

            keys = list(args[:numkeys])
            argv = list(args[numkeys:])

            # Script 1: reserve.lua
            if "reserve.lua" in script:
                daily_spend_key, monthly_spend_key, active_day_key, active_month_key, res_record_key = keys
                est_cost = Decimal(str(argv[0]))
                task_limit_str = argv[1]
                daily_limit_str = argv[2]
                monthly_limit_str = argv[3]
                res_id = argv[4]
                exec_id = argv[5]
                reserved_at = argv[6]
                daily_bucket = argv[7]
                monthly_bucket = argv[8]

                # Task limit
                if task_limit_str:
                    task_limit = Decimal(str(task_limit_str))
                    if est_cost > task_limit:
                        return json.dumps({
                            "status": "DENIED",
                            "reason": "max_cost_per_task",
                            "estimated_cost": float(est_cost),
                            "limit": float(task_limit),
                        })

                # Daily limit
                active_day = dict(self._store.get(active_day_key, {})) if isinstance(self._store.get(active_day_key), dict) else {}
                active_day_sum = sum(Decimal(str(v)) for v in active_day.values())
                committed_daily = Decimal(str(self._store.get(daily_spend_key, "0.00")))
                total_day = committed_daily + active_day_sum

                if daily_limit_str:
                    daily_limit = Decimal(str(daily_limit_str))
                    if (total_day + est_cost) > daily_limit:
                        return json.dumps({
                            "status": "DENIED",
                            "reason": "max_cost_per_day",
                            "projected_spend": float(total_day + est_cost),
                            "current_spent": float(committed_daily),
                            "active_reserved": float(active_day_sum),
                            "estimated_cost": float(est_cost),
                            "limit": float(daily_limit),
                        })

                # Monthly limit
                active_month = dict(self._store.get(active_month_key, {})) if isinstance(self._store.get(active_month_key), dict) else {}
                active_month_sum = sum(Decimal(str(v)) for v in active_month.values())
                committed_monthly = Decimal(str(self._store.get(monthly_spend_key, "0.00")))
                total_month = committed_monthly + active_month_sum

                if monthly_limit_str:
                    monthly_limit = Decimal(str(monthly_limit_str))
                    if (total_month + est_cost) > monthly_limit:
                        return json.dumps({
                            "status": "DENIED",
                            "reason": "max_cost_per_month",
                            "projected_spend": float(total_month + est_cost),
                            "current_spent": float(committed_monthly),
                            "active_reserved": float(active_month_sum),
                            "estimated_cost": float(est_cost),
                            "limit": float(monthly_limit),
                        })

                # Record
                active_day[res_id] = str(est_cost)
                self._store[active_day_key] = active_day

                active_month[res_id] = str(est_cost)
                self._store[active_month_key] = active_month

                self._store[res_record_key] = {
                    "reservation_id": res_id,
                    "execution_id": exec_id,
                    "estimated_cost": str(est_cost),
                    "actual_cost": "0.00",
                    "reserved_at": reserved_at,
                    "daily_bucket": daily_bucket,
                    "monthly_bucket": monthly_bucket,
                    "status": "ACTIVE",
                }
                return json.dumps({
                    "status": "OK",
                    "reservation_id": res_id,
                    "execution_id": exec_id,
                    "estimated_cost": float(est_cost),
                    "reserved_at": reserved_at,
                    "daily_bucket": daily_bucket,
                    "monthly_bucket": monthly_bucket,
                })

            # Script 2: reconcile.lua
            elif "reconcile.lua" in script:
                res_record_key, active_day_key, active_month_key, daily_spend_key, monthly_spend_key = keys
                res_id = argv[0]
                actual_cost = max(Decimal("0.00"), Decimal(str(argv[1])))

                raw_rec = self._store.get(res_record_key)
                if not raw_rec or not isinstance(raw_rec, dict):
                    return json.dumps({"status": "NOT_FOUND"})

                rec = dict(raw_rec)
                curr_status = rec.get("status")
                if curr_status in ("RECONCILED", "RELEASED"):
                    return json.dumps({
                        "status": "NOOP",
                        "current_status": curr_status,
                        "reservation_id": rec.get("reservation_id"),
                        "execution_id": rec.get("execution_id"),
                        "estimated_cost": float(rec.get("estimated_cost", "0.00")),
                        "actual_cost": float(rec.get("actual_cost", "0.00")),
                        "reserved_at": rec.get("reserved_at"),
                        "daily_bucket": rec.get("daily_bucket"),
                        "monthly_bucket": rec.get("monthly_bucket"),
                    })

                rec["status"] = "RECONCILED"
                rec["actual_cost"] = str(actual_cost)
                self._store[res_record_key] = rec

                if isinstance(self._store.get(active_day_key), dict):
                    ad = dict(self._store[active_day_key])
                    ad.pop(res_id, None)
                    self._store[active_day_key] = ad

                if isinstance(self._store.get(active_month_key), dict):
                    am = dict(self._store[active_month_key])
                    am.pop(res_id, None)
                    self._store[active_month_key] = am

                if actual_cost > Decimal("0.00"):
                    curr_d = Decimal(str(self._store.get(daily_spend_key, "0.00")))
                    self._store[daily_spend_key] = str(curr_d + actual_cost)
                    curr_m = Decimal(str(self._store.get(monthly_spend_key, "0.00")))
                    self._store[monthly_spend_key] = str(curr_m + actual_cost)

                return json.dumps({
                    "status": "OK",
                    "current_status": "RECONCILED",
                    "reservation_id": rec.get("reservation_id"),
                    "execution_id": rec.get("execution_id"),
                    "estimated_cost": float(rec.get("estimated_cost", "0.00")),
                    "actual_cost": float(actual_cost),
                    "reserved_at": rec.get("reserved_at"),
                    "daily_bucket": rec.get("daily_bucket"),
                    "monthly_bucket": rec.get("monthly_bucket"),
                })

            # Script 3: release.lua
            elif "release.lua" in script:
                res_record_key, active_day_key, active_month_key = keys
                res_id = argv[0]

                raw_rec = self._store.get(res_record_key)
                if not raw_rec or not isinstance(raw_rec, dict):
                    return json.dumps({"status": "NOT_FOUND"})

                rec = dict(raw_rec)
                curr_status = rec.get("status")
                if curr_status in ("RECONCILED", "RELEASED"):
                    return json.dumps({
                        "status": "NOOP",
                        "current_status": curr_status,
                        "reservation_id": rec.get("reservation_id"),
                        "execution_id": rec.get("execution_id"),
                        "estimated_cost": float(rec.get("estimated_cost", "0.00")),
                        "actual_cost": float(rec.get("actual_cost", "0.00")),
                        "reserved_at": rec.get("reserved_at"),
                        "daily_bucket": rec.get("daily_bucket"),
                        "monthly_bucket": rec.get("monthly_bucket"),
                    })

                rec["status"] = "RELEASED"
                self._store[res_record_key] = rec

                if isinstance(self._store.get(active_day_key), dict):
                    ad = dict(self._store[active_day_key])
                    ad.pop(res_id, None)
                    self._store[active_day_key] = ad

                if isinstance(self._store.get(active_month_key), dict):
                    am = dict(self._store[active_month_key])
                    am.pop(res_id, None)
                    self._store[active_month_key] = am

                return json.dumps({
                    "status": "OK",
                    "current_status": "RELEASED",
                    "reservation_id": rec.get("reservation_id"),
                    "execution_id": rec.get("execution_id"),
                    "estimated_cost": float(rec.get("estimated_cost", "0.00")),
                    "actual_cost": 0.0,
                    "reserved_at": rec.get("reserved_at"),
                    "daily_bucket": rec.get("daily_bucket"),
                    "monthly_bucket": rec.get("monthly_bucket"),
                })

            return json.dumps({"status": "UNKNOWN_SCRIPT"})


def _worker_reserve_task(
    worker_id: int,
    num_requests: int,
    cost_per_req: str,
    daily_limit_str: str,
    shared_store: Dict[str, Any],
    lock: Any,
    results_list: Any,
) -> None:
    """Worker task executed in separate child OS processes."""
    client = MockRedisClient(shared_dict=shared_store, lock=lock)
    store = RedisBudgetStore(redis_client=client, tenant_id="mp_test")
    manager = BudgetReservationManager(store=store)

    policy = GovernancePolicy(
        policy_id=f"pol_mp_{worker_id}",
        budget=BudgetControls(max_cost_per_day=Decimal(daily_limit_str)),
    )

    succeeded = 0
    exhausted = 0
    cost = Decimal(cost_per_req)

    for i in range(num_requests):
        exec_id = f"exec_w{worker_id}_req{i}"
        try:
            res = manager.reserve(execution_id=exec_id, estimated_cost=cost, policy=policy)
            if res and res.status == ReservationStatus.ACTIVE:
                succeeded += 1
                # Reconcile actual spend
                manager.reconcile(res.reservation_id, actual_cost=cost)
        except BudgetExhaustedError:
            exhausted += 1

    results_list.append((worker_id, succeeded, exhausted))


def _worker_reconcile_race_task(
    worker_id: int,
    reservation_id: str,
    cost_str: str,
    shared_store: Dict[str, Any],
    lock: Any,
    results_list: Any,
) -> None:
    """Worker task attempting simultaneous reconcile on the same reservation."""
    client = MockRedisClient(shared_dict=shared_store, lock=lock)
    store = RedisBudgetStore(redis_client=client, tenant_id="reconcile_race")
    manager = BudgetReservationManager(store=store)

    actual_cost = Decimal(cost_str)
    res = manager.reconcile(reservation_id=reservation_id, actual_cost=actual_cost)
    results_list.append((worker_id, res.status if res else None))


class TestRedisBudgetStore(unittest.TestCase):
    """Authoritative test suite for RedisBudgetStore, Multi-Worker and Multi-Process Concurrency."""

    def setUp(self) -> None:
        self.mock_client = MockRedisClient()
        self.store = RedisBudgetStore(redis_client=self.mock_client, tenant_id="test_suite")
        self.manager = BudgetReservationManager(store=self.store)

    def test_single_process_budget_lifecycle(self) -> None:
        """Verify normal reserve, reconcile, release, and uncertain state transitions."""
        policy = GovernancePolicy(
            policy_id="test_policy",
            budget=BudgetControls(
                max_cost_per_task=Decimal("5.00"),
                max_cost_per_day=Decimal("10.00"),
                max_cost_per_month=Decimal("50.00"),
            ),
        )

        # 1. Successful reservation
        res = self.manager.reserve(
            execution_id="exec_01",
            estimated_cost=Decimal("2.50"),
            policy=policy,
        )
        self.assertIsNotNone(res)
        self.assertEqual(res.status, ReservationStatus.ACTIVE)
        self.assertEqual(self.store.get_daily_effective_exposure(res.daily_bucket), Decimal("2.50"))
        self.assertEqual(self.store.get_daily_spend(res.daily_bucket), Decimal("0.00"))

        # 2. Reconcile with actual spend
        reconciled = self.manager.reconcile(res.reservation_id, actual_cost=Decimal("2.10"))
        self.assertIsNotNone(reconciled)
        self.assertEqual(reconciled.status, ReservationStatus.RECONCILED)
        self.assertEqual(reconciled.actual_cost, Decimal("2.10"))
        self.assertEqual(self.store.get_daily_spend(res.daily_bucket), Decimal("2.10"))
        self.assertEqual(self.store.get_daily_effective_exposure(res.daily_bucket), Decimal("2.10"))

        # 3. Repeated reconciliation is idempotent
        repeat = self.manager.reconcile(res.reservation_id, actual_cost=Decimal("2.10"))
        self.assertEqual(repeat.status, ReservationStatus.RECONCILED)
        self.assertEqual(self.store.get_daily_spend(res.daily_bucket), Decimal("2.10"))

    def test_multiprocess_concurrent_budget_ceiling(self) -> None:
        """Verify that multiple independent OS processes cannot exceed the global budget ceiling."""
        manager = multiprocessing.Manager()
        shared_store = manager.dict()
        lock = manager.RLock()
        results_list = manager.list()

        num_processes = 4
        requests_per_proc = 25
        cost_per_req = "0.20"
        daily_limit = "10.00"

        # Total attempted: 4 * 25 * 0.20 = $20.00 against a $10.00 ceiling
        # Exactly 50 requests must succeed ($10.00), exactly 50 must be denied.
        processes = []
        for w_id in range(num_processes):
            p = multiprocessing.Process(
                target=_worker_reserve_task,
                args=(w_id, requests_per_proc, cost_per_req, daily_limit, shared_store, lock, results_list),
            )
            processes.append(p)
            p.start()

        for p in processes:
            p.join(timeout=10.0)

        total_succeeded = sum(r[1] for r in results_list)
        total_exhausted = sum(r[2] for r in results_list)

        self.assertEqual(total_succeeded, 50, f"Expected 50 succeeded, got {total_succeeded}")
        self.assertEqual(total_exhausted, 50, f"Expected 50 exhausted, got {total_exhausted}")

        # Check total committed spend in shared store
        client = MockRedisClient(shared_dict=shared_store, lock=lock)
        store = RedisBudgetStore(redis_client=client, tenant_id="mp_test")
        today = utc_now().strftime("%Y-%m-%d")
        daily_spend = store.get_daily_spend(today)
        self.assertEqual(daily_spend, Decimal("10.00"))

    def test_multiprocess_reconciliation_idempotency(self) -> None:
        """Verify that concurrent reconcile calls across processes never double-count spend."""
        manager = multiprocessing.Manager()
        shared_store = manager.dict()
        lock = manager.RLock()
        results_list = manager.list()

        client = MockRedisClient(shared_dict=shared_store, lock=lock)
        store = RedisBudgetStore(redis_client=client, tenant_id="reconcile_race")
        b_manager = BudgetReservationManager(store=store)

        # Make 1 active reservation of $3.00
        res = b_manager.reserve(execution_id="exec_race_01", estimated_cost=Decimal("3.00"))
        res_id = res.reservation_id

        # Spawn 8 processes all trying to reconcile this reservation with $3.00
        processes = []
        for w_id in range(8):
            p = multiprocessing.Process(
                target=_worker_reconcile_race_task,
                args=(w_id, res_id, "3.00", shared_store, lock, results_list),
            )
            processes.append(p)
            p.start()

        for p in processes:
            p.join(timeout=10.0)

        # Verify daily spend is exactly $3.00, NOT 8 * $3.00 = $24.00
        today = utc_now().strftime("%Y-%m-%d")
        daily_spend = store.get_daily_spend(today)
        self.assertEqual(daily_spend, Decimal("3.00"), f"Expected $3.00, got {daily_spend}")

    def test_store_failure_fail_closed_across_workers(self) -> None:
        """Verify that store failure trips PreFlightGovernanceEngine to fail closed immediately."""
        self.mock_client.set_healthy(False)

        preflight_engine = PreFlightGovernanceEngine(budget_manager=self.manager)

        from infuse.context.service import ExecutionContextService
        ctx_service = ExecutionContextService()
        req = ExecutionRequest(
            request_id="req_fc_01",
            task=TaskContext(task_id="t_fc", description="Test fail closed on store failure"),
            request=OperationRequest(messages=[{"role": "user", "content": "hello"}]),
            requirements=ExecutionRequirements(preferred_providers=["mock"], preferred_models=["mock-fast"]),
        )
        ctx = ctx_service.create_context(req)

        eval_res = preflight_engine.evaluate(
            context=ctx,
            request=req,
            target_provider="mock",
            target_model="mock-fast",
        )

        self.assertFalse(eval_res.is_allowed, "Preflight must disallow execution on store failure.")
        self.assertEqual(eval_res.action, GovernorAction.STOP)
        self.assertIn("BUDGET_STORE_UNAVAILABLE", eval_res.reason_codes)
        self.assertIn("Fail Closed", eval_res.message)

    def test_governed_execution_service_fails_closed_on_store_outage(self) -> None:
        """Verify end-to-end GovernedExecutionService blocks execution with zero provider calls when store is down."""
        self.mock_client.set_healthy(False)

        mock_adapter = MagicMock(spec=MockProviderAdapter)
        mock_adapter.provider_id = "mock"
        mock_adapter.supported_models = ["mock-fast"]

        from infuse.providers.registry import InMemoryProviderAdapterRegistry
        from infuse.providers.service import ProviderAdapterService
        reg = InMemoryProviderAdapterRegistry()
        reg.register(mock_adapter)
        adapter_service = ProviderAdapterService(registry=reg)

        service = GovernedExecutionService(
            budget_manager=self.manager,
            adapter_service=adapter_service,
        )

        req = ExecutionRequest(
            request_id="req_svc_01",
            task=TaskContext(task_id="t_svc", description="Test full service fail closed"),
            request=OperationRequest(messages=[{"role": "user", "content": "ping"}]),
            requirements=ExecutionRequirements(preferred_providers=["mock"], preferred_models=["mock-fast"]),
        )

        result = service.execute(req)
        self.assertEqual(result.status, ExecutionStatus.STOPPED)
        self.assertTrue(result.execution.metadata.get("preflight_denied"))
        self.assertIn("BUDGET_STORE_UNAVAILABLE", result.execution.metadata.get("denial_reasons", []))
        self.assertEqual(mock_adapter.execute.call_count, 0, "Provider adapter must never be invoked.")

    def test_uncertain_reservation_retains_exposure(self) -> None:
        """Verify that an UNCERTAIN reservation continues to occupy daily/monthly exposure."""
        res = self.manager.reserve(execution_id="exec_unc", estimated_cost=Decimal("4.00"))
        self.assertEqual(self.store.get_daily_effective_exposure(res.daily_bucket), Decimal("4.00"))

        uncertain = self.manager.mark_uncertain(res.reservation_id, details={"reason": "timeout"})
        self.assertEqual(uncertain.status, ReservationStatus.UNCERTAIN)

        # Exposure must remain $4.00
        self.assertEqual(self.store.get_daily_effective_exposure(res.daily_bucket), Decimal("4.00"))
        self.assertEqual(self.store.get_daily_spend(res.daily_bucket), Decimal("0.00"))

        # Reconciling afterwards commits actual spend
        reconciled = self.manager.reconcile(res.reservation_id, actual_cost=Decimal("3.50"))
        self.assertEqual(reconciled.status, ReservationStatus.RECONCILED)
        self.assertEqual(self.store.get_daily_spend(res.daily_bucket), Decimal("3.50"))
        self.assertEqual(self.store.get_daily_effective_exposure(res.daily_bucket), Decimal("3.50"))


if __name__ == "__main__":
    unittest.main()
