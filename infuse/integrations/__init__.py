"""INFUSE Third-Party Component Integration Layer (Block 31).

Provides clean boundary isolation, reuse manifest parsing, and adapter interfaces
for external dependencies while maintaining INFUSE core authority.
"""

from infuse.integrations.boundary import IntegrationBoundary
from infuse.integrations.contracts import (
    IntegrationCategory,
    IntegrationComponentInfo,
    IntegrationStatus,
    IntegrationTelemetry,
    VerificationStatus,
)
from infuse.integrations.litellm import LiteLLMProviderAdapter
from infuse.integrations.manifest import ReuseManifest, load_manifest, validate_manifest
from infuse.integrations.registry import IntegrationRegistry

__all__ = [
    "IntegrationBoundary",
    "IntegrationCategory",
    "IntegrationComponentInfo",
    "IntegrationStatus",
    "IntegrationTelemetry",
    "VerificationStatus",
    "LiteLLMProviderAdapter",
    "ReuseManifest",
    "load_manifest",
    "validate_manifest",
    "IntegrationRegistry",
]
