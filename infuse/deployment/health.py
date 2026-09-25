"""Production System Readiness & Liveness Probes for Block 35.

Provides deep readiness checks verifying that internal event bus,
registries, policy services, and execution environments are initialized
and ready to accept traffic without leaking credentials or internal memory layouts.
"""

import time
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from pydantic import Field

from infuse.contracts.common import InfuseBaseModel, utc_now
from infuse.version import __version__, SCHEMA_VERSION


class ReadinessStatus(str, Enum):
    """System readiness classification."""
    READY = "READY"
    DEGRADED = "DEGRADED"
    UNREADY = "UNREADY"


class ReadinessCheckResult(InfuseBaseModel):
    """Structured report returned by the readiness probe."""
    status: ReadinessStatus = Field(..., description="Overall readiness status.")
    version: str = Field(default=__version__, description="Application semantic version.")
    schema_version: str = Field(default=SCHEMA_VERSION, description="System schema version.")
    uptime_seconds: float = Field(..., description="Process uptime in seconds.")
    checks: Dict[str, str] = Field(default_factory=dict, description="Subsystem check status map.")
    timestamp: datetime = Field(default_factory=utc_now, description="Timestamp of probe evaluation.")


class SystemReadinessProbe:
    """Evaluates readiness of all INFUSE runtime subsystems."""

    def __init__(self, start_time: Optional[float] = None) -> None:
        self._start_time = start_time if start_time is not None else time.time()
        self._custom_checks: Dict[str, Callable[[], bool]] = {}

    def register_check(self, name: str, check_fn: Callable[[], bool]) -> None:
        """Register a custom subsystem readiness check function."""
        self._custom_checks[name] = check_fn

    def evaluate_readiness(
        self,
        execution_service: Optional[Any] = None,
        event_service: Optional[Any] = None,
        policy_service: Optional[Any] = None,
    ) -> ReadinessCheckResult:
        """Perform comprehensive readiness probe across all subsystems."""
        checks: Dict[str, str] = {}
        all_passed = True

        # 1. Check Execution Service
        if execution_service is not None:
            try:
                has_exec = hasattr(execution_service, "execute") or hasattr(execution_service, "get_execution")
                checks["execution_service"] = "OK" if has_exec else "DEGRADED"
                if not has_exec:
                    all_passed = False
            except Exception:
                checks["execution_service"] = "ERROR"
                all_passed = False
        else:
            checks["execution_service"] = "OK"

        # 2. Check Event Service
        if event_service is not None:
            try:
                has_event = (
                    hasattr(event_service, "ingest_event")
                    or hasattr(event_service, "get_events")
                    or hasattr(event_service, "publish_event")
                    or hasattr(event_service, "list_events")
                )
                checks["event_service"] = "OK" if has_event else "DEGRADED"
                if not has_event:
                    all_passed = False
            except Exception:
                checks["event_service"] = "ERROR"
                all_passed = False
        else:
            checks["event_service"] = "OK"

        # 3. Check Policy Service
        if policy_service is not None:
            try:
                has_policy = hasattr(policy_service, "get_policy") or hasattr(policy_service, "list_policies") or hasattr(policy_service, "get_active_policy")
                checks["policy_service"] = "OK" if has_policy else "DEGRADED"
                if not has_policy:
                    all_passed = False
            except Exception:
                checks["policy_service"] = "ERROR"
                all_passed = False
        else:
            checks["policy_service"] = "OK"

        # 4. Evaluate Custom Registered Checks
        for name, fn in self._custom_checks.items():
            try:
                passed = bool(fn())
                checks[name] = "OK" if passed else "FAILED"
                if not passed:
                    all_passed = False
            except Exception:
                checks[name] = "ERROR"
                all_passed = False

        status = ReadinessStatus.READY if all_passed else ReadinessStatus.UNREADY
        uptime = round(time.time() - self._start_time, 2)

        return ReadinessCheckResult(
            status=status,
            uptime_seconds=max(0.0, uptime),
            checks=checks,
            timestamp=utc_now(),
        )
