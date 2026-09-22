"""Comprehensive Unit & Architectural Test Suite for Block 07 Execution Context."""

import inspect
import sys
import unittest
from starlette.testclient import TestClient

from infuse.api.app import create_app
from infuse.api.services.default import DefaultExecutionService
from infuse.context.builder import ExecutionContextBuilder, create_execution_context
from infuse.context.errors import (
    ExecutionContextError,
    ExecutionContextNotFoundError,
    ExecutionContextValidationError,
)
from infuse.context.interfaces import (
    IExecutionContextRepository,
    IExecutionContextService,
)
from infuse.context.models import (
    AgentContextInfo,
    ConstraintContextInfo,
    ExecutionContextRecord,
    OperationContextInfo,
    PolicyContextInfo,
    RuntimeContextInfo,
    TaskContextInfo,
)
from infuse.context.normalization import normalize_execution_context
from infuse.context.repository import InMemoryExecutionContextRepository
from infuse.context.service import ExecutionContextService
from infuse.context.validation import validate_execution_context
from infuse.contracts.execution import (
    ExecutionContext,
    ExecutionRequest,
    ExecutionRequirements,
    OperationRequest,
    TaskContext,
)
from infuse.contracts.policy import GovernancePolicy
from infuse.version import SCHEMA_VERSION


class TestExecutionContext(unittest.TestCase):
    """Test suite verifying Execution Context creation, validation, immutability, and boundary isolation."""

    def setUp(self) -> None:
        self.repo = InMemoryExecutionContextRepository()
        self.service = ExecutionContextService(repository=self.repo)

    def _sample_execution_request(self) -> ExecutionRequest:
        return ExecutionRequest(
            request_id="req_test_12345",
            task=TaskContext(
                task_id="task_coding_001",
                description="Refactor database layer",
                workload_hint="coding",
                tags=["refactor", "database"],
                metadata={"priority": "high"}
            ),
            request=OperationRequest(
                messages=[{"role": "user", "content": "Refactor the module."}],
                tools=[{"name": "read_file", "description": "Read file contents."}],
                parameters={"temperature": 0.2, "max_tokens": 4096}
            ),
            requirements=ExecutionRequirements(
                min_context_tokens=8192,
                supports_tools=True,
                supports_vision=False,
                supports_structured_output=True,
                preferred_providers=["Anthropic", "OpenAI"],
                excluded_providers=["LegacyProvider"],
                preferred_models=["claude-3-7-sonnet"],
                excluded_models=["gpt-3.5-turbo"]
            ),
            execution_context=ExecutionContext(
                session_id="sess_agent_99",
                workflow_id="wf_dev_pipeline",
                step_index=2,
                isolation_pool="high-security",
                agent_id="code-assistant-v2",
                client_version="1.4.0",
                metadata={"environment": "production", "region": "us-east-1"}
            )
        )

    def test_01_context_creation_from_request(self) -> None:
        """Verify building canonical ExecutionContextRecord from an ExecutionRequest."""
        req = self._sample_execution_request()
        ctx = create_execution_context(req, execution_id="exec_sample_001")

        self.assertEqual(ctx.execution_id, "exec_sample_001")
        self.assertEqual(ctx.request_id, "req_test_12345")
        self.assertEqual(ctx.task.task_id, "task_coding_001")
        self.assertEqual(ctx.task.description, "Refactor database layer")
        self.assertEqual(ctx.task.workload_hint, "coding")
        self.assertEqual(ctx.task.tags, ["refactor", "database"])
        self.assertEqual(ctx.agent.agent_id, "code-assistant-v2")
        self.assertEqual(ctx.runtime.session_id, "sess_agent_99")
        self.assertEqual(ctx.runtime.workflow_id, "wf_dev_pipeline")
        self.assertEqual(ctx.runtime.step_index, 2)
        self.assertEqual(ctx.constraints.min_context_tokens, 8192)
        self.assertTrue(ctx.constraints.supports_tools)
        self.assertTrue(ctx.constraints.supports_structured_output)
        self.assertEqual(ctx.constraints.preferred_providers, ["Anthropic", "OpenAI"])
        self.assertEqual(ctx.operation.message_count, 1)
        self.assertTrue(ctx.operation.has_tools)
        self.assertEqual(ctx.operation.tool_count, 1)
        self.assertEqual(ctx.schema_version, SCHEMA_VERSION)

    def test_02_required_identity_validation(self) -> None:
        """Verify missing execution_id or request_id fails validation."""
        req = self._sample_execution_request()
        builder = ExecutionContextBuilder.from_execution_request(req)
        builder._execution_id = "   "
        with self.assertRaises(ExecutionContextValidationError) as ctx:
            builder.build()
        self.assertTrue(any("execution_id" in v for v in ctx.exception.violations))

        builder.set_identity(execution_id="exec_ok", request_id="")
        with self.assertRaises(ExecutionContextValidationError) as ctx:
            builder.build()
        self.assertTrue(any("request_id" in v for v in ctx.exception.violations))

    def test_03_task_id_required(self) -> None:
        """Verify empty task_id is rejected."""
        builder = ExecutionContextBuilder()
        builder.set_identity(execution_id="exec_1", request_id="req_1")
        builder.set_task(task_id="  ")
        with self.assertRaises(ExecutionContextValidationError) as ctx:
            builder.build()
        self.assertTrue(any("task.task_id" in v for v in ctx.exception.violations))

    def test_04_negative_step_index_rejection(self) -> None:
        """Verify negative step index fails validation."""
        req = self._sample_execution_request()
        builder = ExecutionContextBuilder.from_execution_request(req)
        builder.set_runtime(step_index=-5)
        with self.assertRaises(ExecutionContextValidationError) as ctx:
            builder.build()
        self.assertTrue(any("step_index" in v for v in ctx.exception.violations))

    def test_05_overlapping_provider_constraints_rejection(self) -> None:
        """Verify overlapping preferred and excluded providers fail validation."""
        builder = ExecutionContextBuilder()
        builder.set_identity("exec_1", "req_1")
        builder.set_task("task_1")
        builder.set_constraints(
            preferred_providers=["OpenAI", "Anthropic"],
            excluded_providers=["Anthropic", "Cohere"]
        )
        with self.assertRaises(ExecutionContextValidationError) as ctx:
            builder.build()
        self.assertTrue(any("Providers cannot be both preferred and excluded" in v for v in ctx.exception.violations))

    def test_06_overlapping_model_constraints_rejection(self) -> None:
        """Verify overlapping preferred and excluded models fail validation."""
        builder = ExecutionContextBuilder()
        builder.set_identity("exec_1", "req_1")
        builder.set_task("task_1")
        builder.set_constraints(
            preferred_models=["claude-3-7-sonnet", "gpt-4o"],
            excluded_models=["gpt-4o"]
        )
        with self.assertRaises(ExecutionContextValidationError) as ctx:
            builder.build()
        self.assertTrue(any("Models cannot be both preferred and excluded" in v for v in ctx.exception.violations))

    def test_07_invalid_constraint_ranges_rejection(self) -> None:
        """Verify negative min_context_tokens and non-positive latency are rejected."""
        builder = ExecutionContextBuilder()
        builder.set_identity("exec_1", "req_1")
        builder.set_task("task_1")
        builder.set_constraints(min_context_tokens=-100, max_latency_ms=-5.0)
        with self.assertRaises(ExecutionContextValidationError) as ctx:
            builder.build()
        self.assertEqual(len(ctx.exception.violations), 2)

    def test_08_deterministic_normalization(self) -> None:
        """Verify strings and lists are trimmed and deduplicated deterministically."""
        builder = ExecutionContextBuilder()
        builder.set_identity(execution_id="  exec_norm_1  ", request_id=" req_norm_1 ")
        builder.set_task(
            task_id="  task_norm_1 ",
            description="  Some description  ",
            tags=[" tag1 ", "tag2", "tag1", " "]
        )
        builder.set_constraints(
            preferred_providers=[" Anthropic ", "Anthropic", " OpenAI "]
        )
        ctx = builder.build()

        self.assertEqual(ctx.execution_id, "exec_norm_1")
        self.assertEqual(ctx.request_id, "req_norm_1")
        self.assertEqual(ctx.task.task_id, "task_norm_1")
        self.assertEqual(ctx.task.description, "Some description")
        self.assertEqual(ctx.task.tags, ["tag1", "tag2"])
        self.assertEqual(ctx.constraints.preferred_providers, ["Anthropic", "OpenAI"])

    def test_09_normalization_idempotency(self) -> None:
        """Verify normalizing multiple times produces strictly identical snapshots."""
        req = self._sample_execution_request()
        ctx1 = create_execution_context(req, "exec_idem_1")
        ctx2 = normalize_execution_context(ctx1)
        self.assertEqual(ctx1.model_dump(), ctx2.model_dump())

    def test_10_immutable_snapshot_behavior(self) -> None:
        """Verify callers mutating returned context cannot corrupt storage."""
        req = self._sample_execution_request()
        ctx = self.service.create_context(req, execution_id="exec_tamper_test")

        # Mutate retrieved object
        ctx.task.description = "MALICIOUS OVERWRITE"
        ctx.constraints.preferred_providers.append("UnauthorizedProvider")

        # Re-fetch from service
        fresh = self.service.get_context("exec_tamper_test")
        self.assertIsNotNone(fresh)
        self.assertEqual(fresh.task.description, "Refactor database layer")
        self.assertEqual(fresh.constraints.preferred_providers, ["Anthropic", "OpenAI"])

    def test_11_policy_reference_handling_without_enforcement(self) -> None:
        """Verify policy reference is captured neutrally without executing policy rules."""
        req = self._sample_execution_request()
        req.policy = GovernancePolicy(
            policy_id="pol_custom_inline",
            version="2.1.0",
            name="Inline Policy"
        )
        ctx = create_execution_context(req)
        self.assertEqual(ctx.policy.policy_id, "pol_custom_inline")
        self.assertEqual(ctx.policy.policy_version, "2.1.0")
        self.assertTrue(ctx.policy.has_inline_policy)

    def test_12_context_service_persistence_and_queries(self) -> None:
        """Verify ExecutionContextService stores and queries records by ID, session, and workflow."""
        req = self._sample_execution_request()
        ctx = self.service.create_context(req, execution_id="exec_query_test")

        by_id = self.service.get_context("exec_query_test")
        self.assertIsNotNone(by_id)
        self.assertEqual(by_id.execution_id, "exec_query_test")

        by_session = self.service.list_contexts(session_id="sess_agent_99")
        self.assertEqual(len(by_session), 1)
        self.assertEqual(by_session[0].execution_id, "exec_query_test")

        by_wrong_session = self.service.list_contexts(session_id="sess_non_existent")
        self.assertEqual(len(by_wrong_session), 0)

    def test_13_default_execution_service_integrates_context_boundary(self) -> None:
        """Verify DefaultExecutionService routes requests through the ExecutionContextService."""
        exec_service = DefaultExecutionService(context_service=self.service)
        req = self._sample_execution_request()

        result = exec_service.execute(req)
        self.assertIsNotNone(result.execution_id)
        self.assertEqual(result.request_id, req.request_id)

        # Context record should now exist in the context service
        ctx = self.service.get_context(result.execution_id)
        self.assertIsNotNone(ctx)
        self.assertEqual(ctx.execution_id, result.execution_id)
        self.assertEqual(ctx.request_id, req.request_id)
        self.assertEqual(ctx.task.workload_hint, "coding")

    def test_14_http_post_execute_endpoint_integration(self) -> None:
        """Verify POST /v1/execute establishes ExecutionContext through the context boundary."""
        exec_service = DefaultExecutionService(context_service=self.service)
        app = create_app(execution_service=exec_service)
        client = TestClient(app)

        payload = {
            "request_id": "req_http_exec_1",
            "task": {
                "task_id": "task_http_1",
                "description": "HTTP Task",
                "workload_hint": "research"
            },
            "request": {
                "messages": [{"role": "user", "content": "Analyze system load."}]
            },
            "requirements": {
                "supports_tools": True,
                "preferred_providers": ["Anthropic"]
            },
            "execution_context": {
                "agent_id": "analyst-agent",
                "session_id": "sess_http_99"
            }
        }

        res = client.post("/v1/execute", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        exec_id = data["execution_id"]

        # Verify context record was stored
        ctx = self.service.get_context(exec_id)
        self.assertIsNotNone(ctx)
        self.assertEqual(ctx.task.workload_hint, "research")
        self.assertEqual(ctx.agent.agent_id, "analyst-agent")
        self.assertEqual(ctx.runtime.session_id, "sess_http_99")

    def test_15_parent_execution_relationship(self) -> None:
        """Verify sub-task parent_execution_id is tracked cleanly."""
        req = self._sample_execution_request()
        ctx = create_execution_context(
            req,
            execution_id="exec_child_001",
            parent_execution_id="exec_parent_root"
        )
        self.assertEqual(ctx.execution_id, "exec_child_001")
        self.assertEqual(ctx.parent_execution_id, "exec_parent_root")

    def test_16_repository_replacement_isolation(self) -> None:
        """Verify a custom repository implementation can be cleanly injected."""
        class CustomContextRepo(IExecutionContextRepository):
            def __init__(self):
                self._db = {}
            def save(self, context):
                self._db[context.execution_id] = context
                return context
            def get_by_id(self, execution_id):
                return self._db.get(execution_id)
            def get_by_request_id(self, request_id):
                return None
            def list_all(self, **kwargs):
                return list(self._db.values())
            def count(self, **kwargs):
                return len(self._db)

        custom_repo = CustomContextRepo()
        svc = ExecutionContextService(repository=custom_repo)
        req = self._sample_execution_request()
        ctx = svc.create_context(req, execution_id="exec_custom_repo_1")
        self.assertIsNotNone(svc.get_context("exec_custom_repo_1"))

    def test_17_zero_database_imports_in_context_package(self) -> None:
        """Verify context package contains zero database library imports."""
        import infuse.context
        context_modules = [m for name, m in sys.modules.items() if name.startswith("infuse.context")]

        forbidden = ["sqlite3", "psycopg2", "asyncpg", "sqlalchemy", "redis", "qdrant_client", "motor", "pymongo"]
        for mod in context_modules:
            src = inspect.getsource(mod)
            for f in forbidden:
                self.assertNotIn(f"import {f}", src)
                self.assertNotIn(f"from {f}", src)

    def test_18_zero_provider_and_agent_sdk_imports(self) -> None:
        """Verify context package contains zero provider or agent SDK imports."""
        import infuse.context
        context_modules = [m for name, m in sys.modules.items() if name.startswith("infuse.context")]

        forbidden = ["openai", "anthropic", "google.generativeai", "cohere", "langchain", "crewai", "autogen"]
        for mod in context_modules:
            src = inspect.getsource(mod)
            for f in forbidden:
                self.assertNotIn(f"import {f}", src)
                self.assertNotIn(f"from {f}", src)

    def test_19_zero_workload_classifier_logic_in_context_package(self) -> None:
        """Verify Execution Context contains zero workload classification or scoring algorithms."""
        import infuse.context
        context_modules = [m for name, m in sys.modules.items() if name.startswith("infuse.context")]

        forbidden_patterns = ["classify_workload", "compute_complexity_score", "infer_task_category"]
        for mod in context_modules:
            src = inspect.getsource(mod)
            for p in forbidden_patterns:
                self.assertNotIn(p, src)

    def test_20_zero_router_and_governor_logic_in_context_package(self) -> None:
        """Verify Execution Context contains zero routing or Governor decision logic."""
        import infuse.context
        context_modules = [m for name, m in sys.modules.items() if name.startswith("infuse.context")]

        forbidden_patterns = ["select_provider", "route_request", "decide_action", "apply_governance", "calculate_cost"]
        for mod in context_modules:
            src = inspect.getsource(mod)
            for p in forbidden_patterns:
                self.assertNotIn(p, src)


if __name__ == "__main__":
    unittest.main()
