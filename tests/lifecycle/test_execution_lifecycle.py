"""Comprehensive Unit and Architectural Test Suite for Block 13 Execution Lifecycle."""

import inspect
import sys
import unittest
from typing import List, Optional

from infuse.contracts.execution import (
    ExecutionContext,
    ExecutionRequest,
    ExecutionRequirements,
    ExecutionResult,
    ExecutionStatus,
    OperationRequest,
    TaskContext,
)
from infuse.lifecycle.errors import (
    ExecutionAlreadyExistsError,
    ExecutionCancellationError,
    ExecutionNotFoundError,
    InvalidStateTransitionError,
)
from infuse.lifecycle.interfaces import (
    IExecutionLifecycleRepository,
    IExecutionLifecycleService,
)
from infuse.lifecycle.models import (
    ExecutionLifecycleRecord,
    LifecycleState,
    LifecycleTransition,
)
from infuse.lifecycle.repository import (
    InMemoryExecutionLifecycleRepository,
    VALID_TRANSITIONS,
)
from infuse.lifecycle.service import ExecutionLifecycleService
from infuse.providers.adapters.mock import MockProviderAdapter
from infuse.providers.models import ProviderUsage
from infuse.providers.registry import InMemoryProviderAdapterRegistry
from infuse.providers.service import ProviderAdapterService
from infuse.registry.models import ModelRecord, ProviderRecord
from infuse.registry.repository import InMemoryProviderModelRegistry
from infuse.resolver.resolver import CapabilityResolver
from infuse.resolver.service import CapabilityResolverService
from infuse.router.models import RoutingStrategy
from infuse.router.service import RouterService


class TestExecutionLifecycleLayer(unittest.TestCase):
    """Test suite verifying execution lifecycle states, transitions, orchestration, and isolation."""

    def setUp(self) -> None:
        # Standard registry setup
        self.model_registry = InMemoryProviderModelRegistry()
        self.model_registry.register_provider(ProviderRecord(
            provider_id="mock",
            name="Mock Provider",
            supported_modalities=["text"]
        ))
        self.model_registry.register_model(ModelRecord(
            model_id="mock-fast",
            provider_id="mock",
            name="Mock Fast Model",
            context_window=128000,
            max_output_tokens=4096
        ))
        self.model_registry.register_model(ModelRecord(
            model_id="mock-pro",
            provider_id="mock",
            name="Mock Pro Model",
            context_window=128000,
            max_output_tokens=8192
        ))

        # Adapter service setup
        self.adapter_registry = InMemoryProviderAdapterRegistry()
        self.mock_adapter = MockProviderAdapter(
            provider_id="mock",
            supported_models=["mock-fast", "mock-pro"]
        )
        self.adapter_registry.register(self.mock_adapter)
        self.adapter_service = ProviderAdapterService(registry=self.adapter_registry)

        # Resolver and Router setup
        self.resolver_service = CapabilityResolverService(registry=self.model_registry)
        self.router_service = RouterService()

        # Lifecycle repository and service
        self.repository = InMemoryExecutionLifecycleRepository()
        self.service = ExecutionLifecycleService(
            repository=self.repository,
            registry=self.model_registry,
            resolver_service=self.resolver_service,
            router_service=self.router_service,
            adapter_service=self.adapter_service
        )

    def _sample_request(
        self,
        request_id: str = "req_life_01",
        task_id: str = "task_life_01",
        preferred_models: Optional[List[str]] = None,
        min_context: int = 4000
    ) -> ExecutionRequest:
        return ExecutionRequest(
            request_id=request_id,
            task=TaskContext(
                task_id=task_id,
                description="Lifecycle orchestration test task",
                workload_hint="general"
            ),
            request=OperationRequest(
                messages=[{"role": "user", "content": "Run lifecycle test"}],
                parameters={"temperature": 0.5}
            ),
            requirements=ExecutionRequirements(
                min_context_tokens=min_context,
                preferred_models=preferred_models or []
            ),
            execution_context=ExecutionContext(
                session_id="session_life_01",
                workflow_id="wf_life_01"
            )
        )

    def test_01_execution_creation_and_context_association(self) -> None:
        """Verify execution lifecycle record creation with ExecutionContext integration."""
        req = self._sample_request()
        record = self.service.create_execution(req, execution_id="exec_test_01")

        self.assertEqual(record.execution_id, "exec_test_01")
        self.assertEqual(record.request_id, "req_life_01")
        self.assertEqual(record.task_id, "task_life_01")
        self.assertEqual(record.state, LifecycleState.CREATED)
        self.assertIsNotNone(record.context)
        self.assertEqual(record.context.execution_id, "exec_test_01")
        self.assertEqual(record.context.runtime.session_id, "session_life_01")

    def test_02_duplicate_execution_id_prevention(self) -> None:
        """Verify duplicate execution IDs raise ExecutionAlreadyExistsError."""
        req = self._sample_request()
        self.service.create_execution(req, execution_id="exec_dup_01")

        with self.assertRaises(ExecutionAlreadyExistsError):
            self.service.create_execution(req, execution_id="exec_dup_01")

    def test_03_successful_orchestration_flow(self) -> None:
        """Verify complete lifecycle flow from request to COMPLETED result."""
        req = self._sample_request(preferred_models=["mock-pro"])
        result = self.service.execute(req, execution_id="exec_flow_01")

        self.assertIsInstance(result, ExecutionResult)
        self.assertEqual(result.execution_id, "exec_flow_01")
        self.assertEqual(result.request_id, "req_life_01")
        self.assertEqual(result.status, ExecutionStatus.COMPLETED)
        self.assertEqual(result.execution.provider, "mock")
        self.assertEqual(result.execution.model, "mock-pro")
        self.assertEqual(result.response.content, "Deterministic mock completion.")

        # Check stored lifecycle record
        record = self.service.get_execution("exec_flow_01")
        self.assertIsNotNone(record)
        self.assertEqual(record.state, LifecycleState.COMPLETED)
        self.assertIsNotNone(record.classification)
        self.assertIsNotNone(record.resolution)
        self.assertIsNotNone(record.route_decision)
        self.assertEqual(record.target.model_id, "mock-pro")
        self.assertIsNotNone(record.started_at)
        self.assertIsNotNone(record.completed_at)
        self.assertIsNotNone(record.duration_ms)
        self.assertGreater(record.duration_ms, 0.0)

        # Check transition audit trail
        states = [t.to_state for t in record.transitions]
        self.assertIn(LifecycleState.INITIALIZING, states)
        self.assertIn(LifecycleState.ROUTED, states)
        self.assertIn(LifecycleState.RUNNING, states)
        self.assertIn(LifecycleState.COMPLETED, states)

    def test_04_provider_failure_normalization(self) -> None:
        """Verify provider errors are caught, normalized, and transition state to FAILED."""
        def raise_provider_error(r):
            class ProviderRateLimit(Exception):
                status_code = 429
                code = "rate_limit_exceeded"
            return ProviderRateLimit("Rate limit exceeded")

        err_adapter = MockProviderAdapter(
            provider_id="mock_err",
            supported_models=["mock-err-model"],
            error_generator=raise_provider_error
        )
        self.adapter_registry.register(err_adapter)
        self.model_registry.register_provider(ProviderRecord(
            provider_id="mock_err",
            name="Error Mock"
        ))
        self.model_registry.register_model(ModelRecord(
            model_id="mock-err-model",
            provider_id="mock_err",
            name="Error Model"
        ))

        req = self._sample_request(preferred_models=["mock-err-model"])
        result = self.service.execute(req, execution_id="exec_err_01")

        self.assertEqual(result.status, ExecutionStatus.FAILED)
        self.assertIn("Rate limit exceeded", result.error_message)
        self.assertEqual(result.execution.provider, "mock_err")
        self.assertEqual(result.execution.errors_count, 1)

        # Stored lifecycle record should be FAILED
        record = self.service.get_execution("exec_err_01")
        self.assertEqual(record.state, LifecycleState.FAILED)
        self.assertIsNotNone(record.error)
        self.assertTrue(record.error.is_retryable)
        self.assertEqual(record.error.http_status, 429)

    def test_05_no_hidden_provider_fallback(self) -> None:
        """Verify provider failure does not silently switch to fallback target."""
        def raise_fail(r):
            class InternalErr(Exception):
                status_code = 500
            return InternalErr("Provider server error")

        fail_adapter = MockProviderAdapter(
            provider_id="mock_fail",
            supported_models=["mock-fail-model"],
            error_generator=raise_fail
        )
        self.adapter_registry.register(fail_adapter)
        self.model_registry.register_provider(ProviderRecord(
            provider_id="mock_fail",
            name="Failing Provider"
        ))
        self.model_registry.register_model(ModelRecord(
            model_id="mock-fail-model",
            provider_id="mock_fail",
            name="Failing Model"
        ))

        req = self._sample_request(preferred_models=["mock-fail-model"])
        result = self.service.execute(req, execution_id="exec_no_fallback")

        self.assertEqual(result.status, ExecutionStatus.FAILED)
        self.assertEqual(result.execution.provider, "mock_fail")

        record = self.service.get_execution("exec_no_fallback")
        self.assertEqual(record.target.provider_id, "mock_fail")
        self.assertEqual(record.state, LifecycleState.FAILED)

    def test_06_infeasible_capability_resolution_failure(self) -> None:
        """Verify infeasible capability requirements fail cleanly at resolution phase."""
        req = self._sample_request(min_context=99999999)  # Impossible context
        result = self.service.execute(req, execution_id="exec_infeasible_01")

        self.assertEqual(result.status, ExecutionStatus.FAILED)
        self.assertIn("No compatible execution targets found", result.error_message)

        record = self.service.get_execution("exec_infeasible_01")
        self.assertEqual(record.state, LifecycleState.FAILED)
        self.assertEqual(len(record.resolution.compatible_targets), 0)

    def test_07_execution_cancellation(self) -> None:
        """Verify non-terminal execution can be cancelled."""
        req = self._sample_request()
        record = self.service.create_execution(req, execution_id="exec_cancel_01")
        self.assertEqual(record.state, LifecycleState.CREATED)

        cancelled = self.service.cancel_execution("exec_cancel_01", reason="User requested cancel")
        self.assertEqual(cancelled.state, LifecycleState.CANCELLED)
        self.assertEqual(cancelled.cancellation_reason, "User requested cancel")
        self.assertEqual(cancelled.result.status, ExecutionStatus.STOPPED)

    def test_08_cancellation_rejection_for_terminal_execution(self) -> None:
        """Verify attempting to cancel an already completed execution raises error."""
        req = self._sample_request()
        self.service.execute(req, execution_id="exec_terminal_01")

        with self.assertRaises(ExecutionCancellationError):
            self.service.cancel_execution("exec_terminal_01")

    def test_09_invalid_state_transition_in_repository(self) -> None:
        """Verify repository rejects invalid lifecycle state transitions."""
        req = self._sample_request()
        record = self.service.create_execution(req, execution_id="exec_trans_01")

        # Direct invalid jump: CREATED -> COMPLETED (must go through RUNNING)
        with self.assertRaises(InvalidStateTransitionError):
            self.repository.update_state("exec_trans_01", LifecycleState.COMPLETED)

    def test_10_list_executions_with_filtering_and_pagination(self) -> None:
        """Verify listing executions by state with deterministic ordering."""
        req1 = self._sample_request(request_id="req_list_1")
        req2 = self._sample_request(request_id="req_list_2")
        self.service.execute(req1, execution_id="exec_l_1")
        self.service.execute(req2, execution_id="exec_l_2")

        completed = self.service.list_executions(state=LifecycleState.COMPLETED)
        self.assertGreaterEqual(len(completed), 2)
        self.assertEqual(completed[0].state, LifecycleState.COMPLETED)

    def test_11_non_existent_execution_lookup(self) -> None:
        """Verify looking up non-existent execution returns None or raises error."""
        self.assertIsNone(self.service.get_execution("non_existent_id"))
        with self.assertRaises(ExecutionNotFoundError):
            self.service.cancel_execution("non_existent_id")

    def test_12_usage_and_timing_preservation(self) -> None:
        """Verify token usage and round-trip latency are preserved in lifecycle result."""
        req = self._sample_request()
        result = self.service.execute(req, execution_id="exec_usage_01")

        self.assertEqual(result.execution.input_tokens, 150)
        self.assertEqual(result.execution.output_tokens, 45)
        self.assertEqual(result.execution.total_tokens, 195)
        self.assertGreater(result.execution.latency_ms, 0.0)

    def test_13_zero_database_imports_in_lifecycle_package(self) -> None:
        """Verify lifecycle package contains zero database library imports."""
        import infuse.lifecycle
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.lifecycle")]

        forbidden = ["sqlite3", "psycopg2", "asyncpg", "sqlalchemy", "redis", "qdrant_client", "motor", "pymongo"]
        for mod in modules:
            src = inspect.getsource(mod)
            for f in forbidden:
                self.assertNotIn(f"import {f}", src)
                self.assertNotIn(f"from {f}", src)

    def test_14_zero_provider_and_agent_sdk_imports(self) -> None:
        """Verify lifecycle package contains zero real provider/agent SDK imports."""
        import infuse.lifecycle
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.lifecycle")]

        forbidden = ["openai", "anthropic", "google.generativeai", "cohere", "langchain", "crewai", "autogen"]
        for mod in modules:
            src = inspect.getsource(mod)
            for f in forbidden:
                self.assertNotIn(f"import {f}", src)
                self.assertNotIn(f"from {f}", src)

    def test_15_zero_governor_or_pricing_logic_in_lifecycle(self) -> None:
        """Verify lifecycle contains zero Governor decisions, pricing calculations, or health scoring."""
        import infuse.lifecycle
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.lifecycle")]

        forbidden_patterns = [
            "calculate_cost",
            "calculate_price",
            "calculate_margin",
            "issue_action",
            "apply_governance",
            "score_health",
            "probe_health"
        ]
        for mod in modules:
            src = inspect.getsource(mod)
            for p in forbidden_patterns:
                self.assertNotIn(p, src)


if __name__ == "__main__":
    unittest.main()
