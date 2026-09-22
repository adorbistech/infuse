"""Capability Resolver service boundary."""

from typing import Optional

from infuse.classifier.models import WorkloadClassification
from infuse.context.models import ExecutionContextRecord
from infuse.registry.interfaces import IProviderModelRegistry
from infuse.registry.repository import InMemoryProviderModelRegistry
from infuse.resolver.interfaces import ICapabilityResolver
from infuse.resolver.models import CapabilityResolutionResult
from infuse.resolver.resolver import CapabilityResolver


class CapabilityResolverService:
    """Service orchestrating capability resolution against provider and model registries."""

    def __init__(
        self,
        resolver: Optional[ICapabilityResolver] = None,
        registry: Optional[IProviderModelRegistry] = None
    ) -> None:
        self.resolver = resolver or CapabilityResolver()
        self.registry = registry or InMemoryProviderModelRegistry()

    def resolve(
        self,
        context: ExecutionContextRecord,
        classification: Optional[WorkloadClassification] = None,
        registry: Optional[IProviderModelRegistry] = None
    ) -> CapabilityResolutionResult:
        """Resolve compatible targets for the given context and classification."""
        active_registry = registry or self.registry
        return self.resolver.resolve(
            context=context,
            classification=classification,
            registry=active_registry
        )
