"""Deterministic Router implementation for selecting and ordering execution targets."""

from typing import List, Optional, Tuple

from infuse.classifier.models import ComplexityLevel, WorkloadClassification
from infuse.context.models import ExecutionContextRecord
from infuse.resolver.models import CandidateTarget, CapabilityResolutionResult
from infuse.router.errors import NoCompatibleTargetsError
from infuse.router.interfaces import IRouter
from infuse.router.models import (
    RouteDecision,
    RouteTarget,
    RoutingEvidence,
    RoutingStrategy,
)
from infuse.version import SCHEMA_VERSION


class DeterministicRouter(IRouter):
    """Deterministic, policy-aware router for selecting primary and fallback execution targets."""

    def route(
        self,
        context: ExecutionContextRecord,
        resolution: CapabilityResolutionResult,
        classification: Optional[WorkloadClassification] = None,
        strategy: Optional[RoutingStrategy] = None
    ) -> RouteDecision:
        if not resolution.compatible_targets:
            raise NoCompatibleTargetsError(
                f"No compatible execution targets available for execution '{context.execution_id}'."
            )

        # 1. Determine active routing strategy
        active_strategy = self._determine_strategy(context, strategy)

        # 2. Extract preferences from resolution requirements
        pref_models = [m.lower().strip() for m in resolution.requirements.preferred_models if m and m.strip()]
        pref_providers = [p.lower().strip() for p in resolution.requirements.preferred_providers if p and p.strip()]

        # 3. Sort candidates deterministically according to strategy
        sorted_candidates = self._sort_candidates(
            candidates=resolution.compatible_targets,
            strategy=active_strategy,
            pref_models=pref_models,
            pref_providers=pref_providers,
            classification=classification
        )

        primary = sorted_candidates[0]
        fallbacks = sorted_candidates[1:]

        # 4. Construct target records
        selected_target = self._to_route_target(primary)
        fallback_targets = [self._to_route_target(f) for f in fallbacks]

        # 5. Build decision evidence
        is_pref_model = primary.model_id.lower() in pref_models
        is_pref_provider = primary.provider_id.lower() in pref_providers
        pref_matched = is_pref_model or is_pref_provider

        reason = self._generate_selection_reason(
            primary=primary,
            strategy=active_strategy,
            pref_matched=pref_matched,
            total_compatible=len(resolution.compatible_targets)
        )

        evidence = RoutingEvidence(
            candidates_evaluated_count=len(resolution.compatible_targets),
            strategy_used=active_strategy,
            preference_matched=pref_matched,
            selection_reason=reason,
            candidate_pool=[
                {"provider_id": c.provider_id, "model_id": c.model_id}
                for c in resolution.compatible_targets
            ],
            tie_breaker_applied=len(resolution.compatible_targets) > 1 and not pref_matched,
            details={
                "preferred_models": pref_models,
                "preferred_providers": pref_providers,
                "primary_provider_id": primary.provider_id,
                "primary_model_id": primary.model_id,
                "fallbacks_count": len(fallbacks)
            }
        )

        return RouteDecision(
            execution_id=context.execution_id,
            selected_target=selected_target,
            fallback_targets=fallback_targets,
            strategy_used=active_strategy,
            evidence=evidence,
            schema_version=SCHEMA_VERSION
        )

    def _determine_strategy(
        self,
        context: ExecutionContextRecord,
        explicit_strategy: Optional[RoutingStrategy]
    ) -> RoutingStrategy:
        if explicit_strategy is not None:
            return explicit_strategy

        custom_strat = (
            context.constraints.metadata.get("routing_strategy")
            if context.constraints and context.constraints.metadata
            else None
        )
        if custom_strat:
            try:
                return RoutingStrategy(str(custom_strat).lower().strip())
            except ValueError:
                pass

        if context.constraints and (context.constraints.preferred_models or context.constraints.preferred_providers):
            return RoutingStrategy.PREFERENCE

        return RoutingStrategy.BALANCED

    def _sort_candidates(
        self,
        candidates: List[CandidateTarget],
        strategy: RoutingStrategy,
        pref_models: List[str],
        pref_providers: List[str],
        classification: Optional[WorkloadClassification]
    ) -> List[CandidateTarget]:
        def sort_key(c: CandidateTarget) -> Tuple:
            m_id = c.model_id.lower()
            p_id = c.provider_id.lower()

            # Preference ranks (lower is better; index 0 is first choice)
            model_pref_rank = pref_models.index(m_id) if m_id in pref_models else 9999
            prov_pref_rank = pref_providers.index(p_id) if p_id in pref_providers else 9999
            has_pref = (model_pref_rank < 9999) or (prov_pref_rank < 9999)

            decl_caps = [cap.lower() for cap in c.declared_capabilities]
            cap_count = len(decl_caps)
            has_reasoning = "reasoning" in decl_caps or "coder" in decl_caps or "coding" in decl_caps

            if strategy == RoutingStrategy.PREFERENCE:
                return (
                    model_pref_rank,
                    prov_pref_rank,
                    -c.context_window,
                    -cap_count,
                    c.provider_id,
                    c.model_id
                )

            elif strategy == RoutingStrategy.WORKLOAD_FIT:
                # Prioritize reasoning for high complexity / coding workloads
                is_complex = (
                    classification and (
                        classification.complexity_level in (ComplexityLevel.VERY_HIGH, ComplexityLevel.HIGH)
                        or classification.category == WorkloadCategory.CODING
                        or classification.category == WorkloadCategory.REASONING
                    )
                )
                fit_score = 0
                if is_complex and has_reasoning:
                    fit_score -= 10
                return (
                    fit_score,
                    model_pref_rank,
                    prov_pref_rank,
                    -c.context_window,
                    -cap_count,
                    c.provider_id,
                    c.model_id
                )

            elif strategy == RoutingStrategy.LOW_LATENCY:
                has_streaming = "streaming" in decl_caps or "sse" in decl_caps
                # Prefer streaming & compact context
                latency_rank = 0 if has_streaming else 1
                return (
                    latency_rank,
                    model_pref_rank,
                    prov_pref_rank,
                    c.context_window,  # Smaller context capacity often indicates lighter model
                    c.provider_id,
                    c.model_id
                )

            elif strategy == RoutingStrategy.COST_EFFICIENT:
                # Prefer efficiency declarations without calculating prices
                return (
                    model_pref_rank,
                    prov_pref_rank,
                    -cap_count,
                    c.context_window,
                    c.provider_id,
                    c.model_id
                )

            else:  # BALANCED
                return (
                    0 if has_pref else 1,
                    model_pref_rank,
                    prov_pref_rank,
                    -cap_count,
                    -c.context_window,
                    c.provider_id,
                    c.model_id
                )

        return sorted(candidates, key=sort_key)

    def _to_route_target(self, candidate: CandidateTarget) -> RouteTarget:
        return RouteTarget(
            provider_id=candidate.provider_id,
            model_id=candidate.model_id,
            context_window=candidate.context_window,
            max_output_tokens=candidate.max_output_tokens,
            declared_capabilities=candidate.declared_capabilities,
            supported_modalities=candidate.supported_modalities,
            metadata=candidate.metadata
        )

    def _generate_selection_reason(
        self,
        primary: CandidateTarget,
        strategy: RoutingStrategy,
        pref_matched: bool,
        total_compatible: int
    ) -> str:
        if pref_matched:
            return (
                f"Selected '{primary.provider_id}/{primary.model_id}' under {strategy.value} strategy "
                f"matching explicit execution preference among {total_compatible} compatible candidate(s)."
            )
        return (
            f"Selected '{primary.provider_id}/{primary.model_id}' under {strategy.value} strategy "
            f"via deterministic capability and identifier ordering among {total_compatible} compatible candidate(s)."
        )
