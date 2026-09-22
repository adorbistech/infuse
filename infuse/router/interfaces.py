"""Router interface definitions."""

from abc import ABC, abstractmethod
from typing import Optional

from infuse.classifier.models import WorkloadClassification
from infuse.context.models import ExecutionContextRecord
from infuse.resolver.models import CapabilityResolutionResult
from infuse.router.models import RouteDecision, RoutingStrategy


class IRouter(ABC):
    """Abstract interface for deterministic routing decisions across compatible execution targets."""

    @abstractmethod
    def route(
        self,
        context: ExecutionContextRecord,
        resolution: CapabilityResolutionResult,
        classification: Optional[WorkloadClassification] = None,
        strategy: Optional[RoutingStrategy] = None
    ) -> RouteDecision:
        """Select primary and fallback execution targets from compatible candidates.

        Operates only on compatible targets from CapabilityResolutionResult.
        Does NOT invoke providers, measure live health, or calculate pricing.
        """
        raise NotImplementedError
