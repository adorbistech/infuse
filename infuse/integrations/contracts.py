"""Integration contract taxonomy and models for Block 31."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import Field

from infuse.contracts.common import InfuseBaseModel, utc_now


class IntegrationCategory(str, Enum):
    """Categorical classification of third-party open-source components."""
    DIRECT_DEPENDENCY = "DIRECT_DEPENDENCY"
    ADAPTER_INTEGRATION = "ADAPTER_INTEGRATION"
    REFERENCE_ONLY = "REFERENCE_ONLY"
    SEPARATE_SERVICE = "SEPARATE_SERVICE"
    REIMPLEMENTED_CLEAN_ROOM = "REIMPLEMENTED_CLEAN_ROOM"


class VerificationStatus(str, Enum):
    """Due diligence provenance verification status."""
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    REJECTED = "REJECTED"
    DEFERRED = "DEFERRED"


class IntegrationStatus(str, Enum):
    """Runtime availability and operational status of an integration."""
    ACTIVE = "ACTIVE"
    OPTIONAL_AVAILABLE = "OPTIONAL_AVAILABLE"
    OPTIONAL_UNAVAILABLE = "OPTIONAL_UNAVAILABLE"
    DISABLED = "DISABLED"


class IntegrationComponentInfo(InfuseBaseModel):
    """Structured representation of an evaluated third-party component."""
    name: str = Field(..., description="Canonical component identifier.")
    repository: str = Field(..., description="Upstream repository URL.")
    version: str = Field(..., description="Exact pinned version or tag.")
    commit_sha: str = Field(..., description="Exact verified commit SHA.")
    license: str = Field(..., description="SPDX or OSI license identifier.")
    intended_purpose: str = Field(..., description="Intended architectural role.")
    integration_type: IntegrationCategory = Field(..., description="Classification category.")
    dependency_status: str = Field(default="NONE", description="Dependency status (e.g. OPTIONAL, DIRECT, NONE).")
    source_copied: bool = Field(default=False, description="Whether any upstream source was copied.")
    source_adapted: bool = Field(default=False, description="Whether code patterns were adapted.")
    clean_room_implementation: bool = Field(default=True, description="Whether implementation is clean-room.")
    separately_deployed: bool = Field(default=False, description="Whether component is a standalone service.")
    infuse_boundary: str = Field(..., description="INFUSE interface or boundary.")
    affected_blocks: List[str] = Field(default_factory=list, description="List of affected INFUSE blocks.")
    runtime_dependency: bool = Field(default=False, description="Whether it is a mandatory runtime dependency.")
    security_considerations: List[str] = Field(default_factory=list, description="Security review findings.")
    license_notes: str = Field(default="", description="License due diligence notes.")
    removal_strategy: str = Field(default="", description="Strategy for safe isolation/removal.")
    verification_status: VerificationStatus = Field(default=VerificationStatus.VERIFIED, description="Verification status.")
    verification_source: str = Field(default="", description="Upstream Git resolution provenance source.")


class IntegrationTelemetry(InfuseBaseModel):
    """Telemetry and operational health for an integrated component."""
    component_name: str
    status: IntegrationStatus
    invocations_count: int = Field(default=0, ge=0)
    errors_count: int = Field(default=0, ge=0)
    last_invoked_at: Optional[str] = None
    last_error: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


__all__ = [
    "IntegrationCategory",
    "VerificationStatus",
    "IntegrationStatus",
    "IntegrationComponentInfo",
    "IntegrationTelemetry",
]
