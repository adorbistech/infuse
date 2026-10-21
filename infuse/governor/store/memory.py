"""Thread-Safe In-Memory Budget Store for Single-Process Deployments (INFUSE_WORKERS=1)."""

import threading
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from infuse.contracts.common import utc_now
from infuse.governor.store.interfaces import (
    BudgetReservationRecord,
    IBudgetStore,
    ReservationStatus,
)


class BudgetExhaustedError(Exception):
    """Raised when an execution request exceeds pre-flight budget limits."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class InMemoryBudgetStore(IBudgetStore):
    """Thread-safe in-memory budget storage and aggregation backend.

    Authoritative for single-process deployments (INFUSE_WORKERS=1).
    Guarantees atomic pre-flight gating, lease/exposure retention on uncertain outcomes,
    and thread-safe daily/monthly bucket aggregation.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._reservations: Dict[str, BudgetReservationRecord] = {}
        self._daily_spend: Dict[str, Decimal] = {}
        self._monthly_spend: Dict[str, Decimal] = {}
        self._is_healthy: bool = True

    def set_healthy(self, healthy: bool) -> None:
        """Allow fault injection for readiness and health checks."""
        with self._lock:
            self._is_healthy = healthy

    def ping(self) -> bool:
        """Health probe check."""
        with self._lock:
            return self._is_healthy

    def get_daily_spend(self, bucket: str) -> Decimal:
        """Get committed daily spend."""
        with self._lock:
            return self._daily_spend.get(bucket, Decimal("0.00"))

    def get_monthly_spend(self, bucket: str) -> Decimal:
        """Get committed monthly spend."""
        with self._lock:
            return self._monthly_spend.get(bucket, Decimal("0.00"))

    def get_daily_effective_exposure(self, bucket: str) -> Decimal:
        """Get total committed spend plus active and uncertain reservations for a daily bucket."""
        with self._lock:
            committed = self._daily_spend.get(bucket, Decimal("0.00"))
            active_or_uncertain = sum(
                r.estimated_cost
                for r in self._reservations.values()
                if r.daily_bucket == bucket and r.status in (ReservationStatus.ACTIVE, ReservationStatus.UNCERTAIN)
            )
            return committed + active_or_uncertain

    def get_monthly_effective_exposure(self, bucket: str) -> Decimal:
        """Get total committed spend plus active and uncertain reservations for a monthly bucket."""
        with self._lock:
            committed = self._monthly_spend.get(bucket, Decimal("0.00"))
            active_or_uncertain = sum(
                r.estimated_cost
                for r in self._reservations.values()
                if r.monthly_bucket == bucket and r.status in (ReservationStatus.ACTIVE, ReservationStatus.UNCERTAIN)
            )
            return committed + active_or_uncertain

    def reserve(
        self,
        reservation_id: str,
        execution_id: str,
        estimated_cost: Decimal,
        daily_bucket: str,
        monthly_bucket: str,
        task_limit: Optional[Decimal] = None,
        daily_limit: Optional[Decimal] = None,
        monthly_limit: Optional[Decimal] = None,
        timestamp: Optional[datetime] = None,
    ) -> BudgetReservationRecord:
        """Atomically test limits and record an ACTIVE reservation."""
        if not self.ping():
            raise RuntimeError("Budget store is unavailable (Fail Closed).")

        now = timestamp or utc_now()

        with self._lock:
            # 1. Task Budget Limit
            if task_limit is not None and estimated_cost > task_limit:
                raise BudgetExhaustedError(
                    f"Estimated cost ${estimated_cost:.4f} exceeds task budget limit of ${task_limit:.4f}.",
                    details={
                        "estimated_cost": float(estimated_cost),
                        "limit": float(task_limit),
                        "limit_type": "max_cost_per_task",
                    },
                )

            # 2. Daily Budget Limit
            if daily_limit is not None:
                current_exposure = self.get_daily_effective_exposure(daily_bucket)
                projected_day = current_exposure + estimated_cost
                if projected_day > daily_limit:
                    current_committed = self._daily_spend.get(daily_bucket, Decimal("0.00"))
                    active_reserved = current_exposure - current_committed
                    raise BudgetExhaustedError(
                        f"Projected daily spend ${projected_day:.4f} exceeds daily budget limit of ${daily_limit:.4f}.",
                        details={
                            "projected_spend": float(projected_day),
                            "current_spent": float(current_committed),
                            "active_reserved": float(active_reserved),
                            "estimated_cost": float(estimated_cost),
                            "limit": float(daily_limit),
                            "limit_type": "max_cost_per_day",
                        },
                    )

            # 3. Monthly Budget Limit
            if monthly_limit is not None:
                current_exposure = self.get_monthly_effective_exposure(monthly_bucket)
                projected_month = current_exposure + estimated_cost
                if projected_month > monthly_limit:
                    current_committed = self._monthly_spend.get(monthly_bucket, Decimal("0.00"))
                    active_reserved = current_exposure - current_committed
                    raise BudgetExhaustedError(
                        f"Projected monthly spend ${projected_month:.4f} exceeds monthly budget limit of ${monthly_limit:.4f}.",
                        details={
                            "projected_spend": float(projected_month),
                            "current_spent": float(current_committed),
                            "active_reserved": float(active_reserved),
                            "estimated_cost": float(estimated_cost),
                            "limit": float(monthly_limit),
                            "limit_type": "max_cost_per_month",
                        },
                    )

            # Record ACTIVE reservation
            record = BudgetReservationRecord(
                reservation_id=reservation_id,
                execution_id=execution_id,
                estimated_cost=estimated_cost,
                reserved_at=now,
                daily_bucket=daily_bucket,
                monthly_bucket=monthly_bucket,
                status=ReservationStatus.ACTIVE,
            )
            self._reservations[reservation_id] = record
            return record

    def reconcile(
        self,
        reservation_id: str,
        actual_cost: Decimal,
    ) -> Optional[BudgetReservationRecord]:
        """Atomically transition ACTIVE or UNCERTAIN reservation to RECONCILED with actual cost.

        Guarantees idempotency under lock: repeated calls for an already-reconciled reservation
        return the existing record and do not double-count daily or monthly spend.
        Invalid transitions from terminal RELEASED state are rejected without accounting changes.
        """
        with self._lock:
            record = self._reservations.get(reservation_id)
            if not record:
                return None

            # Idempotency guard: Already reconciled reservations must not increment aggregates again
            if record.status == ReservationStatus.RECONCILED:
                return record

            # State transition guard: Released reservations are terminal and cannot be reconciled
            if record.status == ReservationStatus.RELEASED:
                return record

            record.status = ReservationStatus.RECONCILED
            record.actual_cost = max(Decimal("0.00"), actual_cost)

            # Commit actual spend into aggregates exactly once
            self._daily_spend[record.daily_bucket] = (
                self._daily_spend.get(record.daily_bucket, Decimal("0.00")) + record.actual_cost
            )
            self._monthly_spend[record.monthly_bucket] = (
                self._monthly_spend.get(record.monthly_bucket, Decimal("0.00")) + record.actual_cost
            )
            return record

    def release(self, reservation_id: str) -> Optional[BudgetReservationRecord]:
        """Atomically release an ACTIVE reservation on confirmed pre-dispatch failure ($0 spend).

        Guarantees idempotency: repeated calls for an already-released reservation return the record.
        Reconciled reservations cannot be transitioned to RELEASED to protect committed spend.
        """
        with self._lock:
            record = self._reservations.get(reservation_id)
            if not record:
                return None
            if record.status == ReservationStatus.RELEASED:
                return record
            if record.status == ReservationStatus.RECONCILED:
                return record
            record.status = ReservationStatus.RELEASED
            return record

    def mark_uncertain(
        self,
        reservation_id: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> Optional[BudgetReservationRecord]:
        """Transition reservation to UNCERTAIN upon ambiguous timeout/disconnect, retaining exposure.

        Guarantees idempotency: terminal states (RECONCILED, RELEASED) are not overwritten.
        """
        with self._lock:
            record = self._reservations.get(reservation_id)
            if not record:
                return None
            if record.status in (ReservationStatus.RECONCILED, ReservationStatus.RELEASED):
                return record
            record.status = ReservationStatus.UNCERTAIN
            if details:
                record.metadata["uncertain_details"] = details
            return record

    def record_retry_cost(
        self,
        reservation_id: str,
        additional_cost: Decimal,
        task_limit: Optional[Decimal] = None,
    ) -> BudgetReservationRecord:
        """Record additional cost on active reservation for retries."""
        with self._lock:
            record = self._reservations.get(reservation_id)
            if not record:
                raise KeyError(f"Reservation '{reservation_id}' not found.")

            new_est = record.estimated_cost + additional_cost
            if task_limit is not None and new_est > task_limit:
                raise BudgetExhaustedError(
                    f"Cumulative retry/fallback cost ${new_est:.4f} exceeds task budget limit of ${task_limit:.4f}.",
                    details={"cumulative_cost": float(new_est), "limit": float(task_limit)},
                )
            record.estimated_cost = new_est
            return record

    def get_reservation(self, reservation_id: str) -> Optional[BudgetReservationRecord]:
        """Retrieve reservation record by identifier."""
        with self._lock:
            return self._reservations.get(reservation_id)

    def clear(self) -> None:
        """Reset all store state."""
        with self._lock:
            self._reservations.clear()
            self._daily_spend.clear()
            self._monthly_spend.clear()
            self._is_healthy = True
