"""Comprehensive Unit & Integration Test Suite for Block 05 Universal HTTP API."""

import inspect
import sys
import unittest
from starlette.testclient import TestClient

from infuse.api.app import create_app
from infuse.api.errors import ApiError, ErrorCode, NotFoundError
from infuse.api.repositories.interfaces import IExecutionRepository, IPolicyRepository
from infuse.api.repositories.memory import (
    InMemoryExecutionRepository,
    InMemoryPolicyRepository,
)
from infuse.api.services.default import (
    DefaultEventService,
    DefaultExecutionService,
    DefaultPolicyService,
)
from infuse.api.services.interfaces import (
    IEventService,
    IExecutionService,
    IPolicyService,
)
from infuse.contracts.events import EventType, EventSource
from infuse.contracts.execution import ExecutionResult, ExecutionStatus
from infuse.contracts.policy import GovernancePolicy
from infuse.version import SCHEMA_VERSION


class TestUniversalHttpApi(unittest.TestCase):
    """Test suite verifying all Block 05 HTTP API contract behaviors and boundaries."""

    def setUp(self) -> None:
        self.exec_repo = InMemoryExecutionRepository(seed_defaults=True)
        self.policy_repo = InMemoryPolicyRepository(seed_defaults=True)
        self.exec_service = DefaultExecutionService(repository=self.exec_repo)
        self.event_service = DefaultEventService(repository=self.exec_repo)
        self.policy_service = DefaultPolicyService(repository=self.policy_repo)

        self.app = create_app(
            execution_service=self.exec_service,
            event_service=self.event_service,
            policy_service=self.policy_service,
        )
        self.client = TestClient(self.app, raise_server_exceptions=False)

    def test_01_api_application_starts_and_health_routes(self) -> None:
        """Verify API application boots and exposes operational health endpoints."""
        res1 = self.client.get("/health")
        self.assertEqual(res1.status_code, 200)
        data1 = res1.json()
        self.assertEqual(data1["status"], "OK")
        self.assertEqual(data1["schema_version"], SCHEMA_VERSION)
        self.assertIn("X-Correlation-ID", res1.headers)

        res2 = self.client.get("/v1/health")
        self.assertEqual(res2.status_code, 200)
        data2 = res2.json()
        self.assertEqual(data2["status"], "OK")

    def test_02_post_execute_valid_request(self) -> None:
        """Verify POST /v1/execute accepts canonical ExecutionRequest and returns ExecutionResult."""
        payload = {
            "request_id": "req_test_001",
            "task": {
                "task_id": "task_auth_refactor",
                "description": "Refactor JWT middleware",
                "workload_hint": "coding",
                "tags": ["backend", "security"]
            },
            "request": {
                "messages": [{"role": "user", "content": "Refactor JWT auth"}],
                "parameters": {"temperature": 0.2}
            },
            "requirements": {
                "preferred_providers": ["Anthropic"],
                "preferred_models": ["Claude Sonnet"]
            },
            "execution_context": {
                "agent_id": "OpenCode",
                "session_id": "sess_01"
            }
        }
        res = self.client.post("/v1/execute", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertIn("execution_id", data)
        self.assertEqual(data["request_id"], "req_test_001")
        self.assertEqual(data["status"], "COMPLETED")
        self.assertEqual(data["schema_version"], SCHEMA_VERSION)
        self.assertIn("response", data)
        self.assertIn("execution", data)
        self.assertIn("decision", data)

    def test_03_post_execute_response_contract_validation(self) -> None:
        """Verify response from POST /v1/execute strictly deserializes into canonical ExecutionResult."""
        payload = {
            "request_id": "req_test_002",
            "task": {"task_id": "task_math"},
            "request": {"messages": [{"role": "user", "content": "Compute 2+2"}]}
        }
        res = self.client.post("/v1/execute", json=payload)
        self.assertEqual(res.status_code, 200)
        result = ExecutionResult.model_validate(res.json())
        self.assertEqual(result.request_id, "req_test_002")
        self.assertEqual(result.schema_version, SCHEMA_VERSION)

    def test_04_get_executions_list_and_filtering(self) -> None:
        """Verify GET /v1/executions supports listing, counting, and query parameter filtering."""
        res = self.client.get("/v1/executions")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("executions", data)
        self.assertIn("total", data)
        self.assertEqual(data["schema_version"], SCHEMA_VERSION)
        self.assertGreaterEqual(data["total"], 1)

        # Filter by state
        res_filter = self.client.get("/v1/executions?state=COST_PRESSURE")
        self.assertEqual(res_filter.status_code, 200)
        self.assertEqual(res_filter.json()["total"], 1)

        # Filter by agent
        res_agent = self.client.get("/v1/executions?agent=OpenCode")
        self.assertEqual(res_agent.status_code, 200)
        self.assertEqual(res_agent.json()["total"], 1)

        # Pagination validation
        res_bad_limit = self.client.get("/v1/executions?limit=0")
        self.assertEqual(res_bad_limit.status_code, 400)
        self.assertEqual(res_bad_limit.json()["code"], "BAD_REQUEST")

    def test_05_get_execution_by_id_success(self) -> None:
        """Verify GET /v1/executions/{id} returns normalized execution detail."""
        res = self.client.get("/v1/executions/exec_01J8K7A2")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["execution_id"], "exec_01J8K7A2")
        self.assertEqual(data["status"], "RUNNING")
        self.assertEqual(data["execution"]["provider"], "Anthropic")

    def test_06_get_execution_unknown_id_returns_404(self) -> None:
        """Verify GET /v1/executions/{id} with unknown ID returns normalized 404 error."""
        res = self.client.get("/v1/executions/non_existent_exec_999")
        self.assertEqual(res.status_code, 404)
        data = res.json()
        self.assertEqual(data["code"], "NOT_FOUND")
        self.assertIn("non_existent_exec_999", data["message"])
        self.assertEqual(data["schema_version"], SCHEMA_VERSION)
        self.assertIn("correlation_id", data)

    def test_07_post_event_ingestion_success(self) -> None:
        """Verify POST /v1/executions/{id}/events ingests valid events and returns 201."""
        event_payload = {
            "event_id": "evt_test_101",
            "type": "TokenObserved",
            "source": "OBSERVER",
            "sequence": 2,
            "payload": {
                "input_tokens": 1200,
                "output_tokens": 350,
                "cached_tokens": 400,
                "total_tokens": 1550,
                "is_authoritative": True
            }
        }
        res = self.client.post("/v1/executions/exec_01J8K7A2/events", json=event_payload)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["status"], "INGESTED")
        self.assertEqual(data["event_id"], "evt_test_101")
        self.assertEqual(data["execution_id"], "exec_01J8K7A2")
        self.assertEqual(data["schema_version"], SCHEMA_VERSION)

        # Verify event was stored in repository
        stored_events = self.exec_repo.get_events("exec_01J8K7A2")
        self.assertTrue(any(e.event_id == "evt_test_101" for e in stored_events))

    def test_08_post_event_unknown_execution_returns_404(self) -> None:
        """Verify event ingestion to unknown execution returns normalized 404."""
        event_payload = {
            "event_id": "evt_orphan_01",
            "type": "ToolCalled",
            "sequence": 1,
            "payload": {"tool_name": "grep_codebase"}
        }
        res = self.client.post("/v1/executions/unknown_exec_xyz/events", json=event_payload)
        self.assertEqual(res.status_code, 404)
        self.assertEqual(res.json()["code"], "NOT_FOUND")

    def test_09_post_event_invalid_schema_returns_422(self) -> None:
        """Verify invalid event schema (missing sequence or invalid type) is rejected with 422."""
        bad_event = {
            "event_id": "evt_bad_01",
            "type": "INVALID_EVENT_TYPE",
            "sequence": "not_an_integer"
        }
        res = self.client.post("/v1/executions/exec_01J8K7A2/events", json=bad_event)
        self.assertEqual(res.status_code, 422)
        data = res.json()
        self.assertEqual(data["code"], "VALIDATION_ERROR")
        self.assertIn("details", data)

    def test_10_get_policies_list(self) -> None:
        """Verify GET /v1/policies returns active policy and all revisions."""
        res = self.client.get("/v1/policies")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("policies", data)
        self.assertIn("active_policy", data)
        self.assertEqual(data["active_policy"]["policy_id"], "pol_default")
        self.assertEqual(data["schema_version"], SCHEMA_VERSION)

    def test_11_put_policy_update_success(self) -> None:
        """Verify PUT /v1/policies/{id} validates and updates policy."""
        updated_payload = {
            "policy_id": "pol_default",
            "name": "Custom Production Policy",
            "version": "1.1.0",
            "is_active": True,
            "budget": {
                "max_cost_per_task": 15.0,
                "currency": "USD"
            },
            "tokens": {
                "max_total_tokens": 100000
            }
        }
        res = self.client.put("/v1/policies/pol_default", json=updated_payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["name"], "Custom Production Policy")
        self.assertEqual(data["budget"]["max_cost_per_task"], 15.0)

        # Verify active policy in service updated
        active = self.policy_service.get_active_policy()
        self.assertEqual(active.name, "Custom Production Policy")
        self.assertEqual(active.budget.max_cost_per_task, 15.0)

    def test_12_put_policy_invalid_schema_returns_422(self) -> None:
        """Verify invalid policy payload returns 422."""
        invalid_payload = {
            "policy_id": "pol_bad",
            "budget": {
                "max_cost_per_task": "not_a_number"
            }
        }
        res = self.client.put("/v1/policies/pol_bad", json=invalid_payload)
        self.assertEqual(res.status_code, 422)
        self.assertEqual(res.json()["code"], "VALIDATION_ERROR")

    def test_13_malformed_json_body_returns_400(self) -> None:
        """Verify malformed JSON strings return 400 with MALFORMED_JSON code."""
        headers = {"Content-Type": "application/json"}
        res = self.client.post("/v1/execute", content="{malformed_json: true,", headers=headers)
        self.assertEqual(res.status_code, 400)
        data = res.json()
        self.assertEqual(data["code"], "MALFORMED_JSON")
        self.assertEqual(data["schema_version"], SCHEMA_VERSION)

    def test_14_non_object_json_body_returns_422(self) -> None:
        """Verify non-dictionary JSON payloads return 422."""
        res = self.client.post("/v1/execute", json=["array_not_object"])
        self.assertEqual(res.status_code, 422)
        self.assertEqual(res.json()["code"], "VALIDATION_ERROR")

    def test_15_correlation_id_propagation(self) -> None:
        """Verify caller-provided X-Correlation-ID is preserved and returned in response."""
        custom_corr_id = "corr_custom_trace_9999"
        res = self.client.get("/v1/executions", headers={"X-Correlation-ID": custom_corr_id})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("X-Correlation-ID"), custom_corr_id)

    def test_16_unexpected_internal_exception_handling(self) -> None:
        """Verify unexpected service exception returns sanitized 500 without leaking stack traces."""
        class ExplodingExecutionService(IExecutionService):
            def execute(self, request):
                raise RuntimeError("Sensitive internal database connection string: db://user:secret@host")
            def get_execution(self, execution_id):
                raise RuntimeError("Crash")
            def list_executions(self, **kwargs):
                raise RuntimeError("Crash")

        exploding_app = create_app(execution_service=ExplodingExecutionService())
        client = TestClient(exploding_app, raise_server_exceptions=False)

        payload = {
            "request_id": "req_crash",
            "task": {"task_id": "t1"},
            "request": {"messages": []}
        }
        res = client.post("/v1/execute", json=payload)
        self.assertEqual(res.status_code, 500)
        data = res.json()
        self.assertEqual(data["code"], "INTERNAL_ERROR")
        # Ensure sensitive exception details / stack traces are not leaked to caller
        self.assertNotIn("db://user:secret@host", data["message"])
        self.assertNotIn("Traceback", data["message"])
        self.assertEqual(data["message"], "An unexpected internal server error occurred.")

    def test_17_service_boundary_isolation(self) -> None:
        """Verify custom service implementation can be injected into create_app without modifying routes."""
        class MockExecutionService(IExecutionService):
            def execute(self, request):
                return ExecutionResult(
                    execution_id="exec_custom_service_001",
                    request_id=request.request_id,
                    status=ExecutionStatus.RUNNING
                )
            def get_execution(self, execution_id):
                return None
            def list_executions(self, **kwargs):
                return {"executions": [], "total": 0, "schema_version": SCHEMA_VERSION}

        custom_app = create_app(execution_service=MockExecutionService())
        client = TestClient(custom_app)
        res = client.post("/v1/execute", json={
            "request_id": "req_custom",
            "task": {"task_id": "task_1"},
            "request": {"messages": []}
        })
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["execution_id"], "exec_custom_service_001")

    def test_18_repository_boundary_isolation(self) -> None:
        """Verify repository interface can be customized without touching API routes or services."""
        custom_repo = InMemoryExecutionRepository(seed_defaults=False)
        self.assertEqual(custom_repo.count(), 0)

        service = DefaultExecutionService(repository=custom_repo)
        app = create_app(execution_service=service)
        client = TestClient(app)

        res = client.get("/v1/executions")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["total"], 0)

    def test_19_zero_database_dependency(self) -> None:
        """Verify API module contains zero database library imports (sqlite3, sqlalchemy, pg, etc.)."""
        import infuse.api
        api_modules = [m for name, m in sys.modules.items() if name.startswith("infuse.api")]

        forbidden = ["sqlite3", "psycopg2", "asyncpg", "sqlalchemy", "redis", "qdrant_client", "motor", "pymongo"]
        for mod in api_modules:
            src = inspect.getsource(mod)
            for f in forbidden:
                self.assertNotIn(f"import {f}", src)
                self.assertNotIn(f"from {f}", src)

    def test_20_zero_provider_sdk_dependency(self) -> None:
        """Verify API module contains zero provider SDK imports (openai, anthropic, google.generativeai, etc.)."""
        import infuse.api
        api_modules = [m for name, m in sys.modules.items() if name.startswith("infuse.api")]

        forbidden = ["openai", "anthropic", "google.generativeai", "cohere", "mistralai", "bedrock"]
        for mod in api_modules:
            src = inspect.getsource(mod)
            for f in forbidden:
                self.assertNotIn(f"import {f}", src)
                self.assertNotIn(f"from {f}", src)

    def test_21_zero_agent_sdk_dependency(self) -> None:
        """Verify API module contains zero agent framework imports (langchain, crewai, autogen, etc.)."""
        import infuse.api
        api_modules = [m for name, m in sys.modules.items() if name.startswith("infuse.api")]

        forbidden = ["langchain", "crewai", "autogen", "semantic_kernel", "langgraph"]
        for mod in api_modules:
            src = inspect.getsource(mod)
            for f in forbidden:
                self.assertNotIn(f"import {f}", src)
                self.assertNotIn(f"from {f}", src)

    def test_22_zero_governor_enforcement_logic_in_api(self) -> None:
        """Verify API transport layer does not perform autonomous Governor decision enforcement."""
        from infuse.api.routes import execute, executions, policies
        for mod in [execute, executions, policies]:
            src = inspect.getsource(mod)
            self.assertNotIn("enforce_policy", src)
            self.assertNotIn("calculate_throttle", src)
            self.assertNotIn("circuit_breaker", src)

    def test_23_zero_policy_manager_enforcement_in_api(self) -> None:
        """Verify API layer does not evaluate policy rules or block requests autonomously."""
        from infuse.api.routes import execute, executions, policies
        for mod in [execute, executions, policies]:
            src = inspect.getsource(mod)
            self.assertNotIn("evaluate_policy", src)
            self.assertNotIn("check_budget_exhaustion", src)

    def test_24_zero_provider_selection_or_ranking_in_api(self) -> None:
        """Verify API transport layer contains zero provider scoring or ranking algorithms."""
        from infuse.api.routes import execute, executions, policies
        for mod in [execute, executions, policies]:
            src = inspect.getsource(mod)
            self.assertNotIn("rank_providers", src)
            self.assertNotIn("select_best_model", src)

    def test_25_zero_pricing_calculation_in_api(self) -> None:
        """Verify API transport layer contains zero financial/token pricing formulas."""
        from infuse.api.routes import execute, executions, policies
        for mod in [execute, executions, policies]:
            src = inspect.getsource(mod)
            self.assertNotIn("cost_per_token", src)
            self.assertNotIn("compute_cost", src)


if __name__ == "__main__":
    unittest.main()
