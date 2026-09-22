"""Capability Resolver interface definitions."""

from abc import ABC, abstractmethod
from typing import Optional

from infuse.classifier.models import WorkloadClassification
from infuse.context.models import ExecutionContextRecord
from infuse.registry.interfaces import IProviderModelRegistry
from infuse.resolver.models import CapabilityResolutionResult


class ICapabilityResolver(ABC):
    """Abstract interface for resolving candidate execution targets against workload requirements."""

    @abstractmethod
    def resolve(
        self,
        context: ExecutionContextRecord,
        classification: Optional[WorkloadClassification],
        registry: IProviderModelRegistry
    ) -> CapabilityResolutionResult:
        """Evaluate workload requirements from ExecutionContext and WorkloadClassification against targets in the Registry.

        Returns deterministic compatibility evaluation. Does NOT rank, score, select, or route.
        """
        raise NotImplementedError
