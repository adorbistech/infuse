"""INFUSE Health Layer (Block 17: Health Engine)."""

from infuse.health.classifier import classify_error_category
from infuse.health.engine import HealthEngine
from infuse.health.errors import (
    HealthError,
    HealthObservationError,
    InvalidEventError,
)
from infuse.health.interfaces import IHealthEngine
from infuse.health.models import (
    ErrorCategory,
    ExecutionHealthSummary,
    HealthCompleteness,
    ModelHealthAggregate,
    ObservedErrorRecord,
    ObservedRetryRecord,
    ProviderHealthAggregate,
)

__all__ = [
    "HealthError",
    "HealthObservationError",
    "InvalidEventError",
    "ErrorCategory",
    "HealthCompleteness",
    "ObservedErrorRecord",
    "ObservedRetryRecord",
    "ExecutionHealthSummary",
    "ProviderHealthAggregate",
    "ModelHealthAggregate",
    "IHealthEngine",
    "HealthEngine",
    "classify_error_category",
]
