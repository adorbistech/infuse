"""INFUSE Web Activity Observation Layer (Block 19)."""

from infuse.web.errors import (
    WebCorrelationError,
    WebObservationError,
    WebObserverError,
)
from infuse.web.interfaces import IWebActivityObserver
from infuse.web.models import (
    ExecutionWebSummary,
    WebActivityRecord,
    WebActivityStatus,
    WebObservationCompleteness,
)
from infuse.web.observer import WebActivityObserver

__all__ = [
    "WebObserverError",
    "WebObservationError",
    "WebCorrelationError",
    "WebActivityStatus",
    "WebObservationCompleteness",
    "WebActivityRecord",
    "ExecutionWebSummary",
    "IWebActivityObserver",
    "WebActivityObserver",
]
