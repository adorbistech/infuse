"""Abstract interfaces for the INFUSE Provider Adapter Layer."""

from abc import ABC, abstractmethod
from typing import Any, Iterator, List, Optional

from infuse.contracts.capabilities import ProviderCapability
from infuse.providers.models import (
    ProviderErrorRecord,
    ProviderExecutionChunk,
    ProviderExecutionRequest,
    ProviderExecutionResponse,
)


class IProviderAdapter(ABC):
    """Universal contract for AI provider adapters."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Normalized identifier of the provider (e.g. 'openai', 'anthropic', 'google', 'mock')."""
        pass

    @abstractmethod
    def get_capability(self) -> ProviderCapability:
        """Expose declared capabilities of this provider adapter."""
        pass

    @abstractmethod
    def list_models(self) -> List[str]:
        """List model IDs supported by this adapter."""
        pass

    @abstractmethod
    def supports_model(self, model_id: str) -> bool:
        """Check whether this adapter can execute the specified model ID."""
        pass

    @abstractmethod
    def execute(self, request: ProviderExecutionRequest) -> ProviderExecutionResponse:
        """Execute a normalized request and return a normalized response."""
        pass

    @abstractmethod
    def stream(self, request: ProviderExecutionRequest) -> Iterator[ProviderExecutionChunk]:
        """Stream normalized chunk deltas for the given execution request."""
        pass

    @abstractmethod
    def normalize_error(self, raw_error: Any, model_id: Optional[str] = None) -> ProviderErrorRecord:
        """Translate provider-specific errors/exceptions into normalized ProviderErrorRecord."""
        pass


class IProviderAdapterRegistry(ABC):
    """Interface for managing provider adapter instances."""

    @abstractmethod
    def register(self, adapter: IProviderAdapter, overwrite: bool = False) -> None:
        """Register an adapter for a provider."""
        pass

    @abstractmethod
    def get(self, provider_id: str) -> IProviderAdapter:
        """Retrieve the registered adapter for the given provider ID."""
        pass

    @abstractmethod
    def has(self, provider_id: str) -> bool:
        """Check whether an adapter is registered for the provider ID."""
        pass

    @abstractmethod
    def list_providers(self) -> List[str]:
        """Return list of all registered provider IDs."""
        pass

    @abstractmethod
    def list_adapters(self) -> List[IProviderAdapter]:
        """Return list of all registered adapter instances."""
        pass

    @abstractmethod
    def unregister(self, provider_id: str) -> bool:
        """Unregister an adapter by provider ID. Return True if removed, False otherwise."""
        pass
