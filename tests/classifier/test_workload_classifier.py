"""Comprehensive Unit & Architectural Test Suite for Block 08 Workload Classifier."""

import inspect
import sys
import unittest

from infuse.classifier.interfaces import IWorkloadClassifier
from infuse.classifier.models import (
    ComplexityLevel,
    IntensityLevel,
    WorkloadCategory,
    WorkloadClassification,
    WorkloadDimensions,
)
from infuse.classifier.rule_based import RuleBasedWorkloadClassifier
from infuse.classifier.service import WorkloadClassificationService
from infuse.context.builder import ExecutionContextBuilder
from infuse.version import SCHEMA_VERSION


class TestWorkloadClassifier(unittest.TestCase):
    """Test suite verifying Workload Classifier determinism, category resolution, complexity scoring, and isolation."""

    def setUp(self) -> None:
        self.classifier = RuleBasedWorkloadClassifier()
        self.service = WorkloadClassificationService(classifier=self.classifier)

    def _build_context(
        self,
        task_id="task_1",
        workload_hint=None,
        description="Sample task",
        tags=None,
        requested_capabilities=None,
        min_context_tokens=None,
        max_latency_ms=None,
        supports_tools=False,
        supports_vision=False,
        supports_structured_output=False,
        step_index=0,
        workflow_id=None,
        message_count=1,
        tool_count=0
    ):
        builder = ExecutionContextBuilder()
        builder.set_identity(execution_id="exec_test_01", request_id="req_test_01")
        builder.set_task(
            task_id=task_id,
            description=description,
            workload_hint=workload_hint,
            tags=tags or []
        )
        builder.set_runtime(
            session_id="sess_1",
            workflow_id=workflow_id,
            step_index=step_index
        )
        builder.set_constraints(
            requested_capabilities=requested_capabilities or [],
            min_context_tokens=min_context_tokens,
            max_latency_ms=max_latency_ms,
            supports_tools=supports_tools,
            supports_vision=supports_vision,
            supports_structured_output=supports_structured_output
        )
        builder.set_operation(
            message_count=message_count,
            has_tools=tool_count > 0,
            tool_count=tool_count
        )
        return builder.build()

    def test_01_classifier_interface_and_return_type(self) -> None:
        """Verify classifier returns canonical WorkloadClassification model."""
        ctx = self._build_context(workload_hint="coding")
        result = self.classifier.classify(ctx)
        self.assertIsInstance(result, WorkloadClassification)
        self.assertEqual(result.schema_version, SCHEMA_VERSION)
        self.assertIsInstance(result.dimensions, WorkloadDimensions)
        self.assertEqual(result.category, WorkloadCategory.CODING)
        self.assertEqual(result.complexity_level, ComplexityLevel.LOW)

    def test_02_caller_workload_hint_mapping(self) -> None:
        """Verify caller workload_hint takes precedence and maps to canonical categories."""
        test_cases = [
            ("coding", WorkloadCategory.CODING),
            ("code", WorkloadCategory.CODING),
            ("reasoning", WorkloadCategory.REASONING),
            ("chat", WorkloadCategory.CONVERSATIONAL),
            ("fast-chat", WorkloadCategory.CONVERSATIONAL),
            ("tools", WorkloadCategory.TOOL_USE),
            ("web", WorkloadCategory.WEB_ENABLED),
            ("vision", WorkloadCategory.MULTIMODAL),
            ("extract", WorkloadCategory.EXTRACTION),
            ("transform", WorkloadCategory.TRANSFORMATION),
            ("workflow", WorkloadCategory.WORKFLOW_EXECUTION),
            ("STRUCTURED_GENERATION", WorkloadCategory.STRUCTURED_GENERATION),
        ]
        for hint, expected_category in test_cases:
            with self.subTest(hint=hint):
                ctx = self._build_context(workload_hint=hint)
                result = self.classifier.classify(ctx)
                self.assertEqual(result.category, expected_category)
                self.assertTrue(any(f"mapped from caller workload_hint '{hint}'" in e or "matched explicit canonical enum" in e for e in result.evidence))

    def test_03_inferred_category_from_signals_when_hint_missing(self) -> None:
        """Verify category is inferred from capability signals when workload_hint is omitted."""
        # Vision -> MULTIMODAL
        ctx_vis = self._build_context(supports_vision=True)
        self.assertEqual(self.classifier.classify(ctx_vis).category, WorkloadCategory.MULTIMODAL)

        # Tools -> TOOL_USE
        ctx_tools = self._build_context(supports_tools=True, tool_count=2)
        self.assertEqual(self.classifier.classify(ctx_tools).category, WorkloadCategory.TOOL_USE)

        # Web capability -> WEB_ENABLED
        ctx_web = self._build_context(requested_capabilities=["web"])
        self.assertEqual(self.classifier.classify(ctx_web).category, WorkloadCategory.WEB_ENABLED)

        # Structured output -> STRUCTURED_GENERATION
        ctx_struct = self._build_context(supports_structured_output=True)
        self.assertEqual(self.classifier.classify(ctx_struct).category, WorkloadCategory.STRUCTURED_GENERATION)

        # Workflow step -> WORKFLOW_EXECUTION
        ctx_wf = self._build_context(step_index=3, workflow_id="pipeline_01")
        self.assertEqual(self.classifier.classify(ctx_wf).category, WorkloadCategory.WORKFLOW_EXECUTION)

        # Plain conversation
        ctx_conv = self._build_context(message_count=6)
        self.assertEqual(self.classifier.classify(ctx_conv).category, WorkloadCategory.CONVERSATIONAL)

    def test_04_secondary_categories_tracking(self) -> None:
        """Verify secondary capabilities are recorded in secondary_categories."""
        ctx = self._build_context(
            workload_hint="coding",
            supports_tools=True,
            tool_count=3,
            requested_capabilities=["web"],
            supports_structured_output=True
        )
        res = self.classifier.classify(ctx)
        self.assertEqual(res.category, WorkloadCategory.CODING)
        self.assertIn(WorkloadCategory.TOOL_USE, res.secondary_categories)
        self.assertIn(WorkloadCategory.WEB_ENABLED, res.secondary_categories)
        self.assertIn(WorkloadCategory.STRUCTURED_GENERATION, res.secondary_categories)

    def test_05_deterministic_classification_output(self) -> None:
        """Verify identical contexts produce strictly identical classifications."""
        ctx1 = self._build_context(
            workload_hint="research",
            requested_capabilities=["web"],
            min_context_tokens=16000,
            max_latency_ms=2000.0,
            tool_count=2
        )
        ctx2 = self._build_context(
            workload_hint="research",
            requested_capabilities=["web"],
            min_context_tokens=16000,
            max_latency_ms=2000.0,
            tool_count=2
        )
        res1 = self.classifier.classify(ctx1)
        res2 = self.classifier.classify(ctx2)
        self.assertEqual(res1.model_dump(), res2.model_dump())

    def test_06_immutability_execution_context_not_mutated(self) -> None:
        """Verify classifier does not alter or mutate the input ExecutionContext."""
        ctx = self._build_context(
            task_id="task_immutability",
            workload_hint="coding",
            min_context_tokens=8192
        )
        before_dump = ctx.model_dump()
        _ = self.classifier.classify(ctx)
        after_dump = ctx.model_dump()
        self.assertEqual(before_dump, after_dump)

    def test_07_complexity_scoring_and_levels(self) -> None:
        """Verify complexity score increases deterministically with complexity factors."""
        # Simple chat
        ctx_simple = self._build_context(workload_hint="chat", message_count=1)
        res_simple = self.classifier.classify(ctx_simple)
        self.assertEqual(res_simple.complexity_level, ComplexityLevel.LOW)
        self.assertLess(res_simple.complexity_score, 0.30)

        # Moderate coding with tools
        ctx_mod = self._build_context(
            workload_hint="coding",
            supports_tools=True,
            tool_count=2,
            min_context_tokens=4000
        )
        res_mod = self.classifier.classify(ctx_mod)
        self.assertEqual(res_mod.complexity_level, ComplexityLevel.MODERATE)
        self.assertTrue(0.30 <= res_mod.complexity_score < 0.60)

        # Complex multi-step agent with tools, web, structured output, long context
        ctx_high = self._build_context(
            workload_hint="agent",
            supports_tools=True,
            tool_count=5,
            requested_capabilities=["web"],
            supports_vision=True,
            supports_structured_output=True,
            step_index=4,
            min_context_tokens=40000,
            message_count=12
        )
        res_high = self.classifier.classify(ctx_high)
        self.assertIn(res_high.complexity_level, [ComplexityLevel.HIGH, ComplexityLevel.VERY_HIGH])
        self.assertGreaterEqual(res_high.complexity_score, 0.70)
        self.assertLessEqual(res_high.complexity_score, 1.0)

    def test_08_dimensions_and_intensities(self) -> None:
        """Verify resource dimensions and intensity levels are mapped correctly."""
        ctx = self._build_context(
            min_context_tokens=32000,
            max_latency_ms=500.0,
            tool_count=4,
            requested_capabilities=["web"]
        )
        res = self.classifier.classify(ctx)
        dims = res.dimensions
        self.assertEqual(dims.context_intensity, IntensityLevel.HIGH)
        self.assertEqual(dims.latency_sensitivity, IntensityLevel.HIGH)
        self.assertEqual(dims.tool_intensity, IntensityLevel.MEDIUM)
        self.assertTrue(dims.requires_tools)
        self.assertTrue(dims.requires_web)
        self.assertEqual(dims.tool_count, 4)

    def test_09_evidence_and_explainability(self) -> None:
        """Verify classification evidence provides clear traceability."""
        ctx = self._build_context(
            workload_hint="coding",
            supports_tools=True,
            tool_count=2
        )
        res = self.classifier.classify(ctx)
        self.assertGreater(len(res.evidence), 0)
        evidence_str = " ".join(res.evidence)
        self.assertIn("Category 'CODING'", evidence_str)
        self.assertIn("Dimensions: tools=True", evidence_str)
        self.assertIn("Derived complexity score", evidence_str)

    def test_10_unknown_handling_for_empty_context(self) -> None:
        """Verify empty context with zero signals yields UNKNOWN category."""
        ctx = self._build_context(
            task_id="task_blank",
            workload_hint=None,
            description=None,
            message_count=0,
            tool_count=0
        )
        res = self.classifier.classify(ctx)
        self.assertEqual(res.category, WorkloadCategory.UNKNOWN)
        self.assertFalse(res.dimensions.requires_tools)

    def test_11_service_boundary_delegation(self) -> None:
        """Verify WorkloadClassificationService delegates to underlying classifier."""
        ctx = self._build_context(workload_hint="coding")
        res = self.service.classify(ctx)
        self.assertEqual(res.category, WorkloadCategory.CODING)

    def test_12_classifier_independence_from_provider_registry(self) -> None:
        """Verify classification result contains zero provider or model selection fields."""
        ctx = self._build_context(workload_hint="coding")
        res = self.classifier.classify(ctx)
        dump = res.model_dump()
        self.assertNotIn("selected_provider", dump)
        self.assertNotIn("recommended_model", dump)
        self.assertNotIn("route", dump)
        self.assertNotIn("cost_usd", dump)
        self.assertNotIn("action", dump)

    def test_13_zero_database_imports_in_classifier_package(self) -> None:
        """Verify classifier package contains zero database library imports."""
        import infuse.classifier
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.classifier")]

        forbidden = ["sqlite3", "psycopg2", "asyncpg", "sqlalchemy", "redis", "qdrant_client", "motor", "pymongo"]
        for mod in modules:
            src = inspect.getsource(mod)
            for f in forbidden:
                self.assertNotIn(f"import {f}", src)
                self.assertNotIn(f"from {f}", src)

    def test_14_zero_provider_and_agent_sdk_imports(self) -> None:
        """Verify classifier package contains zero provider or agent SDK imports."""
        import infuse.classifier
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.classifier")]

        forbidden = ["openai", "anthropic", "google.generativeai", "cohere", "langchain", "crewai", "autogen"]
        for mod in modules:
            src = inspect.getsource(mod)
            for f in forbidden:
                self.assertNotIn(f"import {f}", src)
                self.assertNotIn(f"from {f}", src)

    def test_15_zero_routing_and_governor_logic(self) -> None:
        """Verify classifier contains zero routing, Governor decision, or pricing logic."""
        import infuse.classifier
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.classifier")]

        forbidden_patterns = ["select_provider", "route_request", "decide_action", "apply_governance", "calculate_cost"]
        for mod in modules:
            src = inspect.getsource(mod)
            for p in forbidden_patterns:
                self.assertNotIn(p, src)


if __name__ == "__main__":
    unittest.main()
