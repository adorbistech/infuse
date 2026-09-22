"""In-memory, thread-safe implementation of IProviderModelRegistry."""

import threading
from typing import Dict, List, Optional, Tuple

from infuse.registry.errors import (
    DuplicateModelError,
    DuplicateProviderError,
    ModelNotFoundError,
    ProviderNotFoundError,
)
from infuse.registry.interfaces import IProviderModelRegistry
from infuse.registry.models import (
    ModelRecord,
    ProviderRecord,
    RegistryLifecycleStatus,
    RegistrySummary,
)
from infuse.registry.normalization import (
    normalize_model_record,
    normalize_provider_record,
)
from infuse.registry.validation import (
    validate_model_record,
    validate_provider_record,
)
from infuse.version import SCHEMA_VERSION


class InMemoryProviderModelRegistry(IProviderModelRegistry):
    """Thread-safe, persistence-agnostic in-memory catalog for providers and models."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._providers: Dict[str, ProviderRecord] = {}
        # Keyed by (provider_id, model_id)
        self._models: Dict[Tuple[str, str], ModelRecord] = {}

    def register_provider(self, provider: ProviderRecord) -> ProviderRecord:
        """Validate, normalize, and store a new provider record."""
        validate_provider_record(provider)
        normalized = normalize_provider_record(provider)

        with self._lock:
            if normalized.provider_id in self._providers:
                raise DuplicateProviderError(normalized.provider_id)
            self._providers[normalized.provider_id] = normalized.model_copy(deep=True)
            return normalized.model_copy(deep=True)

    def get_provider(self, provider_id: str) -> Optional[ProviderRecord]:
        """Retrieve a deep-copy of the provider record by ID."""
        with self._lock:
            rec = self._providers.get(provider_id.strip())
            return rec.model_copy(deep=True) if rec else None

    def list_providers(
        self,
        status: Optional[RegistryLifecycleStatus] = None
    ) -> List[ProviderRecord]:
        """List registered providers with optional lifecycle status filtering."""
        with self._lock:
            results = []
            for p in self._providers.values():
                if status is None or p.status == status:
                    results.append(p.model_copy(deep=True))
            return sorted(results, key=lambda x: x.provider_id)

    def update_provider(self, provider: ProviderRecord) -> ProviderRecord:
        """Update an existing provider record."""
        validate_provider_record(provider)
        normalized = normalize_provider_record(provider)

        with self._lock:
            if normalized.provider_id not in self._providers:
                raise ProviderNotFoundError(normalized.provider_id)
            self._providers[normalized.provider_id] = normalized.model_copy(deep=True)
            return normalized.model_copy(deep=True)

    def delete_provider(self, provider_id: str) -> bool:
        """Delete a provider record and cascade delete all models belonging to it."""
        prov_id = provider_id.strip()
        with self._lock:
            if prov_id not in self._providers:
                return False
            del self._providers[prov_id]
            # Cascade delete associated models
            keys_to_del = [k for k in self._models.keys() if k[0] == prov_id]
            for k in keys_to_del:
                del self._models[k]
            return True

    def register_model(self, model: ModelRecord) -> ModelRecord:
        """Validate, normalize, and register a model under an existing provider."""
        validate_model_record(model)
        normalized = normalize_model_record(model)

        with self._lock:
            if normalized.provider_id not in self._providers:
                raise ProviderNotFoundError(normalized.provider_id)

            key = (normalized.provider_id, normalized.model_id)
            if key in self._models:
                raise DuplicateModelError(normalized.model_id, normalized.provider_id)

            self._models[key] = normalized.model_copy(deep=True)
            return normalized.model_copy(deep=True)

    def get_model(
        self,
        model_id: str,
        provider_id: Optional[str] = None
    ) -> Optional[ModelRecord]:
        """Retrieve a model by model_id, optionally qualified by provider_id."""
        m_id = model_id.strip()
        with self._lock:
            if provider_id:
                p_id = provider_id.strip()
                rec = self._models.get((p_id, m_id))
                return rec.model_copy(deep=True) if rec else None

            # If provider_id not provided, match first matching model_id
            for (p, m), rec in self._models.items():
                if m == m_id:
                    return rec.model_copy(deep=True)
            return None

    def list_models(
        self,
        status: Optional[RegistryLifecycleStatus] = None
    ) -> List[ModelRecord]:
        """List all models in the catalog, optionally filtered by status."""
        with self._lock:
            results = []
            for m in self._models.values():
                if status is None or m.status == status:
                    results.append(m.model_copy(deep=True))
            return sorted(results, key=lambda x: (x.provider_id, x.model_id))

    def list_models_for_provider(
        self,
        provider_id: str,
        status: Optional[RegistryLifecycleStatus] = None
    ) -> List[ModelRecord]:
        """List all models registered under a specific provider."""
        p_id = provider_id.strip()
        with self._lock:
            if p_id not in self._providers:
                raise ProviderNotFoundError(p_id)

            results = []
            for (p, m), rec in self._models.items():
                if p == p_id and (status is None or rec.status == status):
                    results.append(rec.model_copy(deep=True))
            return sorted(results, key=lambda x: x.model_id)

    def update_model(self, model: ModelRecord) -> ModelRecord:
        """Update an existing model record."""
        validate_model_record(model)
        normalized = normalize_model_record(model)

        with self._lock:
            key = (normalized.provider_id, normalized.model_id)
            if key not in self._models:
                raise ModelNotFoundError(normalized.model_id, normalized.provider_id)
            self._models[key] = normalized.model_copy(deep=True)
            return normalized.model_copy(deep=True)

    def delete_model(
        self,
        model_id: str,
        provider_id: Optional[str] = None
    ) -> bool:
        """Delete a model record from the catalog."""
        m_id = model_id.strip()
        with self._lock:
            if provider_id:
                p_id = provider_id.strip()
                key = (p_id, m_id)
                if key in self._models:
                    del self._models[key]
                    return True
                return False

            # Delete across providers if unqualified
            deleted = False
            keys_to_del = [k for k in self._models.keys() if k[1] == m_id]
            for k in keys_to_del:
                del self._models[k]
                deleted = True
            return deleted

    def get_summary(self) -> RegistrySummary:
        """Compute aggregate summary counts for the registry."""
        with self._lock:
            total_providers = len(self._providers)
            active_providers = sum(
                1 for p in self._providers.values() if p.status == RegistryLifecycleStatus.ACTIVE
            )
            total_models = len(self._models)
            active_models = sum(
                1 for m in self._models.values() if m.status == RegistryLifecycleStatus.ACTIVE
            )
            return RegistrySummary(
                total_providers=total_providers,
                active_providers=active_providers,
                total_models=total_models,
                active_models=active_models,
                schema_version=SCHEMA_VERSION
            )
