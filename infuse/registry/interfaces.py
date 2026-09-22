"""Provider & Model Registry interface definitions."""

from abc import ABC, abstractmethod
from typing import List, Optional

from infuse.registry.models import (
    ModelRecord,
    ProviderRecord,
    RegistryLifecycleStatus,
    RegistrySummary,
)


class IProviderModelRegistry(ABC):
    """Abstract catalog repository interface for managing providers and models."""

    @abstractmethod
    def register_provider(self, provider: ProviderRecord) -> ProviderRecord:
        """Register a new provider record."""
        raise NotImplementedError

    @abstractmethod
    def get_provider(self, provider_id: str) -> Optional[ProviderRecord]:
        """Retrieve a provider record by provider_id."""
        raise NotImplementedError

    @abstractmethod
    def list_providers(
        self,
        status: Optional[RegistryLifecycleStatus] = None
    ) -> List[ProviderRecord]:
        """List registered providers, optionally filtered by lifecycle status."""
        raise NotImplementedError

    @abstractmethod
    def update_provider(self, provider: ProviderRecord) -> ProviderRecord:
        """Update an existing provider record."""
        raise NotImplementedError

    @abstractmethod
    def delete_provider(self, provider_id: str) -> bool:
        """Remove a provider record and its associated models."""
        raise NotImplementedError

    @abstractmethod
    def register_model(self, model: ModelRecord) -> ModelRecord:
        """Register a new model record under a provider."""
        raise NotImplementedError

    @abstractmethod
    def get_model(
        self,
        model_id: str,
        provider_id: Optional[str] = None
    ) -> Optional[ModelRecord]:
        """Retrieve a model by model_id, optionally qualified by provider_id."""
        raise NotImplementedError

    @abstractmethod
    def list_models(
        self,
        status: Optional[RegistryLifecycleStatus] = None
    ) -> List[ModelRecord]:
        """List all registered models across providers, optionally filtered by status."""
        raise NotImplementedError

    @abstractmethod
    def list_models_for_provider(
        self,
        provider_id: str,
        status: Optional[RegistryLifecycleStatus] = None
    ) -> List[ModelRecord]:
        """List all models registered under a specific provider."""
        raise NotImplementedError

    @abstractmethod
    def update_model(self, model: ModelRecord) -> ModelRecord:
        """Update an existing model record."""
        raise NotImplementedError

    @abstractmethod
    def delete_model(
        self,
        model_id: str,
        provider_id: Optional[str] = None
    ) -> bool:
        """Delete a model record from the catalog."""
        raise NotImplementedError

    @abstractmethod
    def get_summary(self) -> RegistrySummary:
        """Return aggregate summary metrics for the registry."""
        raise NotImplementedError
