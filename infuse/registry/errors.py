"""Provider & Model Registry exception taxonomy."""

from typing import Any, Dict, List, Optional


class RegistryError(Exception):
    """Base exception for all registry operations."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class RegistryValidationError(RegistryError):
    """Raised when provider or model records fail structural validation."""
    def __init__(self, message: str, violations: Optional[List[str]] = None) -> None:
        super().__init__(message, {"violations": violations or []})
        self.violations = violations or []


class ProviderNotFoundError(RegistryError):
    """Raised when a requested provider is not found in the registry."""
    def __init__(self, provider_id: str) -> None:
        super().__init__(f"Provider '{provider_id}' not found in registry.", {"provider_id": provider_id})
        self.provider_id = provider_id


class ModelNotFoundError(RegistryError):
    """Raised when a requested model is not found in the registry."""
    def __init__(self, model_id: str, provider_id: Optional[str] = None) -> None:
        msg = f"Model '{model_id}'" + (f" for provider '{provider_id}'" if provider_id else "") + " not found in registry."
        super().__init__(msg, {"model_id": model_id, "provider_id": provider_id})
        self.model_id = model_id
        self.provider_id = provider_id


class DuplicateProviderError(RegistryError):
    """Raised when attempting to register a provider with an existing provider_id."""
    def __init__(self, provider_id: str) -> None:
        super().__init__(f"Provider '{provider_id}' already exists in registry.", {"provider_id": provider_id})
        self.provider_id = provider_id


class DuplicateModelError(RegistryError):
    """Raised when attempting to register a duplicate model for a provider."""
    def __init__(self, model_id: str, provider_id: str) -> None:
        super().__init__(f"Model '{model_id}' already exists under provider '{provider_id}'.", {"model_id": model_id, "provider_id": provider_id})
        self.model_id = model_id
        self.provider_id = provider_id


class SecretDetectedError(RegistryValidationError):
    """Raised when credentials, secrets, or API keys are detected in registry metadata."""
    pass
