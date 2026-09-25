"""Central Integration Registry for managing third-party components in Block 31."""

import os
from typing import Any, Dict, List, Optional

from infuse.integrations.contracts import (
    IntegrationCategory,
    IntegrationComponentInfo,
    IntegrationStatus,
    IntegrationTelemetry,
    VerificationStatus,
)
from infuse.integrations.manifest import ReuseManifest, load_manifest, validate_manifest


class IntegrationRegistry:
    """Central registry and health tracker for third-party integrations."""

    def __init__(self, manifest: Optional[ReuseManifest] = None):
        self._manifest = manifest or self._safe_load_manifest()
        self._telemetry: Dict[str, IntegrationTelemetry] = {}
        self._custom_components: Dict[str, IntegrationComponentInfo] = {}
        self._init_telemetry()

    def _safe_load_manifest(self) -> ReuseManifest:
        try:
            return load_manifest()
        except Exception:
            return ReuseManifest(
                schema_version="1.0.0",
                project="INFUSE",
                manifest_rules=[],
                components=[],
            )

    def _init_telemetry(self) -> None:
        for comp in self.list_components():
            status = self._evaluate_initial_status(comp)
            self._telemetry[comp.name] = IntegrationTelemetry(
                component_name=comp.name,
                status=status,
                invocations_count=0,
                errors_count=0,
            )

    def _evaluate_initial_status(self, comp: IntegrationComponentInfo) -> IntegrationStatus:
        # Check environment override
        env_disabled = os.environ.get(f"INFUSE_INTEGRATION_{comp.name.upper().replace('-', '_').replace('/', '_')}_ENABLED", "true").lower() in ("false", "0", "no")
        if env_disabled:
            return IntegrationStatus.DISABLED

        if comp.integration_type == IntegrationCategory.ADAPTER_INTEGRATION:
            if comp.name == "litellm":
                from infuse.integrations.litellm.adapter import _LITELLM_AVAILABLE
                return IntegrationStatus.OPTIONAL_AVAILABLE if _LITELLM_AVAILABLE else IntegrationStatus.OPTIONAL_UNAVAILABLE
            return IntegrationStatus.ACTIVE
        elif comp.integration_type in (
            IntegrationCategory.REIMPLEMENTED_CLEAN_ROOM,
            IntegrationCategory.DIRECT_DEPENDENCY,
        ):
            return IntegrationStatus.ACTIVE
        elif comp.integration_type == IntegrationCategory.REFERENCE_ONLY:
            return IntegrationStatus.ACTIVE
        elif comp.integration_type == IntegrationCategory.SEPARATE_SERVICE:
            return IntegrationStatus.OPTIONAL_AVAILABLE

        return IntegrationStatus.ACTIVE

    def list_components(self) -> List[IntegrationComponentInfo]:
        """Return all evaluated components recorded in the manifest or added dynamically."""
        comps = list(self._manifest.components)
        for custom in self._custom_components.values():
            if not any(c.name == custom.name for c in comps):
                comps.append(custom)
        return comps

    def get_component(self, name: str) -> Optional[IntegrationComponentInfo]:
        """Look up component details by canonical name."""
        for comp in self.list_components():
            if comp.name.lower() == name.lower():
                return comp
        return None

    def get_status(self, name: str) -> IntegrationStatus:
        """Get live runtime status of an integration."""
        if name in self._telemetry:
            return self._telemetry[name].status
        comp = self.get_component(name)
        if comp:
            return self._evaluate_initial_status(comp)
        return IntegrationStatus.OPTIONAL_UNAVAILABLE

    def record_invocation(self, name: str, success: bool = True, error: Optional[str] = None) -> None:
        """Update operational invocation telemetry for an integration."""
        if name not in self._telemetry:
            self._telemetry[name] = IntegrationTelemetry(
                component_name=name,
                status=IntegrationStatus.ACTIVE,
            )
        telem = self._telemetry[name]
        telem.invocations_count += 1
        if not success:
            telem.errors_count += 1
            telem.last_error = error

    def get_telemetry(self, name: Optional[str] = None) -> Dict[str, Any]:
        """Retrieve telemetry reports for all integrations or a single component."""
        if name:
            telem = self._telemetry.get(name)
            return telem.model_dump() if telem else {}
        return {k: v.model_dump() for k, v in self._telemetry.items()}

    def validate_manifest_integrity(self) -> List[str]:
        """Validate integrity and rules for all registered components."""
        return validate_manifest(self._manifest)


__all__ = ["IntegrationRegistry"]
