"""Comprehensive Unit & Architectural Test Suite for Block 10 Capability Resolver."""

import inspect
import sys
import unittest

from infuse.classifier.models import (
    ComplexityLevel,
    IntensityLevel,
    WorkloadCategory,
    WorkloadClassification,
    WorkloadDimensions,
)
from infuse.context.builder import ExecutionContextBuilder
from infuse.registry.defaults import get_default_catalog_records
from infuse.registry.models import (
    ModelCapabilityDeclaration,
    ModelModality,
    ModelRecord,
    ProviderCapabilityDeclaration,
    ProviderRecord,
    RegistryLifecycleStatus,
)
from infuse.registry.repository import InMemoryProviderModelRegistry
from infuse.resolver.interfaces import ICapabilityResolver
from infuse.resolver.models import (
    CandidateTarget,
    CapabilityResolutionResult,
    MismatchReason,
)
from infuse.resolver.resolver import CapabilityResolver
from infuse.resolver.service import CapabilityResolverService
from infuse.version import SCHEMA_VERSION


class TestCapabilityResolver(unittest.TestCase):
    """Test suite verifying capability matching, context checking, exclusions, determinism, and boundaries."""

    def setUp(self) -> None:
        self.registry = InMemoryProviderModelRegistry()
        providers, models = get_default_catalog_records()
        for p in providers:
            self.registry.register_provider(p)
        for m in models:
            self.registry.register_model(m)

        self.resolver = CapabilityResolver()
        self.service = CapabilityResolverService(resolver=self.resolver, registry=self.registry)

    def _build_context(
        self,
        requested_capabilities=None,
        min_context_tokens=None,
        supports_tools=False,
        supports_vision=False,
        supports_structured_output=False,
        excluded_providers=None,
        excluded_models=None,
        preferred_providers=None,
        preferred_models=None
    ):
        builder = ExecutionContextBuilder()
        builder.set_identity(execution_id="exec_res_01", request_id="req_res_01")
        builder.set_task(task_id="task_res_01", workload_hint="coding")
        builder.set_constraints(
            requested_capabilities=requested_capabilities or [],
            min_context_tokens=min_context_tokens,
            supports_tools=supports_tools,
            supports_vision=supports_vision,
            supports_structured_output=supports_structured_output,
            excluded_providers=excluded_providers or [],
            excluded_models=excluded_models or [],
            preferred_providers=preferred_providers or [],
            preferred_models=preferred_models or []
        )
        return builder.build()

    def test_01_empty_requirements_matches_all_active_models(self) -> None:
        """Verify minimal requirements match all active registered models without ranking."""
        ctx = self._build_context()
        result = self.resolver.resolve(ctx, None, self.registry)

        self.assertIsInstance(result, CapabilityResolutionResult)
        self.assertEqual(result.schema_version, SCHEMA_VERSION)
        self.assertEqual(result.total_evaluated, 4)
        self.assertEqual(result.total_compatible, 4)
        self.assertEqual(len(result.compatible_targets), 4)
        self.assertEqual(len(result.incompatible_targets), 0)

    def test_02_required_tools_filters_out_models_without_tools(self) -> None:
        """Verify models lacking tools capability are marked incompatible with explicit reason."""
        # Register a model without tools
        m_no_tools = ModelRecord(
            model_id="gpt-basic",
            provider_id="openai",
            name="GPT Basic No Tools",
            context_window=32000,
            max_output_tokens=2048,
            capabilities=ModelCapabilityDeclaration(supports_tools=False, declared_capabilities=[])
        )
        self.registry.register_model(m_no_tools)

        ctx = self._build_context(supports_tools=True)
        result = self.resolver.resolve(ctx, None, self.registry)

        comp_ids = [t.model_id for t in result.compatible_targets]
        self.assertNotIn("gpt-basic", comp_ids)

        incomp = next((t for t in result.incompatible_targets if t.model_id == "gpt-basic"), None)
        self.assertIsNotNone(incomp)
        self.assertTrue(any("missing_required_capability:tools" in r for r in incomp.mismatch_reasons))

    def test_03_required_vision_filters_text_only_models(self) -> None:
        """Verify vision requirement filters text-only models (like deepseek-v3)."""
        ctx = self._build_context(supports_vision=True)
        result = self.resolver.resolve(ctx, None, self.registry)

        comp_ids = [t.model_id for t in result.compatible_targets]
        self.assertIn("claude-3-7-sonnet", comp_ids)
        self.assertIn("gpt-4o", comp_ids)
        self.assertIn("gemini-2.0-flash", comp_ids)
        self.assertNotIn("deepseek-v3", comp_ids)

        incomp_deepseek = next(t for t in result.incompatible_targets if t.model_id == "deepseek-v3")
        self.assertTrue(any("missing_required_capability:vision" in r for r in incomp_deepseek.mismatch_reasons))

    def test_04_context_window_insufficient_check(self) -> None:
        """Verify models with insufficient context window are rejected with exact token context in details."""
        ctx = self._build_context(min_context_tokens=150000)
        result = self.resolver.resolve(ctx, None, self.registry)

        comp_ids = [t.model_id for t in result.compatible_targets]
        # Only claude-3-7-sonnet (200k) and gemini-2.0-flash (1000k) have >= 150k
        self.assertIn("claude-3-7-sonnet", comp_ids)
        self.assertIn("gemini-2.0-flash", comp_ids)
        self.assertNotIn("gpt-4o", comp_ids)
        self.assertNotIn("deepseek-v3", comp_ids)

        incomp_gpt = next(t for t in result.incompatible_targets if t.model_id == "gpt-4o")
        self.assertIn(MismatchReason.CONTEXT_WINDOW_INSUFFICIENT.value, incomp_gpt.mismatch_reasons)
        self.assertEqual(incomp_gpt.details["context_window_required"], 150000)
        self.assertEqual(incomp_gpt.details["context_window_available"], 128000)

    def test_05_excluded_provider_constraint(self) -> None:
        """Verify models belonging to excluded providers are filtered out."""
        ctx = self._build_context(excluded_providers=["openai", "deepseek"])
        result = self.resolver.resolve(ctx, None, self.registry)

        comp_providers = {t.provider_id for t in result.compatible_targets}
        self.assertNotIn("openai", comp_providers)
        self.assertNotIn("deepseek", comp_providers)
        self.assertIn("anthropic", comp_providers)
        self.assertIn("google", comp_providers)

        incomp_openai = next(t for t in result.incompatible_targets if t.provider_id == "openai")
        self.assertIn(MismatchReason.EXCLUDED_PROVIDER.value, incomp_openai.mismatch_reasons)

    def test_06_excluded_model_constraint(self) -> None:
        """Verify specifically excluded models are filtered out."""
        ctx = self._build_context(excluded_models=["gpt-4o"])
        result = self.resolver.resolve(ctx, None, self.registry)

        comp_ids = [t.model_id for t in result.compatible_targets]
        self.assertNotIn("gpt-4o", comp_ids)

        incomp_gpt = next(t for t in result.incompatible_targets if t.model_id == "gpt-4o")
        self.assertIn(MismatchReason.EXCLUDED_MODEL.value, incomp_gpt.mismatch_reasons)

    def test_07_administrative_status_filtering(self) -> None:
        """Verify disabled or deprecated models/providers are marked administratively ineligible."""
        # Deprecate gpt-4o
        gpt = self.registry.get_model("gpt-4o", "openai")
        gpt.status = RegistryLifecycleStatus.DEPRECATED
        self.registry.update_model(gpt)

        # Disable google provider
        google = self.registry.get_provider("google")
        google.status = RegistryLifecycleStatus.DISABLED
        self.registry.update_provider(google)

        ctx = self._build_context()
        result = self.resolver.resolve(ctx, None, self.registry)

        comp_ids = [t.model_id for t in result.compatible_targets]
        self.assertNotIn("gpt-4o", comp_ids)
        self.assertNotIn("gemini-2.0-flash", comp_ids)

        incomp_gpt = next(t for t in result.incompatible_targets if t.model_id == "gpt-4o")
        self.assertIn(MismatchReason.ADMINISTRATIVELY_INELIGIBLE.value, incomp_gpt.mismatch_reasons)

        incomp_gemini = next(t for t in result.incompatible_targets if t.model_id == "gemini-2.0-flash")
        self.assertIn(MismatchReason.PROVIDER_INELIGIBLE.value, incomp_gemini.mismatch_reasons)

    def test_08_zero_compatible_models_handling(self) -> None:
        """Verify extreme requirements result in 0 compatible targets with explainable mismatch reasons."""
        ctx = self._build_context(min_context_tokens=2000000)  # 2M tokens exceeds all
        result = self.resolver.resolve(ctx, None, self.registry)

        self.assertEqual(result.total_compatible, 0)
        self.assertEqual(len(result.compatible_targets), 0)
        self.assertEqual(result.total_evaluated, 4)
        self.assertEqual(len(result.incompatible_targets), 4)

    def test_09_workload_classification_integration(self) -> None:
        """Verify resolver incorporates requirements from WorkloadClassification."""
        ctx = self._build_context()  # Empty direct constraints
        clf = WorkloadClassification(
            category=WorkloadCategory.MULTIMODAL,
            dimensions=WorkloadDimensions(
                requires_vision=True,
                estimated_context_tokens=150000
            )
        )
        result = self.resolver.resolve(ctx, clf, self.registry)

        # Only models with vision AND >= 150k tokens (claude-3-7-sonnet and gemini-2.0-flash)
        comp_ids = [t.model_id for t in result.compatible_targets]
        self.assertIn("claude-3-7-sonnet", comp_ids)
        self.assertIn("gemini-2.0-flash", comp_ids)
        self.assertNotIn("gpt-4o", comp_ids)
        self.assertNotIn("deepseek-v3", comp_ids)

    def test_10_deterministic_resolution_results(self) -> None:
        """Verify repeated resolutions yield identical results."""
        ctx = self._build_context(supports_vision=True, min_context_tokens=100000)
        res1 = self.resolver.resolve(ctx, None, self.registry)
        res2 = self.resolver.resolve(ctx, None, self.registry)

        d1 = res1.model_dump()
        d2 = res2.model_dump()
        d1.pop("resolution_timestamp", None)
        d2.pop("resolution_timestamp", None)
        self.assertEqual(d1, d2)

    def test_11_immutability_inputs_not_mutated(self) -> None:
        """Verify resolver does not mutate ExecutionContext, Classification, or Registry."""
        ctx = self._build_context(supports_vision=True)
        ctx_before = ctx.model_dump()

        clf = WorkloadClassification(category=WorkloadCategory.CODING)
        clf_before = clf.model_dump()

        _ = self.resolver.resolve(ctx, clf, self.registry)

        self.assertEqual(ctx.model_dump(), ctx_before)
        self.assertEqual(clf.model_dump(), clf_before)

    def test_12_service_boundary_delegation(self) -> None:
        """Verify CapabilityResolverService orchestrates resolver correctly."""
        ctx = self._build_context(supports_tools=True)
        res = self.service.resolve(ctx)
        self.assertIsInstance(res, CapabilityResolutionResult)
        self.assertEqual(res.total_evaluated, 4)

    def test_13_no_ranking_or_winner_in_output(self) -> None:
        """Verify output has no rank, score, winner, or recommended target fields."""
        ctx = self._build_context()
        res = self.resolver.resolve(ctx, None, self.registry)
        dump = res.model_dump()

        self.assertNotIn("selected_target", dump)
        self.assertNotIn("recommended_target", dump)
        self.assertNotIn("winner", dump)
        self.assertNotIn("score", dump)
        self.assertNotIn("rank", dump)

        for target in res.compatible_targets:
            t_dump = target.model_dump()
            self.assertNotIn("score", t_dump)
            self.assertNotIn("rank", t_dump)
            self.assertNotIn("weight", t_dump)

    def test_14_zero_database_imports_in_resolver_package(self) -> None:
        """Verify resolver package contains zero database library imports."""
        import infuse.resolver
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.resolver")]

        forbidden = ["sqlite3", "psycopg2", "asyncpg", "sqlalchemy", "redis", "qdrant_client", "motor", "pymongo"]
        for mod in modules:
            src = inspect.getsource(mod)
            for f in forbidden:
                self.assertNotIn(f"import {f}", src)
                self.assertNotIn(f"from {f}", src)

    def test_15_zero_provider_and_agent_sdk_imports(self) -> None:
        """Verify resolver package contains zero provider or agent SDK imports."""
        import infuse.resolver
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.resolver")]

        forbidden = ["openai", "anthropic", "google.generativeai", "cohere", "langchain", "crewai", "autogen"]
        for mod in modules:
            src = inspect.getsource(mod)
            for f in forbidden:
                self.assertNotIn(f"import {f}", src)
                self.assertNotIn(f"from {f}", src)

    def test_16_zero_routing_pricing_and_governor_logic(self) -> None:
        """Verify resolver contains zero routing decisions, pricing calculations, or Governor logic."""
        import infuse.resolver
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.resolver")]

        forbidden_patterns = ["select_provider", "route_request", "decide_action", "apply_governance", "calculate_cost"]
        for mod in modules:
            src = inspect.getsource(mod)
            for p in forbidden_patterns:
                self.assertNotIn(p, src)


if __name__ == "__main__":
    unittest.main()
