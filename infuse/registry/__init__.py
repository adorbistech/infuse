"""INFUSE Provider & Model Registry Package."""

from infuse.registry.defaults import get_default_catalog_records
from infuse.registry.errors import (
    DuplicateModelError,
    DuplicateProviderError,
    ModelNotFoundError,
    ProviderNotFoundError,
    RegistryError,
    RegistryValidationError,
    SecretDetectedError,
)
from infuse.registry.interfaces import IProviderModelRegistry
from infuse.registry.models import (
    ModelCapabilityDeclaration,
    ModelModality,
    ModelRecord,
    ProviderCapabilityDeclaration,
    ProviderRecord,
    RegistryLifecycleStatus,
    RegistrySummary,
)
from infuse.registry.normalization import (
    normalize_model_record,
    normalize_provider_record,
)
from infuse.registry.repository import InMemoryProviderModelRegistry
from infuse.registry.service import ProviderModelService
from infuse.registry.validation import (
    validate_model_record,
    validate_provider_record,
)

__all__ = [
    "RegistryLifecycleStatus",
    "ModelModality",
    "ModelCapabilityDeclaration",
    "ProviderCapabilityDeclaration",
    "ProviderRecord",
    "ModelRecord",
    "RegistrySummary",
    "IProviderModelRegistry",
    "InMemoryProviderModelRegistry",
    "ProviderModelService",
    "get_default_catalog_records",
    "validate_provider_record",
    "validate_model_record",
    "normalize_provider_record",
    "normalize_model_record",
    "RegistryError",
    "RegistryValidationError",
    "SecretDetectedError",
    "ProviderNotFoundError",
    "ModelNotFoundError",
    "DuplicateProviderError",
    "DuplicateModelError",
]
