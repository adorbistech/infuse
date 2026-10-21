"""Distributed Redis-Backed Budget Store for Multi-Worker / Multi-Replica Deployments."""

import json
import logging
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from infuse.contracts.common import utc_now
from infuse.governor.store.errors import (
    BudgetStoreError,
    BudgetStoreUnavailableError,
)
from infuse.governor.store.interfaces import (
    BudgetReservationRecord,
    IBudgetStore,
    ReservationStatus,
)
from infuse.governor.store.memory import BudgetExhaustedError

logger = logging.getLogger("infuse.governor.store.redis")

# Path to Lua scripts
_SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "scripts")


def _read_lua_script(filename: str) -> str:
    path = os.path.join(_SCRIPTS_DIR, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    raise FileNotFoundError(f"Lua script '{filename}' not found at {path}")


class RedisBudgetStore(IBudgetStore):
    """Distributed, atomic budget storage backend backed by Redis and Lua scripts.

    Enforces global task, daily, and monthly budget limits across multiple independent
    processes (INFUSE_WORKERS > 1) and container replicas. Guarantees fail-closed
    behavior upon store outage, TTL-based auto-reclamation for crashed workers,
    and idempotent reconciliation under distributed concurrency.
    """

    def __init__(
        self,
        redis_client: Optional[Any] = None,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        prefix: str = "infuse:budget",
        tenant_id: str = "default",
        default_ttl_seconds: int = 120,
    ) -> None:
        self.prefix = prefix
        self.tenant_id = tenant_id
        self.default_ttl_seconds = default_ttl_seconds

        self._client = redis_client
        if self._client is None:
            try:
                import redis
                self._client = redis.Redis(host=host, port=port, db=db, decode_responses=True)
            except Exception:
                # If redis library or connection is unavailable, client remains None
                self._client = None

        self._reserve_script_content = _read_lua_script("reserve.lua")
        self._reconcile_script_content = _read_lua_script("reconcile.lua")
        self._release_script_content = _read_lua_script("release.lua")

    def _ensure_client(self) -> Any:
        if self._client is None:
            raise BudgetStoreUnavailableError("Redis budget store client is unavailable (Fail Closed).")
        return self._client

    def _get_keys(self, daily_bucket: str, monthly_bucket: str, reservation_id: str) -> List[str]:
        return [
            f"{self.prefix}:{self.tenant_id}:daily_spend:{daily_bucket}",
            f"{self.prefix}:{self.tenant_id}:monthly_spend:{monthly_bucket}",
            f"{self.prefix}:{self.tenant_id}:active_day:{daily_bucket}",
            f"{self.prefix}:{self.tenant_id}:active_month:{monthly_bucket}",
            f"{self.prefix}:{self.tenant_id}:res:{reservation_id}",
        ]

    def ping(self) -> bool:
        """Health probe check."""
        try:
            client = self._ensure_client()
            return bool(client.ping())
        except Exception:
            return False

    def get_daily_spend(self, bucket: str) -> Decimal:
        """Get committed daily spend for a bucket."""
        try:
            client = self._ensure_client()
            key = f"{self.prefix}:{self.tenant_id}:daily_spend:{bucket}"
            val = client.get(key)
            return Decimal(str(val)) if val is not None else Decimal("0.00")
        except BudgetStoreUnavailableError:
            raise
        except Exception as exc:
            raise BudgetStoreUnavailableError(f"Failed to query daily spend from Redis: {exc}") from exc

    def get_monthly_spend(self, bucket: str) -> Decimal:
        """Get committed monthly spend for a bucket."""
        try:
            client = self._ensure_client()
            key = f"{self.prefix}:{self.tenant_id}:monthly_spend:{bucket}"
            val = client.get(key)
            return Decimal(str(val)) if val is not None else Decimal("0.00")
        except BudgetStoreUnavailableError:
            raise
        except Exception as exc:
            raise BudgetStoreUnavailableError(f"Failed to query monthly spend from Redis: {exc}") from exc

    def get_daily_effective_exposure(self, bucket: str) -> Decimal:
        """Get total committed spend plus active and uncertain reservations for a daily bucket."""
        try:
            client = self._ensure_client()
            committed_key = f"{self.prefix}:{self.tenant_id}:daily_spend:{bucket}"
            active_key = f"{self.prefix}:{self.tenant_id}:active_day:{bucket}"

            committed_val = client.get(committed_key)
            committed = Decimal(str(committed_val)) if committed_val is not None else Decimal("0.00")

            active_vals = client.hvals(active_key) or []
            active_sum = sum(Decimal(str(v)) for v in active_vals)
            return committed + active_sum
        except BudgetStoreUnavailableError:
            raise
        except Exception as exc:
            raise BudgetStoreUnavailableError(f"Failed to query daily effective exposure from Redis: {exc}") from exc

    def get_monthly_effective_exposure(self, bucket: str) -> Decimal:
        """Get total committed spend plus active and uncertain reservations for a monthly bucket."""
        try:
            client = self._ensure_client()
            committed_key = f"{self.prefix}:{self.tenant_id}:monthly_spend:{bucket}"
            active_key = f"{self.prefix}:{self.tenant_id}:active_month:{bucket}"

            committed_val = client.get(committed_key)
            committed = Decimal(str(committed_val)) if committed_val is not None else Decimal("0.00")

            active_vals = client.hvals(active_key) or []
            active_sum = sum(Decimal(str(v)) for v in active_vals)
            return committed + active_sum
        except BudgetStoreUnavailableError:
            raise
        except Exception as exc:
            raise BudgetStoreUnavailableError(f"Failed to query monthly effective exposure from Redis: {exc}") from exc

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
        """Atomically test limits and record an ACTIVE reservation using Lua."""
        client = self._ensure_client()
        now = timestamp or utc_now()
        keys = self._get_keys(daily_bucket, monthly_bucket, reservation_id)

        argv = [
            str(estimated_cost),
            str(task_limit) if task_limit is not None else "",
            str(daily_limit) if daily_limit is not None else "",
            str(monthly_limit) if monthly_limit is not None else "",
            reservation_id,
            execution_id,
            now.isoformat(),
            daily_bucket,
            monthly_bucket,
            str(self.default_ttl_seconds),
        ]

        try:
            raw_res = client.eval(self._reserve_script_content, len(keys), *keys, *argv)
            res = json.loads(raw_res) if isinstance(raw_res, str) else raw_res
        except BudgetStoreUnavailableError:
            raise
        except Exception as exc:
            raise BudgetStoreUnavailableError(f"Redis reserve failed (Fail Closed): {exc}") from exc

        if not isinstance(res, dict):
            raise BudgetStoreUnavailableError(f"Unexpected Redis reserve response format: {res}")

        if res.get("status") == "DENIED":
            reason = res.get("reason", "budget_exceeded")
            limit = res.get("limit", 0.0)
            if reason == "max_cost_per_task":
                raise BudgetExhaustedError(
                    f"Estimated cost ${estimated_cost:.4f} exceeds task budget limit of ${limit:.4f}.",
                    details={
                        "estimated_cost": float(estimated_cost),
                        "limit": float(limit),
                        "limit_type": "max_cost_per_task",
                    },
                )
            elif reason == "max_cost_per_day":
                proj = res.get("projected_spend", 0.0)
                spent = res.get("current_spent", 0.0)
                reserved = res.get("active_reserved", 0.0)
                raise BudgetExhaustedError(
                    f"Projected daily spend ${proj:.4f} exceeds daily budget limit of ${limit:.4f}.",
                    details={
                        "projected_spend": float(proj),
                        "current_spent": float(spent),
                        "active_reserved": float(reserved),
                        "estimated_cost": float(estimated_cost),
                        "limit": float(limit),
                        "limit_type": "max_cost_per_day",
                    },
                )
            elif reason == "max_cost_per_month":
                proj = res.get("projected_spend", 0.0)
                spent = res.get("current_spent", 0.0)
                reserved = res.get("active_reserved", 0.0)
                raise BudgetExhaustedError(
                    f"Projected monthly spend ${proj:.4f} exceeds monthly budget limit of ${limit:.4f}.",
                    details={
                        "projected_spend": float(proj),
                        "current_spent": float(spent),
                        "active_reserved": float(reserved),
                        "estimated_cost": float(estimated_cost),
                        "limit": float(limit),
                        "limit_type": "max_cost_per_month",
                    },
                )
            else:
                raise BudgetExhaustedError("Budget limit exceeded.", details=res)

        return BudgetReservationRecord(
            reservation_id=reservation_id,
            execution_id=execution_id,
            estimated_cost=estimated_cost,
            reserved_at=now,
            daily_bucket=daily_bucket,
            monthly_bucket=monthly_bucket,
            status=ReservationStatus.ACTIVE,
        )

    def reconcile(
        self,
        reservation_id: str,
        actual_cost: Decimal,
    ) -> Optional[BudgetReservationRecord]:
        """Atomically transition ACTIVE or UNCERTAIN reservation to RECONCILED with actual cost."""
        client = self._ensure_client()
        res_key = f"{self.prefix}:{self.tenant_id}:res:{reservation_id}"

        try:
            # Read bucket info from existing record to form keys
            raw_record = client.hgetall(res_key)
            if not raw_record:
                return None

            daily_bucket = raw_record.get("daily_bucket", "")
            monthly_bucket = raw_record.get("monthly_bucket", "")

            keys = [
                res_key,
                f"{self.prefix}:{self.tenant_id}:active_day:{daily_bucket}",
                f"{self.prefix}:{self.tenant_id}:active_month:{monthly_bucket}",
                f"{self.prefix}:{self.tenant_id}:daily_spend:{daily_bucket}",
                f"{self.prefix}:{self.tenant_id}:monthly_spend:{monthly_bucket}",
            ]
            argv = [reservation_id, str(actual_cost)]

            raw_res = client.eval(self._reconcile_script_content, len(keys), *keys, *argv)
            res = json.loads(raw_res) if isinstance(raw_res, str) else raw_res
        except BudgetStoreUnavailableError:
            raise
        except Exception as exc:
            raise BudgetStoreUnavailableError(f"Redis reconcile failed: {exc}") from exc

        if not res or res.get("status") == "NOT_FOUND":
            return None

        # Return updated record
        status_val = res.get("current_status") or res.get("status")
        try:
            status_enum = ReservationStatus(status_val) if status_val in ReservationStatus.__members__ else ReservationStatus.RECONCILED
        except Exception:
            status_enum = ReservationStatus.RECONCILED

        res_at = now = utc_now()
        if res.get("reserved_at"):
            try:
                res_at = datetime.fromisoformat(res["reserved_at"])
            except Exception:
                pass

        return BudgetReservationRecord(
            reservation_id=res.get("reservation_id", reservation_id),
            execution_id=res.get("execution_id", ""),
            estimated_cost=Decimal(str(res.get("estimated_cost", "0.00"))),
            actual_cost=Decimal(str(res.get("actual_cost", actual_cost))),
            reserved_at=res_at,
            daily_bucket=res.get("daily_bucket", daily_bucket),
            monthly_bucket=res.get("monthly_bucket", monthly_bucket),
            status=status_enum,
        )

    def release(self, reservation_id: str) -> Optional[BudgetReservationRecord]:
        """Atomically release an ACTIVE reservation on confirmed pre-dispatch failure ($0 spend)."""
        client = self._ensure_client()
        res_key = f"{self.prefix}:{self.tenant_id}:res:{reservation_id}"

        try:
            raw_record = client.hgetall(res_key)
            if not raw_record:
                return None

            daily_bucket = raw_record.get("daily_bucket", "")
            monthly_bucket = raw_record.get("monthly_bucket", "")

            keys = [
                res_key,
                f"{self.prefix}:{self.tenant_id}:active_day:{daily_bucket}",
                f"{self.prefix}:{self.tenant_id}:active_month:{monthly_bucket}",
            ]
            argv = [reservation_id]

            raw_res = client.eval(self._release_script_content, len(keys), *keys, *argv)
            res = json.loads(raw_res) if isinstance(raw_res, str) else raw_res
        except BudgetStoreUnavailableError:
            raise
        except Exception as exc:
            raise BudgetStoreUnavailableError(f"Redis release failed: {exc}") from exc

        if not res or res.get("status") == "NOT_FOUND":
            return None

        status_val = res.get("current_status") or res.get("status")
        try:
            status_enum = ReservationStatus(status_val) if status_val in ReservationStatus.__members__ else ReservationStatus.RELEASED
        except Exception:
            status_enum = ReservationStatus.RELEASED

        res_at = utc_now()
        if res.get("reserved_at"):
            try:
                res_at = datetime.fromisoformat(res["reserved_at"])
            except Exception:
                pass

        return BudgetReservationRecord(
            reservation_id=res.get("reservation_id", reservation_id),
            execution_id=res.get("execution_id", ""),
            estimated_cost=Decimal(str(res.get("estimated_cost", "0.00"))),
            actual_cost=Decimal(str(res.get("actual_cost", "0.00"))),
            reserved_at=res_at,
            daily_bucket=res.get("daily_bucket", daily_bucket),
            monthly_bucket=res.get("monthly_bucket", monthly_bucket),
            status=status_enum,
        )

    def mark_uncertain(
        self,
        reservation_id: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> Optional[BudgetReservationRecord]:
        """Transition reservation to UNCERTAIN upon ambiguous timeout/disconnect, retaining exposure."""
        client = self._ensure_client()
        res_key = f"{self.prefix}:{self.tenant_id}:res:{reservation_id}"

        try:
            raw_record = client.hgetall(res_key)
            if not raw_record:
                return None

            curr_status = raw_record.get("status")
            if curr_status in (ReservationStatus.RECONCILED.value, ReservationStatus.RELEASED.value):
                return self.get_reservation(reservation_id)

            mapping = {"status": ReservationStatus.UNCERTAIN.value}
            if details:
                mapping["uncertain_details"] = json.dumps(details)

            client.hset(res_key, mapping=mapping)
            return self.get_reservation(reservation_id)
        except BudgetStoreUnavailableError:
            raise
        except Exception as exc:
            raise BudgetStoreUnavailableError(f"Redis mark_uncertain failed: {exc}") from exc

    def record_retry_cost(
        self,
        reservation_id: str,
        additional_cost: Decimal,
        task_limit: Optional[Decimal] = None,
    ) -> BudgetReservationRecord:
        """Record additional cost on active reservation for retries."""
        client = self._ensure_client()
        res_key = f"{self.prefix}:{self.tenant_id}:res:{reservation_id}"

        try:
            raw_record = client.hgetall(res_key)
            if not raw_record:
                raise KeyError(f"Reservation '{reservation_id}' not found.")

            curr_est = Decimal(str(raw_record.get("estimated_cost", "0.00")))
            new_est = curr_est + additional_cost
            if task_limit is not None and new_est > task_limit:
                raise BudgetExhaustedError(
                    f"Cumulative retry/fallback cost ${new_est:.4f} exceeds task budget limit of ${task_limit:.4f}.",
                    details={"cumulative_cost": float(new_est), "limit": float(task_limit)},
                )

            daily_bucket = raw_record.get("daily_bucket", "")
            monthly_bucket = raw_record.get("monthly_bucket", "")

            client.hset(res_key, "estimated_cost", str(new_est))
            if daily_bucket:
                client.hset(f"{self.prefix}:{self.tenant_id}:active_day:{daily_bucket}", reservation_id, str(new_est))
            if monthly_bucket:
                client.hset(f"{self.prefix}:{self.tenant_id}:active_month:{monthly_bucket}", reservation_id, str(new_est))

            record = self.get_reservation(reservation_id)
            if not record:
                raise KeyError(f"Reservation '{reservation_id}' not found.")
            return record
        except (BudgetExhaustedError, KeyError, BudgetStoreUnavailableError):
            raise
        except Exception as exc:
            raise BudgetStoreUnavailableError(f"Redis record_retry_cost failed: {exc}") from exc

    def get_reservation(self, reservation_id: str) -> Optional[BudgetReservationRecord]:
        """Retrieve reservation record by identifier."""
        try:
            client = self._ensure_client()
            res_key = f"{self.prefix}:{self.tenant_id}:res:{reservation_id}"
            raw = client.hgetall(res_key)
            if not raw:
                return None

            status_str = raw.get("status", "ACTIVE")
            try:
                status_enum = ReservationStatus(status_str)
            except Exception:
                status_enum = ReservationStatus.ACTIVE

            res_at = utc_now()
            if raw.get("reserved_at"):
                try:
                    res_at = datetime.fromisoformat(raw["reserved_at"])
                except Exception:
                    pass

            meta: Dict[str, Any] = {}
            if raw.get("uncertain_details"):
                try:
                    meta["uncertain_details"] = json.loads(raw["uncertain_details"])
                except Exception:
                    pass

            return BudgetReservationRecord(
                reservation_id=raw.get("reservation_id", reservation_id),
                execution_id=raw.get("execution_id", ""),
                estimated_cost=Decimal(str(raw.get("estimated_cost", "0.00"))),
                actual_cost=Decimal(str(raw.get("actual_cost", "0.00"))),
                reserved_at=res_at,
                daily_bucket=raw.get("daily_bucket", ""),
                monthly_bucket=raw.get("monthly_bucket", ""),
                status=status_enum,
                metadata=meta,
            )
        except BudgetStoreUnavailableError:
            raise
        except Exception as exc:
            raise BudgetStoreUnavailableError(f"Redis get_reservation failed: {exc}") from exc

    def clear(self) -> None:
        """Clear keys belonging to this tenant (for test isolation)."""
        try:
            client = self._ensure_client()
            match_pattern = f"{self.prefix}:{self.tenant_id}:*"
            keys = client.keys(match_pattern)
            if keys:
                client.delete(*keys)
        except Exception:
            pass
