"""In-memory provider adapter registry implementation."""

from typing import Dict, List

from infuse.providers.errors import AdapterNotFoundError, DuplicateAdapterError
from infuse.providers.interfaces import IProviderAdapter, IProviderAdapterRegistry


class InMemoryProviderAdapterRegistry(IProviderAdapterRegistry):
    """Thread-safe in-memory registry for provider adapter instances."""

    def __init__(self) -> None:
        self._adapters: Dict[str, IProviderAdapter] = {}

    def register(self, adapter: IProviderAdapter, overwrite: bool = False) -> None:
        """Register a provider adapter."""
        if not adapter or not adapter.provider_id:
            raise ValueError("Adapter must be provided and have a valid provider_id.")

        pid = adapter.provider_id.strip().lower()
        if pid in self._adapters and not overwrite:
            raise DuplicateAdapterError(pid)

        self._adapters[pid] = adapter

    def get(self, provider_id: str) -> IProviderAdapter:
        """Retrieve registered adapter for provider_id."""
        if not provider_id:
            raise AdapterNotFoundError("")

        pid = provider_id.strip().lower()
        if pid not in self._adapters:
            raise AdapterNotFoundError(pid)

        return self._adapters[pid]

    def has(self, provider_id: str) -> bool:
        """Check if adapter is registered for provider_id."""
        if not provider_id:
            return False
        return provider_id.strip().lower() in self._adapters

    def list_providers(self) -> List[str]:
        """List all registered provider IDs in deterministic sorted order."""
        return sorted(self._adapters.keys())

    def list_adapters(self) -> List[IProviderAdapter]:
        """List all registered provider adapter instances."""
        return [self._adapters[k] for k in sorted(self._adapters.keys())]

    def unregister(self, provider_id: str) -> bool:
        """Unregister adapter for provider_id. Returns True if removed."""
        if not provider_id:
            return False
        pid = provider_id.strip().lower()
        if pid in self._adapters:
            del self._adapters[pid]
            return True
        return False
