"""Deterministic Capability Resolver implementation."""

from typing import Any, Dict, List, Optional

from infuse.classifier.models import WorkloadClassification
from infuse.context.models import ExecutionContextRecord
from infuse.registry.interfaces import IProviderModelRegistry
from infuse.registry.models import RegistryLifecycleStatus
from infuse.resolver.interfaces import ICapabilityResolver
from infuse.resolver.models import (
    CandidateTarget,
    CapabilityResolutionResult,
    IncompatibleTarget,
    MismatchReason,
    ResolvedRequirements,
)
from infuse.version import SCHEMA_VERSION


class CapabilityResolver(ICapabilityResolver):
    """Deterministic capability resolver matching workload requirements against registry catalog."""

    def resolve(
        self,
        context: ExecutionContextRecord,
        classification: Optional[WorkloadClassification],
        registry: IProviderModelRegistry
    ) -> CapabilityResolutionResult:
        # 1. Consolidate requirements from Context and Classification
        req = self._extract_requirements(context, classification)

        # 2. Snapshot catalog entities
        all_models = registry.list_models()
        all_providers = {p.provider_id: p for p in registry.list_providers()}

        # 3. Deterministically sort models by (provider_id, model_id)
        sorted_models = sorted(all_models, key=lambda m: (m.provider_id, m.model_id))

        compatible: List[CandidateTarget] = []
        incompatible: List[IncompatibleTarget] = []

        # 4. Evaluate each model against requirements
        for model in sorted_models:
            prov = all_providers.get(model.provider_id)
            mismatches: List[str] = []
            details: Dict[str, Any] = {}

            # Administrative eligibility check
            if prov is None or prov.status != RegistryLifecycleStatus.ACTIVE:
                mismatches.append(MismatchReason.PROVIDER_INELIGIBLE.value)
                details["provider_status"] = (
                    prov.status.value if hasattr(prov.status, "value") else str(prov.status)
                ) if prov else "MISSING"

            if model.status != RegistryLifecycleStatus.ACTIVE:
                mismatches.append(MismatchReason.ADMINISTRATIVELY_INELIGIBLE.value)
                details["model_status"] = (
                    model.status.value if hasattr(model.status, "value") else str(model.status)
                )

            # Provider and Model Exclusions
            if model.provider_id.lower() in req.excluded_providers:
                mismatches.append(MismatchReason.EXCLUDED_PROVIDER.value)
                details["excluded_provider"] = model.provider_id

            if model.model_id.lower() in req.excluded_models:
                mismatches.append(MismatchReason.EXCLUDED_MODEL.value)
                details["excluded_model"] = model.model_id

            # Context Window Capacity
            if req.min_context_tokens > 0 and model.context_window < req.min_context_tokens:
                mismatches.append(MismatchReason.CONTEXT_WINDOW_INSUFFICIENT.value)
                details["context_window_required"] = req.min_context_tokens
                details["context_window_available"] = model.context_window

            # Output Token Capacity
            if req.max_output_tokens_demanded and model.max_output_tokens < req.max_output_tokens_demanded:
                mismatches.append(MismatchReason.MAX_OUTPUT_TOKENS_INSUFFICIENT.value)
                details["max_output_tokens_required"] = req.max_output_tokens_demanded
                details["max_output_tokens_available"] = model.max_output_tokens

            # Tool Calling
            if req.requires_tools:
                has_tools = (
                    model.capabilities.supports_tools
                    or "tools" in [c.lower() for c in model.capabilities.declared_capabilities]
                )
                if not has_tools:
                    mismatches.append(f"{MismatchReason.MISSING_REQUIRED_CAPABILITY.value}:tools")

            # Vision
            if req.requires_vision:
                has_vision = (
                    model.capabilities.supports_vision
                    or "vision" in [c.lower() for c in model.capabilities.declared_capabilities]
                )
                if not has_vision:
                    mismatches.append(f"{MismatchReason.MISSING_REQUIRED_CAPABILITY.value}:vision")

            # Structured Output
            if req.requires_structured_output:
                decl_caps = [c.lower() for c in model.capabilities.declared_capabilities]
                has_struct = (
                    model.capabilities.supports_structured_output
                    or "structured_output" in decl_caps
                    or "json" in decl_caps
                )
                if not has_struct:
                    mismatches.append(f"{MismatchReason.MISSING_REQUIRED_CAPABILITY.value}:structured_output")

            # Web Support
            if req.requires_web:
                decl_caps = [c.lower() for c in model.capabilities.declared_capabilities]
                has_web = "web" in decl_caps or "search" in decl_caps
                if not has_web:
                    mismatches.append(f"{MismatchReason.MISSING_REQUIRED_CAPABILITY.value}:web")

            # Custom Capabilities
            if req.custom_capabilities:
                decl_caps = [c.lower() for c in model.capabilities.declared_capabilities]
                for custom_cap in req.custom_capabilities:
                    if custom_cap.lower() not in decl_caps:
                        mismatches.append(f"{MismatchReason.MISSING_REQUIRED_CAPABILITY.value}:{custom_cap}")

            if len(mismatches) == 0:
                compatible.append(
                    CandidateTarget(
                        provider_id=model.provider_id,
                        model_id=model.model_id,
                        context_window=model.context_window,
                        max_output_tokens=model.max_output_tokens,
                        declared_capabilities=model.capabilities.declared_capabilities,
                        supported_modalities=[
                            m.value if hasattr(m, "value") else str(m)
                            for m in model.capabilities.modalities
                        ],
                        metadata=model.capabilities.metadata
                    )
                )
            else:
                incompatible.append(
                    IncompatibleTarget(
                        provider_id=model.provider_id,
                        model_id=model.model_id,
                        mismatch_reasons=mismatches,
                        details=details
                    )
                )

        return CapabilityResolutionResult(
            requirements=req,
            compatible_targets=compatible,
            incompatible_targets=incompatible,
            total_evaluated=len(sorted_models),
            total_compatible=len(compatible),
            schema_version=SCHEMA_VERSION
        )

    def _extract_requirements(
        self,
        context: ExecutionContextRecord,
        classification: Optional[WorkloadClassification]
    ) -> ResolvedRequirements:
        req_caps = [c.lower().strip() for c in context.constraints.requested_capabilities if c and c.strip()]

        requires_tools = (
            context.constraints.supports_tools
            or context.operation.has_tools
            or context.operation.tool_count > 0
            or "tools" in req_caps
            or "tool_use" in req_caps
            or (classification.dimensions.requires_tools if classification else False)
        )

        requires_vision = (
            context.constraints.supports_vision
            or "vision" in req_caps
            or "multimodal" in req_caps
            or (classification.dimensions.requires_vision if classification else False)
        )

        requires_structured_output = (
            context.constraints.supports_structured_output
            or "structured_output" in req_caps
            or "json" in req_caps
            or (classification.dimensions.requires_structured_output if classification else False)
        )

        requires_web = (
            "web" in req_caps
            or "search" in req_caps
            or (classification.dimensions.requires_web if classification else False)
        )

        requires_streaming = "streaming" in req_caps

        ctx_req_tokens = context.constraints.min_context_tokens or 0
        clf_tokens = classification.dimensions.estimated_context_tokens if classification else 0
        min_context_tokens = max(ctx_req_tokens, clf_tokens)

        excluded_providers = [
            p.lower().strip() for p in context.constraints.excluded_providers if p and p.strip()
        ]
        excluded_models = [
            m.lower().strip() for m in context.constraints.excluded_models if m and m.strip()
        ]
        preferred_providers = [
            p.strip() for p in context.constraints.preferred_providers if p and p.strip()
        ]
        preferred_models = [
            m.strip() for m in context.constraints.preferred_models if m and m.strip()
        ]

        standard_caps = {"tools", "tool_use", "vision", "multimodal", "structured_output", "json", "web", "search", "streaming"}
        custom_capabilities = [c for c in req_caps if c not in standard_caps]

        return ResolvedRequirements(
            requires_tools=requires_tools,
            requires_vision=requires_vision,
            requires_structured_output=requires_structured_output,
            requires_web=requires_web,
            requires_streaming=requires_streaming,
            min_context_tokens=min_context_tokens,
            max_output_tokens_demanded=None,
            excluded_providers=excluded_providers,
            excluded_models=excluded_models,
            preferred_providers=preferred_providers,
            preferred_models=preferred_models,
            custom_capabilities=custom_capabilities
        )
