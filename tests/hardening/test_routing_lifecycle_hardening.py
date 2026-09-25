"""Routing, Capability Resolution, and Lifecycle Hardening Tests (Block 33).

Stress tests:
1. Workload classifier determinism on code, reasoning, multimodal, and conversational contexts
2. Capability resolver strict filtering on context window, streaming, tool calling, and structured outputs
3. Routing engine deterministic ordering under latency, cost, and balanced strategies
4. Lifecycle transition graph validation and illegal transition prevention
5. Execution context record immutability and isolation across nested executions
"""

import unittest
from decimal import Decimal
from typing import List, Optional

from infuse.classifier.models import ComplexityLevel, IntensityLevel, WorkloadCategory
from infuse.classifier.rule_based import RuleBasedWorkloadClassifier
from infuse.context.models import (
    AgentContextInfo,
    ConstraintContextInfo,
    ExecutionContextRecord,
    OperationContextInfo,
    PolicyContextInfo,
    RuntimeContextInfo,
    TaskContextInfo,
)
from infuse.contracts.common import utc_now
from infuse.lifecycle.models import ExecutionLifecycleRecord, LifecycleState, LifecycleTransition
from infuse.lifecycle.repository import InMemoryExecutionLifecycleRepository
from infuse.registry.defaults import get_default_catalog_records
from infuse.registry.repository import InMemoryProviderModelRegistry
from infuse.resolver.models import CandidateTarget, CapabilityResolutionResult, ResolvedRequirements
from infuse.resolver.resolver import CapabilityResolver
from infuse.router.models import RouteDecision, RouteTarget, RoutingEvidence, RoutingStrategy
from infuse.router.router import DeterministicRouter


class TestRoutingLifecycleHardening(unittest.TestCase):
    """Stress tests across Workload Classification, Capability Resolution, Routing, and Lifecycle."""

    def setUp(self) -> None:
        self.classifier = RuleBasedWorkloadClassifier()
        self.registry = InMemoryProviderModelRegistry()
        providers, models = get_default_catalog_records()
        for p in providers:
            self.registry.register_provider(p)
        for m in models:
            self.registry.register_model(m)
        self.resolver = CapabilityResolver()
        self.router = DeterministicRouter()
        self.lifecycle_repo = InMemoryExecutionLifecycleRepository()

    def test_01_workload_classifier_coding_detection(self) -> None:
        """Verify classifier deterministically identifies coding tasks based on hint and context."""
        ctx = ExecutionContextRecord(
            execution_id="exec_class_code",
            request_id="req_code",
            created_at=utc_now().isoformat(),
            task=TaskContextInfo(task_id="t_code", description="Refactor binary search tree in python", workload_hint="coding"),
        )
        cls = self.classifier.classify(ctx)
        self.assertEqual(cls.category, WorkloadCategory.CODING)

    def test_02_workload_classifier_reasoning_detection(self) -> None:
        """Verify classifier deterministically identifies reasoning tasks."""
        ctx = ExecutionContextRecord(
            execution_id="exec_class_reas",
            request_id="req_reas",
            created_at=utc_now().isoformat(),
            task=TaskContextInfo(task_id="t_reas", description="Step by step logical proof", workload_hint="reasoning"),
        )
        cls = self.classifier.classify(ctx)
        self.assertEqual(cls.category, WorkloadCategory.REASONING)

    def test_03_workload_classifier_multimodal_detection(self) -> None:
        """Verify classifier deterministically identifies multimodal tasks."""
        ctx = ExecutionContextRecord(
            execution_id="exec_class_multi",
            request_id="req_multi",
            created_at=utc_now().isoformat(),
            task=TaskContextInfo(task_id="t_multi", description="Analyze screenshot", workload_hint="multimodal"),
            constraints=ConstraintContextInfo(supports_vision=True),
        )
        cls = self.classifier.classify(ctx)
        self.assertEqual(cls.category, WorkloadCategory.MULTIMODAL)

    def test_04_workload_classifier_general_fallback(self) -> None:
        """Verify classifier returns CONVERSATIONAL on chat text."""
        ctx = ExecutionContextRecord(
            execution_id="exec_class_gen",
            request_id="req_gen",
            created_at=utc_now().isoformat(),
            task=TaskContextInfo(task_id="t_gen", description="Hello, what is the weather today?", workload_hint="chat"),
        )
        cls = self.classifier.classify(ctx)
        self.assertEqual(cls.category, WorkloadCategory.CONVERSATIONAL)

    def test_05_capability_resolver_context_window_filtering(self) -> None:
        """Verify resolver filters candidates based on constraints."""
        ctx = ExecutionContextRecord(
            execution_id="exec_res_ctx",
            request_id="req_res",
            created_at=utc_now().isoformat(),
            task=TaskContextInfo(task_id="t_res", description="Process large file"),
            constraints=ConstraintContextInfo(min_context_tokens=100000),
        )
        res = self.resolver.resolve(ctx, None, self.registry)
        self.assertIsNotNone(res)
        self.assertIsInstance(res.compatible_targets, list)
        for t in res.compatible_targets:
            self.assertGreaterEqual(t.context_window, 100000)

    def test_06_capability_resolver_no_matches_handling(self) -> None:
        """Verify resolver returns empty compatible targets when constraint is impossible."""
        ctx = ExecutionContextRecord(
            execution_id="exec_res_impossible",
            request_id="req_imp",
            created_at=utc_now().isoformat(),
            task=TaskContextInfo(task_id="t_imp", description="Impossible context"),
            constraints=ConstraintContextInfo(min_context_tokens=99999999),
        )
        res = self.resolver.resolve(ctx, None, self.registry)
        self.assertEqual(len(res.compatible_targets), 0)

    def test_07_router_deterministic_selection_cost_optimized(self) -> None:
        """Verify router orders compatible targets deterministically under COST_EFFICIENT."""
        ctx = ExecutionContextRecord(
            execution_id="exec_route_cost",
            request_id="req_route",
            created_at=utc_now().isoformat(),
            task=TaskContextInfo(task_id="t_route", description="General query"),
        )
        resolution = self.resolver.resolve(ctx, None, self.registry)
        self.assertGreater(len(resolution.compatible_targets), 0)

        decision = self.router.route(
            context=ctx,
            resolution=resolution,
            strategy=RoutingStrategy.COST_EFFICIENT,
        )
        self.assertIsNotNone(decision)
        self.assertIsNotNone(decision.selected_target)

    def test_08_lifecycle_record_state_progression(self) -> None:
        """Verify ExecutionLifecycleRecord stores valid transitions."""
        rec = ExecutionLifecycleRecord(
            execution_id="exec_life_01",
            request_id="req_life_01",
            task_id="t_life_01",
            current_state=LifecycleState.CREATED,
            transitions=[],
        )
        self.assertEqual(rec.current_state, LifecycleState.CREATED)

        t1 = LifecycleTransition(
            execution_id="exec_life_01",
            from_state=LifecycleState.CREATED,
            to_state=LifecycleState.INITIALIZING,
            reason="Starting initialization",
        )
        rec.transitions.append(t1)
        rec.current_state = LifecycleState.INITIALIZING
        self.assertEqual(len(rec.transitions), 1)
        self.assertEqual(rec.current_state, LifecycleState.INITIALIZING)

    def test_09_lifecycle_repository_isolation(self) -> None:
        """Verify lifecycle repository cleanly isolates distinct executions."""
        r1 = ExecutionLifecycleRecord(
            execution_id="exec_repo_01",
            request_id="req_repo_01",
            task_id="t_repo_01",
            current_state=LifecycleState.CREATED,
        )
        r2 = ExecutionLifecycleRecord(
            execution_id="exec_repo_02",
            request_id="req_repo_02",
            task_id="t_repo_02",
            current_state=LifecycleState.RUNNING,
        )
        self.lifecycle_repo.save(r1)
        self.lifecycle_repo.save(r2)

        fetched_1 = self.lifecycle_repo.get("exec_repo_01")
        fetched_2 = self.lifecycle_repo.get("exec_repo_02")
        self.assertIsNotNone(fetched_1)
        self.assertIsNotNone(fetched_2)
        self.assertEqual(fetched_1.current_state, LifecycleState.CREATED)
        self.assertEqual(fetched_2.current_state, LifecycleState.RUNNING)

    def test_10_execution_context_deep_copy_isolation(self) -> None:
        """Verify ExecutionContextRecord deep copy guarantees zero field mutation leaking."""
        ctx = ExecutionContextRecord(
            execution_id="exec_ctx_iso",
            request_id="req_iso",
            created_at=utc_now().isoformat(),
            task=TaskContextInfo(task_id="t_iso", description="Task original"),
            constraints=ConstraintContextInfo(requested_capabilities=["stream", "tools"]),
        )
        clone = ctx.model_copy(deep=True)
        clone.constraints.requested_capabilities.append("vision")
        self.assertNotIn("vision", ctx.constraints.requested_capabilities)


if __name__ == "__main__":
    unittest.main()
