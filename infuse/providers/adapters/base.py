"""Base provider adapter implementation."""

from typing import Any, Iterator, List, Optional

from infuse.contracts.capabilities import ProviderCapability
from infuse.providers.errors import UnsupportedModelError
from infuse.providers.interfaces import IProviderAdapter
from infuse.providers.models import (
    ProviderErrorRecord,
    ProviderExecutionChunk,
    ProviderExecutionRequest,
    ProviderExecutionResponse,
)


class BaseProviderAdapter(IProviderAdapter):
    """Abstract base class providing common capability and validation utilities."""

    def __init__(
        self,
        provider_id: str,
        supported_models: Optional[List[str]] = None,
        capability: Optional[ProviderCapability] = None
    ) -> None:
        self._provider_id = provider_id.strip().lower()
        self._supported_models = [m.strip() for m in (supported_models or [])]
        self._capability = capability or ProviderCapability(
            provider_name=self._provider_id,
            supported_models=self._supported_models,
            supports_streaming=True,
            supports_tool_calling=True
        )

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def get_capability(self) -> ProviderCapability:
        return self._capability

    def list_models(self) -> List[str]:
        return list(self._supported_models)

    def supports_model(self, model_id: str) -> bool:
        if not model_id:
            return False
        # If no explicit list provided, consider open; otherwise check membership
        if not self._supported_models:
            return True
        return model_id.strip().lower() in [m.lower() for m in self._supported_models]

    def _validate_request(self, request: ProviderExecutionRequest) -> None:
        if not request:
            raise ValueError("Execution request cannot be None.")
        if request.provider_id.strip().lower() != self._provider_id:
            raise ValueError(
                f"Provider mismatch: Adapter '{self._provider_id}' received request for '{request.provider_id}'."
            )
        if not self.supports_model(request.model_id):
            raise UnsupportedModelError(self._provider_id, request.model_id)

    def execute(self, request: ProviderExecutionRequest) -> ProviderExecutionResponse:
        raise NotImplementedError("Subclasses must implement execute().")

    def stream(self, request: ProviderExecutionRequest) -> Iterator[ProviderExecutionChunk]:
        raise NotImplementedError("Subclasses must implement stream().")

    def normalize_error(self, raw_error: Any, model_id: Optional[str] = None) -> ProviderErrorRecord:
        if isinstance(raw_error, ProviderErrorRecord):
            return raw_error

        msg = str(raw_error)
        http_status = getattr(raw_error, "status_code", None) or getattr(raw_error, "http_status", None)
        error_code = getattr(raw_error, "code", None) or getattr(raw_error, "error_code", None)
        is_retryable = http_status in (429, 500, 502, 503, 504) if http_status else False

        return ProviderErrorRecord(
            provider_id=self._provider_id,
            model_id=model_id,
            error_type="PROVIDER_ERROR",
            error_code=str(error_code) if error_code else None,
            message=msg,
            is_retryable=is_retryable,
            http_status=http_status,
            raw_error={"error_str": str(raw_error)} if not isinstance(raw_error, dict) else raw_error
        )
