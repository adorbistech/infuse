"""Comprehensive Unit & Architectural Test Suite for Block 11 Deterministic Router."""

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
from infuse.resolver.models import (
    CandidateTarget,
    CapabilityResolutionResult,
    IncompatibleTarget,
    ResolvedRequirements,
)
from infuse.router.errors import NoCompatibleTargetsError
from infuse.router.interfaces import IRouter
from infuse.router.models import (
    RouteDecision,
    RoutingStrategy,
)
from infuse.router.router import DeterministicRouter
from infuse.router.service import RouterService
from infuse.version import SCHEMA_VERSION


class TestDeterministicRouter(unittest.TestCase):
    """Test suite verifying target selection, preference handling, fallback ordering, determinism, and boundaries."""

    def setUp(self) -> None:
        self.router = DeterministicRouter()
        self.service = RouterService(router=self.router)

    def _sample_candidates(self):
        return [
            CandidateTarget(
                provider_id="anthropic",
                model_id="claude-3-7-sonnet",
                context_window=200000,
                max_output_tokens=8192,
                declared_capabilities=["tools", "vision", "caching", "reasoning", "coding"],
                supported_modalities=["text", "vision"]
            ),
            CandidateTarget(
                provider_id="openai",
                model_id="gpt-4o",
                context_window=128000,
                max_output_tokens=4096,
                declared_capabilities=["tools", "vision", "json", "streaming"],
                supported_modalities=["text", "vision"]
            ),
            CandidateTarget(
                provider_id="google",
                model_id="gemini-2.0-flash",
                context_window=1000000,
                max_output_tokens=8192,
                declared_capabilities=["tools", "vision", "audio", "long_context", "streaming"],
                supported_modalities=["text", "vision", "audio"]
            ),
            CandidateTarget(
                provider_id="deepseek",
                model_id="deepseek-v3",
                context_window=64000,
                max_output_tokens=4096,
                declared_capabilities=["tools", "coding", "json"],
                supported_modalities=["text"]
            ),
        ]

    def _build_context(
        self,
        preferred_providers=None,
        preferred_models=None,
        metadata=None
    ):
        builder = ExecutionContextBuilder()
        builder.set_identity(execution_id="exec_route_01", request_id="req_route_01")
        builder.set_task(task_id="task_route_01", workload_hint="coding")
        builder.set_constraints(
            preferred_providers=preferred_providers or [],
            preferred_models=preferred_models or [],
            metadata=metadata or {}
        )
        return builder.build()

    def _build_resolution(
        self,
        compatible=None,
        preferred_providers=None,
        preferred_models=None
    ):
        cand = self._sample_candidates() if compatible is None else compatible
        req = ResolvedRequirements(
            preferred_providers=preferred_providers or [],
            preferred_models=preferred_models or []
        )
        return CapabilityResolutionResult(
            requirements=req,
            compatible_targets=cand,
            incompatible_targets=[],
            total_evaluated=len(cand),
            total_compatible=len(cand)
        )

    def test_01_single_compatible_candidate_routing(self) -> None:
        """Verify routing when exactly one compatible target exists."""
        single_cand = [self._sample_candidates()[0]]
        ctx = self._build_context()
        res = self._build_resolution(compatible=single_cand)

        decision = self.router.route(ctx, res)
        self.assertIsInstance(decision, RouteDecision)
        self.assertEqual(decision.execution_id, "exec_route_01")
        self.assertEqual(decision.selected_target.model_id, "claude-3-7-sonnet")
        self.assertEqual(len(decision.fallback_targets), 0)
        self.assertEqual(decision.evidence.candidates_evaluated_count, 1)

    def test_02_multiple_compatible_candidates_selection_and_fallbacks(self) -> None:
        """Verify multiple compatible candidates produce a primary target and ordered fallbacks."""
        ctx = self._build_context()
        res = self._build_resolution()

        decision = self.router.route(ctx, res)
        self.assertIsNotNone(decision.selected_target)
        self.assertEqual(len(decision.fallback_targets), 3)

        # Ensure all 4 candidates are accounted for without duplication
        all_models = [decision.selected_target.model_id] + [f.model_id for f in decision.fallback_targets]
        self.assertEqual(len(all_models), 4)
        self.assertEqual(len(set(all_models)), 4)

    def test_03_zero_compatible_candidates_raises_error(self) -> None:
        """Verify empty compatible targets raises NoCompatibleTargetsError."""
        ctx = self._build_context()
        empty_res = CapabilityResolutionResult(
            requirements=ResolvedRequirements(),
            compatible_targets=[],
            incompatible_targets=[
                IncompatibleTarget(
                    provider_id="openai",
                    model_id="gpt-4o",
                    mismatch_reasons=["missing_required_capability:vision"]
                )
            ],
            total_evaluated=1,
            total_compatible=0
        )

        with self.assertRaises(NoCompatibleTargetsError):
            self.router.route(ctx, empty_res)

    def test_04_explicit_provider_preference_selection(self) -> None:
        """Verify explicit preferred provider drives primary target selection."""
        ctx = self._build_context(preferred_providers=["google"])
        res = self._build_resolution(preferred_providers=["google"])

        decision = self.router.route(ctx, res)
        self.assertEqual(decision.selected_target.provider_id, "google")
        self.assertEqual(decision.selected_target.model_id, "gemini-2.0-flash")
        self.assertTrue(decision.evidence.preference_matched)

    def test_05_explicit_model_preference_selection(self) -> None:
        """Verify explicit preferred model drives primary target selection."""
        ctx = self._build_context(preferred_models=["deepseek-v3"])
        res = self._build_resolution(preferred_models=["deepseek-v3"])

        decision = self.router.route(ctx, res)
        self.assertEqual(decision.selected_target.provider_id, "deepseek")
        self.assertEqual(decision.selected_target.model_id, "deepseek-v3")
        self.assertTrue(decision.evidence.preference_matched)

    def test_06_model_preference_takes_precedence_over_provider_preference(self) -> None:
        """Verify model preference takes precedence over conflicting provider preference."""
        ctx = self._build_context(
            preferred_providers=["openai"],
            preferred_models=["claude-3-7-sonnet"]
        )
        res = self._build_resolution(
            preferred_providers=["openai"],
            preferred_models=["claude-3-7-sonnet"]
        )

        decision = self.router.route(ctx, res)
        self.assertEqual(decision.selected_target.model_id, "claude-3-7-sonnet")
        self.assertEqual(decision.selected_target.provider_id, "anthropic")

    def test_07_preference_index_precedence(self) -> None:
        """Verify the first model in preferred_models list is selected over the second."""
        ctx = self._build_context(preferred_models=["gpt-4o", "claude-3-7-sonnet"])
        res = self._build_resolution(preferred_models=["gpt-4o", "claude-3-7-sonnet"])

        decision = self.router.route(ctx, res)
        self.assertEqual(decision.selected_target.model_id, "gpt-4o")
        # Second preference should appear first in fallback targets
        self.assertEqual(decision.fallback_targets[0].model_id, "claude-3-7-sonnet")

    def test_08_workload_fit_strategy(self) -> None:
        """Verify WORKLOAD_FIT strategy prioritizes reasoning models on complex workloads."""
        ctx = self._build_context()
        res = self._build_resolution()
        clf = WorkloadClassification(
            category=WorkloadCategory.CODING,
            complexity_level=ComplexityLevel.HIGH,
            complexity_score=0.85
        )

        decision = self.router.route(ctx, res, classification=clf, strategy=RoutingStrategy.WORKLOAD_FIT)
        # Claude 3.7 Sonnet declares "reasoning" & "coding"
        self.assertEqual(decision.selected_target.model_id, "claude-3-7-sonnet")
        self.assertEqual(decision.strategy_used, RoutingStrategy.WORKLOAD_FIT)

    def test_09_low_latency_strategy(self) -> None:
        """Verify LOW_LATENCY strategy prioritizes streaming/compact models."""
        ctx = self._build_context()
        res = self._build_resolution()

        decision = self.router.route(ctx, res, strategy=RoutingStrategy.LOW_LATENCY)
        self.assertEqual(decision.strategy_used, RoutingStrategy.LOW_LATENCY)
        self.assertIsNotNone(decision.selected_target)

    def test_10_deterministic_reproducibility(self) -> None:
        """Verify repeated route calls produce identical decision outputs."""
        ctx = self._build_context(preferred_providers=["anthropic"])
        res = self._build_resolution(preferred_providers=["anthropic"])

        d1 = self.router.route(ctx, res)
        d2 = self.router.route(ctx, res)

        m1 = d1.model_dump()
        m2 = d2.model_dump()
        # Route IDs and timestamps are unique per decision instance
        m1.pop("route_id")
        m2.pop("route_id")
        m1.pop("timestamp")
        m2.pop("timestamp")
        self.assertEqual(m1, m2)

    def test_11_immutability_inputs_not_mutated(self) -> None:
        """Verify router does not mutate Context or Resolution inputs."""
        ctx = self._build_context()
        ctx_dump = ctx.model_dump()

        res = self._build_resolution()
        res_dump = res.model_dump()

        _ = self.router.route(ctx, res)

        self.assertEqual(ctx.model_dump(), ctx_dump)
        self.assertEqual(res.model_dump(), res_dump)

    def test_12_service_boundary_delegation(self) -> None:
        """Verify RouterService orchestrates route selection correctly."""
        ctx = self._build_context()
        res = self._build_resolution()

        decision = self.service.route(ctx, res)
        self.assertIsInstance(decision, RouteDecision)
        self.assertEqual(decision.schema_version, SCHEMA_VERSION)

    def test_13_zero_database_imports_in_router_package(self) -> None:
        """Verify router package contains zero database library imports."""
        import infuse.router
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.router")]

        forbidden = ["sqlite3", "psycopg2", "asyncpg", "sqlalchemy", "redis", "qdrant_client", "motor", "pymongo"]
        for mod in modules:
            src = inspect.getsource(mod)
            for f in forbidden:
                self.assertNotIn(f"import {f}", src)
                self.assertNotIn(f"from {f}", src)

    def test_14_zero_provider_and_agent_sdk_imports(self) -> None:
        """Verify router package contains zero provider or agent SDK imports."""
        import infuse.router
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.router")]

        forbidden = ["openai", "anthropic", "google.generativeai", "cohere", "langchain", "crewai", "autogen"]
        for mod in modules:
            src = inspect.getsource(mod)
            for f in forbidden:
                self.assertNotIn(f"import {f}", src)
                self.assertNotIn(f"from {f}", src)

    def test_15_zero_pricing_health_and_governor_logic(self) -> None:
        """Verify router contains zero pricing calculations, health pings, or Governor logic."""
        import infuse.router
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.router")]

        forbidden_patterns = ["calculate_cost", "calculate_price", "probe_health", "ping_provider", "issue_action", "apply_governance"]
        for mod in modules:
            src = inspect.getsource(mod)
            for p in forbidden_patterns:
                self.assertNotIn(p, src)


if __name__ == "__main__":
    unittest.main()
