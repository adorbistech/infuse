"""Router service boundary."""

from typing import Optional

from infuse.classifier.models import WorkloadClassification
from infuse.context.models import ExecutionContextRecord
from infuse.resolver.models import CapabilityResolutionResult
from infuse.router.interfaces import IRouter
from infuse.router.models import RouteDecision, RoutingStrategy
from infuse.router.router import DeterministicRouter


class RouterService:
    """Service boundary orchestrating deterministic execution route selection."""

    def __init__(self, router: Optional[IRouter] = None) -> None:
        self.router = router or DeterministicRouter()

    def route(
        self,
        context: ExecutionContextRecord,
        resolution: CapabilityResolutionResult,
        classification: Optional[WorkloadClassification] = None,
        strategy: Optional[RoutingStrategy] = None
    ) -> RouteDecision:
        """Execute deterministic routing decision over compatible targets."""
        return self.router.route(
            context=context,
            resolution=resolution,
            classification=classification,
            strategy=strategy
        )
