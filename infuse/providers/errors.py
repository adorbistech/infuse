"""Provider Adapter Layer exceptions."""

from typing import Any, Dict, Optional


class ProviderAdapterError(Exception):
    """Base exception for all provider adapter layer failures."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class AdapterNotFoundError(ProviderAdapterError):
    """Raised when an adapter for the specified provider identifier is not registered."""

    def __init__(self, provider_id: str) -> None:
        super().__init__(
            f"No provider adapter registered for provider '{provider_id}'.",
            details={"provider_id": provider_id}
        )
        self.provider_id = provider_id


class DuplicateAdapterError(ProviderAdapterError):
    """Raised when registering an adapter for an already registered provider without overwrite flag."""

    def __init__(self, provider_id: str) -> None:
        super().__init__(
            f"Provider adapter already registered for provider '{provider_id}'.",
            details={"provider_id": provider_id}
        )
        self.provider_id = provider_id


class UnsupportedModelError(ProviderAdapterError):
    """Raised when an adapter is asked to execute a model it does not support."""

    def __init__(self, provider_id: str, model_id: str) -> None:
        super().__init__(
            f"Provider '{provider_id}' does not support model '{model_id}'.",
            details={"provider_id": provider_id, "model_id": model_id}
        )
        self.provider_id = provider_id
        self.model_id = model_id


class InvalidRequestError(ProviderAdapterError):
    """Raised when a request payload is structurally invalid for adapter execution."""
    pass


class ProviderInvocationError(ProviderAdapterError):
    """Raised when a provider execution fails, wrapping normalized error telemetry."""

    def __init__(
        self,
        message: str,
        provider_id: str,
        model_id: Optional[str] = None,
        error_type: str = "PROVIDER_ERROR",
        error_code: Optional[str] = None,
        is_retryable: bool = False,
        http_status: Optional[int] = None,
        provider_request_id: Optional[str] = None,
        raw_error: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(message, details=details)
        self.provider_id = provider_id
        self.model_id = model_id
        self.error_type = error_type
        self.error_code = error_code
        self.is_retryable = is_retryable
        self.http_status = http_status
        self.provider_request_id = provider_request_id
        self.raw_error = raw_error
