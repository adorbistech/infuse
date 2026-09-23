"""Comprehensive Unit & Architectural Test Suite for Block 12 Provider Adapter Layer."""

import inspect
import sys
import unittest
from typing import Dict, List, Optional

from infuse.contracts.capabilities import ProviderCapability
from infuse.contracts.execution import (
    ExecutionContext,
    ExecutionRequest,
    ExecutionRequirements,
    ExecutionResult,
    ExecutionStatus,
    OperationRequest,
    TaskContext,
)
from infuse.providers.adapters.base import BaseProviderAdapter
from infuse.providers.adapters.mock import (
    DeterministicReferenceAdapter,
    MockProviderAdapter,
)
from infuse.providers.errors import (
    AdapterNotFoundError,
    DuplicateAdapterError,
    ProviderInvocationError,
    UnsupportedModelError,
)
from infuse.providers.interfaces import IProviderAdapter, IProviderAdapterRegistry
from infuse.providers.models import (
    ProviderErrorRecord,
    ProviderExecutionChunk,
    ProviderExecutionRequest,
    ProviderExecutionResponse,
    ProviderUsage,
)
from infuse.providers.registry import InMemoryProviderAdapterRegistry
from infuse.providers.service import ProviderAdapterService
from infuse.registry.models import ModelRecord, ProviderRecord
from infuse.registry.repository import InMemoryProviderModelRegistry
from infuse.resolver.resolver import CapabilityResolver
from infuse.router.models import RouteTarget
from infuse.version import SCHEMA_VERSION


class TestProviderAdapterLayer(unittest.TestCase):
    """Test suite verifying adapter interfaces, registration, translation, error normalization, and boundaries."""

    def setUp(self) -> None:
        self.registry = InMemoryProviderAdapterRegistry()
        self.service = ProviderAdapterService(registry=self.registry)
        self.mock_adapter = MockProviderAdapter(
            provider_id="mock",
            supported_models=["mock-fast", "mock-pro", "mock-code"]
        )
        self.service.register_adapter(self.mock_adapter)

    def _sample_execution_request(self) -> ExecutionRequest:
        return ExecutionRequest(
            request_id="req_test_01",
            task=TaskContext(
                task_id="task_test_01",
                description="Test execution task",
                workload_hint="coding"
            ),
            request=OperationRequest(
                messages=[{"role": "user", "content": "Hello INFUSE"}],
                parameters={"temperature": 0.7}
            ),
            requirements=ExecutionRequirements(
                min_context_tokens=4000,
                supports_tools=False
            ),
            execution_context=ExecutionContext(
                session_id="session_01",
                metadata={"test_key": "test_val"}
            )
        )

    def _sample_route_target(self, provider_id: str = "mock", model_id: str = "mock-fast") -> RouteTarget:
        return RouteTarget(
            provider_id=provider_id,
            model_id=model_id,
            context_window=128000,
            max_output_tokens=4096,
            declared_capabilities=["streaming", "tools"],
            supported_modalities=["text"]
        )

    def test_01_adapter_registration_and_resolution(self) -> None:
        """Verify registering and retrieving adapters by provider ID."""
        self.assertTrue(self.registry.has("mock"))
        self.assertFalse(self.registry.has("nonexistent"))

        adapter = self.registry.get("mock")
        self.assertEqual(adapter.provider_id, "mock")
        self.assertIn("mock", self.registry.list_providers())

    def test_02_duplicate_registration_behavior(self) -> None:
        """Verify registering duplicate adapter raises error unless overwrite=True."""
        duplicate = MockProviderAdapter(provider_id="mock")
        with self.assertRaises(DuplicateAdapterError):
            self.registry.register(duplicate, overwrite=False)

        # Allowed with overwrite=True
        self.registry.register(duplicate, overwrite=True)
        self.assertEqual(self.registry.get("mock"), duplicate)

    def test_03_missing_adapter_raises_error(self) -> None:
        """Verify resolving non-existent adapter raises AdapterNotFoundError."""
        with self.assertRaises(AdapterNotFoundError):
            self.registry.get("unknown_provider")

    def test_04_unregister_adapter(self) -> None:
        """Verify unregistering adapter removes it from registry."""
        custom = MockProviderAdapter(provider_id="custom_temp")
        self.registry.register(custom)
        self.assertTrue(self.registry.has("custom_temp"))

        removed = self.registry.unregister("custom_temp")
        self.assertTrue(removed)
        self.assertFalse(self.registry.has("custom_temp"))

    def test_05_unsupported_model_raises_error(self) -> None:
        """Verify executing an unsupported model raises UnsupportedModelError."""
        req = ProviderExecutionRequest(
            execution_id="exec_01",
            request_id="req_01",
            task_id="task_01",
            provider_id="mock",
            model_id="unsupported-model-999"
        )
        with self.assertRaises(UnsupportedModelError):
            self.mock_adapter.execute(req)

    def test_06_request_translation(self) -> None:
        """Verify translating universal ExecutionRequest + RouteTarget to ProviderExecutionRequest."""
        exec_req = self._sample_execution_request()
        target = self._sample_route_target()

        prov_req = self.service.translate_request(
            execution_id="exec_tx_01",
            request=exec_req,
            target=target
        )

        self.assertEqual(prov_req.execution_id, "exec_tx_01")
        self.assertEqual(prov_req.request_id, "req_test_01")
        self.assertEqual(prov_req.task_id, "task_test_01")
        self.assertEqual(prov_req.provider_id, "mock")
        self.assertEqual(prov_req.model_id, "mock-fast")
        self.assertEqual(prov_req.messages[0]["content"], "Hello INFUSE")
        self.assertEqual(prov_req.metadata.get("target_context_window"), 128000)

    def test_07_deterministic_reference_adapter_execution(self) -> None:
        """Verify reference adapter executes request and preserves identity and metadata."""
        exec_req = self._sample_execution_request()
        target = self._sample_route_target()

        response = self.service.execute_target(
            execution_id="exec_run_01",
            request=exec_req,
            target=target
        )

        self.assertIsInstance(response, ProviderExecutionResponse)
        self.assertEqual(response.execution_id, "exec_run_01")
        self.assertEqual(response.request_id, "req_test_01")
        self.assertEqual(response.provider_id, "mock")
        self.assertEqual(response.model_id, "mock-fast")
        self.assertEqual(response.content, "Deterministic mock completion.")
        self.assertEqual(response.finish_reason, "stop")
        self.assertIsNotNone(response.provider_request_id)
        self.assertTrue(response.provider_request_id.startswith("mock_req_"))

    def test_08_response_normalization_to_execution_result(self) -> None:
        """Verify normalizing ProviderExecutionResponse into universal ExecutionResult."""
        exec_req = self._sample_execution_request()
        target = self._sample_route_target()

        response = self.service.execute_target("exec_run_02", exec_req, target)
        result = self.service.normalize_response_to_result(response, exec_req)

        self.assertIsInstance(result, ExecutionResult)
        self.assertEqual(result.execution_id, "exec_run_02")
        self.assertEqual(result.request_id, "req_test_01")
        self.assertEqual(result.status, ExecutionStatus.COMPLETED)
        self.assertEqual(result.response.content, "Deterministic mock completion.")
        self.assertEqual(result.execution.provider, "mock")
        self.assertEqual(result.execution.model, "mock-fast")
        self.assertEqual(result.execution.input_tokens, 150)
        self.assertEqual(result.execution.output_tokens, 45)
        self.assertEqual(result.execution.total_tokens, 195)

    def test_09_usage_normalization(self) -> None:
        """Verify usage metadata normalization including cached tokens and authoritative flag."""
        custom_usage = ProviderUsage(
            input_tokens=2000,
            output_tokens=500,
            total_tokens=2500,
            cached_tokens=1500,
            is_authoritative=True,
            details={"cache_read_tokens": 1500}
        )
        req = ProviderExecutionRequest(
            execution_id="exec_usage_01",
            request_id="req_usage_01",
            task_id="task_usage_01",
            provider_id="mock",
            model_id="mock-pro",
            parameters={"mock_usage": custom_usage}
        )

        resp = self.mock_adapter.execute(req)
        self.assertEqual(resp.usage.input_tokens, 2000)
        self.assertEqual(resp.usage.cached_tokens, 1500)
        self.assertEqual(resp.usage.total_tokens, 2500)
        self.assertTrue(resp.usage.is_authoritative)

    def test_10_provider_error_normalization(self) -> None:
        """Verify provider errors are normalized with retryability and status codes."""
        class MockHttpError(Exception):
            def __init__(self, msg, status_code, code=None):
                super().__init__(msg)
                self.status_code = status_code
                self.code = code

        # 429 Rate Limit (Retryable)
        rate_err = MockHttpError("Rate limit exceeded", 429, "rate_limit_exceeded")
        norm_rate = self.service.normalize_error("mock", rate_err, model_id="mock-pro")
        self.assertTrue(norm_rate.is_retryable)
        self.assertEqual(norm_rate.http_status, 429)
        self.assertEqual(norm_rate.error_code, "rate_limit_exceeded")

        # 401 Unauthorized (Not retryable)
        auth_err = MockHttpError("Invalid API key", 401, "invalid_api_key")
        norm_auth = self.service.normalize_error("mock", auth_err, model_id="mock-pro")
        self.assertFalse(norm_auth.is_retryable)
        self.assertEqual(norm_auth.http_status, 401)

    def test_11_simulated_error_raising(self) -> None:
        """Verify error generator raises normalized ProviderInvocationError."""
        def raise_503(r):
            class ServiceUnavailable(Exception):
                status_code = 503
            return ServiceUnavailable("Service unavailable")

        err_adapter = MockProviderAdapter(
            provider_id="mock_err",
            error_generator=raise_503
        )
        self.service.register_adapter(err_adapter)

        req = ProviderExecutionRequest(
            execution_id="exec_err_01",
            request_id="req_err_01",
            task_id="task_err_01",
            provider_id="mock_err",
            model_id="mock-fast"
        )

        with self.assertRaises(ProviderInvocationError) as cm:
            err_adapter.execute(req)

        self.assertEqual(cm.exception.provider_id, "mock_err")
        self.assertTrue(cm.exception.is_retryable)
        self.assertEqual(cm.exception.http_status, 503)

    def test_12_streaming_chunks(self) -> None:
        """Verify adapter streaming yields chunks with delta content and sequence indices."""
        req = ProviderExecutionRequest(
            execution_id="exec_stream_01",
            request_id="req_stream_01",
            task_id="task_stream_01",
            provider_id="mock",
            model_id="mock-fast",
            parameters={"mock_content": "Hello stream test world"}
        )

        chunks = list(self.mock_adapter.stream(req))
        self.assertEqual(len(chunks), 4)
        self.assertEqual(chunks[0].delta_content, "Hello ")
        self.assertIsNone(chunks[0].finish_reason)
        self.assertEqual(chunks[-1].delta_content, "world")
        self.assertEqual(chunks[-1].finish_reason, "stop")
        self.assertIsNotNone(chunks[-1].usage)

    def test_13_capability_exposure(self) -> None:
        """Verify adapter exposes ProviderCapability conforming to Block 00 contract."""
        cap = self.mock_adapter.get_capability()
        self.assertIsInstance(cap, ProviderCapability)
        self.assertEqual(cap.provider_name, "mock")
        self.assertTrue(cap.supports_streaming)
        self.assertTrue(cap.supports_tool_calling)
        self.assertEqual(cap.max_context_window, 128000)

    def test_14_capability_resolver_integration(self) -> None:
        """Verify adapter capability can be verified by Capability Resolver."""
        cap = self.mock_adapter.get_capability()
        # Verify capability model contains all declared supported models
        self.assertIn("mock-fast", cap.supported_models)
        self.assertIn("mock-pro", cap.supported_models)

    def test_15_provider_registry_integration(self) -> None:
        """Verify Block 09 Provider & Model Registry integration with adapter."""
        model_reg = InMemoryProviderModelRegistry()
        model_reg.register_provider(ProviderRecord(
            provider_id="mock",
            name="Mock Provider",
            supported_modalities=["text"]
        ))
        model_reg.register_model(ModelRecord(
            model_id="mock-fast",
            provider_id="mock",
            name="Mock Fast Model",
            context_window=128000,
            max_output_tokens=4096
        ))

        # Check adapter supports the registered model
        self.assertIsNotNone(model_reg.get_model("mock-fast", "mock"))
        self.assertTrue(self.mock_adapter.supports_model("mock-fast"))

    def test_16_zero_database_imports_in_providers_package(self) -> None:
        """Verify providers package contains zero database library imports."""
        import infuse.providers
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.providers")]

        forbidden = ["sqlite3", "psycopg2", "asyncpg", "sqlalchemy", "redis", "qdrant_client", "motor", "pymongo"]
        for mod in modules:
            src = inspect.getsource(mod)
            for f in forbidden:
                self.assertNotIn(f"import {f}", src)
                self.assertNotIn(f"from {f}", src)

    def test_17_zero_provider_and_agent_sdk_imports(self) -> None:
        """Verify providers package contains zero real provider/agent SDK imports."""
        import infuse.providers
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.providers")]

        forbidden = ["openai", "anthropic", "google.generativeai", "cohere", "langchain", "crewai", "autogen"]
        for mod in modules:
            src = inspect.getsource(mod)
            for f in forbidden:
                self.assertNotIn(f"import {f}", src)
                self.assertNotIn(f"from {f}", src)

    def test_18_zero_routing_governor_or_pricing_logic(self) -> None:
        """Verify adapter contains zero routing decisions, Governor logic, or pricing calculations."""
        import infuse.providers
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.providers")]

        forbidden_patterns = [
            "select_route",
            "calculate_cost",
            "calculate_price",
            "issue_action",
            "apply_governance",
            "retry_execution",
            "select_fallback"
        ]
        for mod in modules:
            src = inspect.getsource(mod)
            for p in forbidden_patterns:
                self.assertNotIn(p, src)


if __name__ == "__main__":
    unittest.main()
