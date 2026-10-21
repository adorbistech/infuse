"""Authoritative Budget Store Interface Contract for Block 21 & Block 16."""

from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional


class ReservationStatus(str, Enum):
    """Lifecycle status of a budget reservation."""
    ACTIVE = "ACTIVE"
    RECONCILED = "RECONCILED"
    RELEASED = "RELEASED"
    UNCERTAIN = "UNCERTAIN"


class BudgetReservationRecord:
    """Canonical representation of an active, reconciled, released, or uncertain reservation."""

    def __init__(
        self,
        reservation_id: str,
        execution_id: str,
        estimated_cost: Decimal,
        reserved_at: datetime,
        daily_bucket: str,
        monthly_bucket: str,
        status: ReservationStatus = ReservationStatus.ACTIVE,
        actual_cost: Decimal = Decimal("0.00"),
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.reservation_id = reservation_id
        self.execution_id = execution_id
        self.estimated_cost = estimated_cost
        self.actual_cost = actual_cost
        self.reserved_at = reserved_at
        self.daily_bucket = daily_bucket
        self.monthly_bucket = monthly_bucket
        self.status = status
        self.metadata: Dict[str, Any] = metadata or {}

    @property
    def is_active(self) -> bool:
        return self.status == ReservationStatus.ACTIVE

    @is_active.setter
    def is_active(self, value: bool) -> None:
        if value:
            self.status = ReservationStatus.ACTIVE
        elif self.status == ReservationStatus.ACTIVE:
            self.status = ReservationStatus.RELEASED

    @property
    def is_reconciled(self) -> bool:
        return self.status == ReservationStatus.RECONCILED

    @is_reconciled.setter
    def is_reconciled(self, value: bool) -> None:
        if value:
            self.status = ReservationStatus.RECONCILED

    @property
    def is_uncertain(self) -> bool:
        return self.status == ReservationStatus.UNCERTAIN

    @is_uncertain.setter
    def is_uncertain(self, value: bool) -> None:
        if value:
            self.status = ReservationStatus.UNCERTAIN


class IBudgetStore(ABC):
    """Abstract interface contract for budget reservation and aggregation stores."""

    @abstractmethod
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
        ...

    @abstractmethod
    def reconcile(
        self,
        reservation_id: str,
        actual_cost: Decimal,
    ) -> Optional[BudgetReservationRecord]:
        """Atomically transition ACTIVE or UNCERTAIN reservation to RECONCILED with actual cost."""
        ...

    @abstractmethod
    def release(self, reservation_id: str) -> Optional[BudgetReservationRecord]:
        """Atomically release an ACTIVE reservation on confirmed pre-dispatch failure ($0 spend)."""
        ...

    @abstractmethod
    def mark_uncertain(
        self,
        reservation_id: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> Optional[BudgetReservationRecord]:
        """Transition reservation to UNCERTAIN upon ambiguous timeout/disconnect, retaining exposure."""
        ...

    @abstractmethod
    def record_retry_cost(
        self,
        reservation_id: str,
        additional_cost: Decimal,
        task_limit: Optional[Decimal] = None,
    ) -> BudgetReservationRecord:
        """Record additional cost on active reservation for retries."""
        ...

    @abstractmethod
    def get_reservation(self, reservation_id: str) -> Optional[BudgetReservationRecord]:
        """Retrieve reservation record by identifier."""
        ...

    @abstractmethod
    def get_daily_spend(self, bucket: str) -> Decimal:
        """Get committed daily spend for a bucket."""
        ...

    @abstractmethod
    def get_monthly_spend(self, bucket: str) -> Decimal:
        """Get committed monthly spend for a bucket."""
        ...

    @abstractmethod
    def get_daily_effective_exposure(self, bucket: str) -> Decimal:
        """Get total committed spend plus active and uncertain reservations for a daily bucket."""
        ...

    @abstractmethod
    def get_monthly_effective_exposure(self, bucket: str) -> Decimal:
        """Get total committed spend plus active and uncertain reservations for a monthly bucket."""
        ...

    @abstractmethod
    def clear(self) -> None:
        """Reset all store state."""
        ...

    @abstractmethod
    def ping(self) -> bool:
        """Health check for readiness probe."""
        ...
