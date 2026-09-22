"""Provider & Model Registry service boundary."""

from typing import List, Optional

from infuse.registry.defaults import get_default_catalog_records
from infuse.registry.interfaces import IProviderModelRegistry
from infuse.registry.models import (
    ModelRecord,
    ProviderRecord,
    RegistryLifecycleStatus,
    RegistrySummary,
)
from infuse.registry.repository import InMemoryProviderModelRegistry


class ProviderModelService:
    """Service providing neutral discovery and metadata operations on the registry."""

    def __init__(
        self,
        repository: Optional[IProviderModelRegistry] = None,
        seed_defaults: bool = False
    ) -> None:
        self.repository = repository or InMemoryProviderModelRegistry()
        if seed_defaults:
            self._seed_defaults()

    def _seed_defaults(self) -> None:
        """Seed registry with standard reference catalog data."""
        providers, models = get_default_catalog_records()
        for p in providers:
            if not self.repository.get_provider(p.provider_id):
                self.repository.register_provider(p)
        for m in models:
            if not self.repository.get_model(m.model_id, m.provider_id):
                self.repository.register_model(m)

    def register_provider(self, provider: ProviderRecord) -> ProviderRecord:
        """Register a provider record."""
        return self.repository.register_provider(provider)

    def get_provider(self, provider_id: str) -> Optional[ProviderRecord]:
        """Get provider by identifier."""
        return self.repository.get_provider(provider_id)

    def list_providers(
        self,
        status: Optional[RegistryLifecycleStatus] = None
    ) -> List[ProviderRecord]:
        """List all providers."""
        return self.repository.list_providers(status=status)

    def update_provider(self, provider: ProviderRecord) -> ProviderRecord:
        """Update provider record."""
        return self.repository.update_provider(provider)

    def delete_provider(self, provider_id: str) -> bool:
        """Delete provider and associated models."""
        return self.repository.delete_provider(provider_id)

    def register_model(self, model: ModelRecord) -> ModelRecord:
        """Register a model record."""
        return self.repository.register_model(model)

    def get_model(
        self,
        model_id: str,
        provider_id: Optional[str] = None
    ) -> Optional[ModelRecord]:
        """Get model by identifier."""
        return self.repository.get_model(model_id=model_id, provider_id=provider_id)

    def list_models(
        self,
        status: Optional[RegistryLifecycleStatus] = None
    ) -> List[ModelRecord]:
        """List all models."""
        return self.repository.list_models(status=status)

    def list_models_for_provider(
        self,
        provider_id: str,
        status: Optional[RegistryLifecycleStatus] = None
    ) -> List[ModelRecord]:
        """List models registered under a provider."""
        return self.repository.list_models_for_provider(provider_id=provider_id, status=status)

    def update_model(self, model: ModelRecord) -> ModelRecord:
        """Update model record."""
        return self.repository.update_model(model)

    def delete_model(
        self,
        model_id: str,
        provider_id: Optional[str] = None
    ) -> bool:
        """Delete a model record."""
        return self.repository.delete_model(model_id=model_id, provider_id=provider_id)

    def get_summary(self) -> RegistrySummary:
        """Get catalog aggregate counts."""
        return self.repository.get_summary()
