"""Comprehensive Unit & Architectural Test Suite for Block 09 Provider & Model Registry."""

import concurrent.futures
import inspect
import sys
import unittest

from infuse.registry.errors import (
    DuplicateModelError,
    DuplicateProviderError,
    ModelNotFoundError,
    ProviderNotFoundError,
    RegistryValidationError,
    SecretDetectedError,
)
from infuse.registry.interfaces import IProviderModelRegistry
from infuse.registry.models import (
    ModelCapabilityDeclaration,
    ModelModality,
    ModelRecord,
    ProviderCapabilityDeclaration,
    ProviderRecord,
    RegistryLifecycleStatus,
)
from infuse.registry.normalization import (
    normalize_model_record,
    normalize_provider_record,
)
from infuse.registry.repository import InMemoryProviderModelRegistry
from infuse.registry.service import ProviderModelService
from infuse.registry.validation import (
    validate_model_record,
    validate_provider_record,
)
from infuse.version import SCHEMA_VERSION


class TestProviderModelRegistry(unittest.TestCase):
    """Test suite verifying Provider & Model Registry validation, normalization, CRUD, and isolation."""

    def setUp(self) -> None:
        self.repo = InMemoryProviderModelRegistry()
        self.service = ProviderModelService(repository=self.repo)

    def _sample_provider(
        self,
        provider_id: str = "anthropic",
        name: str = "Anthropic",
        status: RegistryLifecycleStatus = RegistryLifecycleStatus.ACTIVE
    ) -> ProviderRecord:
        return ProviderRecord(
            provider_id=provider_id,
            name=name,
            description="Leading AI research company.",
            provider_type="cloud",
            endpoint_reference="https://api.anthropic.com",
            capabilities=ProviderCapabilityDeclaration(
                supports_streaming=True,
                supports_tool_calling=True,
                supports_caching=True,
                supports_vision=True,
                supports_structured_output=True,
                supported_protocols=["http", "sse"]
            ),
            status=status
        )

    def _sample_model(
        self,
        model_id: str = "claude-3-7-sonnet",
        provider_id: str = "anthropic",
        name: str = "Claude 3.7 Sonnet",
        context_window: int = 200000,
        max_output_tokens: int = 8192,
        status: RegistryLifecycleStatus = RegistryLifecycleStatus.ACTIVE
    ) -> ModelRecord:
        return ModelRecord(
            model_id=model_id,
            provider_id=provider_id,
            name=name,
            family="claude-3",
            description="Agentic coding and reasoning model.",
            context_window=context_window,
            max_output_tokens=max_output_tokens,
            capabilities=ModelCapabilityDeclaration(
                supports_tools=True,
                supports_vision=True,
                supports_structured_output=True,
                supports_streaming=True,
                supports_caching=True,
                supports_reasoning=True,
                modalities=[ModelModality.TEXT, ModelModality.VISION],
                declared_capabilities=["tools", "vision", "caching", "coding"]
            ),
            status=status
        )

    def test_01_provider_registration_and_retrieval(self) -> None:
        """Verify registering and retrieving a provider record."""
        p = self._sample_provider()
        registered = self.service.register_provider(p)
        self.assertEqual(registered.provider_id, "anthropic")
        self.assertEqual(registered.schema_version, SCHEMA_VERSION)

        fetched = self.service.get_provider("anthropic")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.name, "Anthropic")
        self.assertTrue(fetched.capabilities.supports_tool_calling)

    def test_02_model_registration_and_retrieval(self) -> None:
        """Verify registering and retrieving a model under an existing provider."""
        p = self._sample_provider()
        self.service.register_provider(p)

        m = self._sample_model()
        registered = self.service.register_model(m)
        self.assertEqual(registered.model_id, "claude-3-7-sonnet")
        self.assertEqual(registered.provider_id, "anthropic")

        fetched = self.service.get_model("claude-3-7-sonnet", "anthropic")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.context_window, 200000)
        self.assertTrue(fetched.capabilities.supports_reasoning)

    def test_03_provider_uniqueness_enforcement(self) -> None:
        """Verify duplicate provider registration raises DuplicateProviderError."""
        p = self._sample_provider(provider_id="openai", name="OpenAI")
        self.service.register_provider(p)

        with self.assertRaises(DuplicateProviderError):
            self.service.register_provider(p)

    def test_04_model_uniqueness_under_same_provider(self) -> None:
        """Verify duplicate model registration under same provider raises DuplicateModelError."""
        p = self._sample_provider(provider_id="openai", name="OpenAI")
        self.service.register_provider(p)

        m = self._sample_model(model_id="gpt-4o", provider_id="openai", name="GPT-4o")
        self.service.register_model(m)

        with self.assertRaises(DuplicateModelError):
            self.service.register_model(m)

    def test_05_model_registration_fails_if_provider_missing(self) -> None:
        """Verify registering a model without its parent provider raises ProviderNotFoundError."""
        m = self._sample_model(model_id="gpt-4o", provider_id="non_existent_provider")
        with self.assertRaises(ProviderNotFoundError):
            self.service.register_model(m)

    def test_06_invalid_provider_rejection(self) -> None:
        """Verify empty provider_id or name fails validation."""
        with self.assertRaises(RegistryValidationError):
            p_bad = self._sample_provider(provider_id="  ")
            validate_provider_record(p_bad)

        with self.assertRaises(RegistryValidationError):
            p_bad_name = self._sample_provider(name="")
            validate_provider_record(p_bad_name)

    def test_07_invalid_model_rejection(self) -> None:
        """Verify non-positive context limits or empty IDs fail validation."""
        with self.assertRaises(RegistryValidationError):
            m_bad = self._sample_model(model_id="   ")
            validate_model_record(m_bad)

        # Context window <= 0 caught at model construction or validation
        with self.assertRaises((RegistryValidationError, Exception)):
            self._sample_model(context_window=0)

        with self.assertRaises((RegistryValidationError, Exception)):
            self._sample_model(max_output_tokens=-10)

    def test_08_secret_detection_in_provider_metadata(self) -> None:
        """Verify records containing API keys or credential patterns are strictly rejected."""
        # Forbidden key in metadata
        p_secret_key = self._sample_provider()
        p_secret_key.capabilities.metadata["api_key"] = "any-string"
        with self.assertRaises(SecretDetectedError):
            validate_provider_record(p_secret_key)

        # Token pattern in description
        p_secret_val = self._sample_provider()
        p_secret_val.description = "sk-1234567890abcdefghijklmnop"
        with self.assertRaises(SecretDetectedError):
            validate_provider_record(p_secret_val)

        # Bearer token pattern
        m_secret = self._sample_model()
        m_secret.capabilities.metadata["token"] = "Bearer eyJhbGciOi..."
        with self.assertRaises(SecretDetectedError):
            validate_model_record(m_secret)

    def test_09_deterministic_normalization(self) -> None:
        """Verify whitespace trimming and list deduplication are deterministic."""
        p = self._sample_provider(
            provider_id="  google  ",
            name="  Google Gemini  "
        )
        p.capabilities.supported_protocols = [" HTTP ", "http", "GRPC "]
        norm_p = normalize_provider_record(p)
        self.assertEqual(norm_p.provider_id, "google")
        self.assertEqual(norm_p.name, "Google Gemini")
        self.assertEqual(norm_p.capabilities.supported_protocols, ["http", "grpc"])

        m = self._sample_model(
            model_id=" gemini-2.0-flash ",
            provider_id=" google ",
            name=" Gemini 2.0 Flash "
        )
        m.capabilities.declared_capabilities = [" TOOLS ", "tools", " VISION "]
        norm_m = normalize_model_record(m)
        self.assertEqual(norm_m.model_id, "gemini-2.0-flash")
        self.assertEqual(norm_m.provider_id, "google")
        self.assertEqual(norm_m.name, "Gemini 2.0 Flash")
        self.assertEqual(norm_m.capabilities.declared_capabilities, ["tools", "vision"])

    def test_10_list_providers_and_models_with_status_filter(self) -> None:
        """Verify listing providers and models with status filtering."""
        p1 = self._sample_provider(provider_id="p1", name="P1", status=RegistryLifecycleStatus.ACTIVE)
        p2 = self._sample_provider(provider_id="p2", name="P2", status=RegistryLifecycleStatus.DISABLED)
        self.service.register_provider(p1)
        self.service.register_provider(p2)

        m1 = self._sample_model(model_id="m1", provider_id="p1", status=RegistryLifecycleStatus.ACTIVE)
        m2 = self._sample_model(model_id="m2", provider_id="p1", status=RegistryLifecycleStatus.DEPRECATED)
        self.service.register_model(m1)
        self.service.register_model(m2)

        # Providers
        all_p = self.service.list_providers()
        self.assertEqual(len(all_p), 2)
        active_p = self.service.list_providers(status=RegistryLifecycleStatus.ACTIVE)
        self.assertEqual(len(active_p), 1)
        self.assertEqual(active_p[0].provider_id, "p1")

        # Models
        all_m = self.service.list_models()
        self.assertEqual(len(all_m), 2)
        active_m = self.service.list_models(status=RegistryLifecycleStatus.ACTIVE)
        self.assertEqual(len(active_m), 1)
        self.assertEqual(active_m[0].model_id, "m1")

        # Models for provider
        p1_models = self.service.list_models_for_provider("p1")
        self.assertEqual(len(p1_models), 2)

    def test_11_update_and_delete_operations(self) -> None:
        """Verify updating records and deleting provider cascades to models."""
        p = self._sample_provider()
        self.service.register_provider(p)

        m = self._sample_model()
        self.service.register_model(m)

        # Update model description
        m.description = "Updated description"
        updated_m = self.service.update_model(m)
        self.assertEqual(updated_m.description, "Updated description")

        # Delete provider cascades to models
        deleted = self.service.delete_provider("anthropic")
        self.assertTrue(deleted)
        self.assertIsNone(self.service.get_provider("anthropic"))
        self.assertIsNone(self.service.get_model("claude-3-7-sonnet", "anthropic"))
        self.assertEqual(len(self.service.list_models()), 0)

    def test_12_registry_summary_computation(self) -> None:
        """Verify summary aggregate counts match registered active entities."""
        service = ProviderModelService(seed_defaults=True)
        summary = service.get_summary()

        self.assertGreaterEqual(summary.total_providers, 4)
        self.assertGreaterEqual(summary.active_providers, 4)
        self.assertGreaterEqual(summary.total_models, 4)
        self.assertGreaterEqual(summary.active_models, 4)

    def test_13_immutability_deep_copy_protection(self) -> None:
        """Verify mutating returned records does not corrupt internal storage."""
        p = self._sample_provider()
        self.service.register_provider(p)

        fetched = self.service.get_provider("anthropic")
        fetched.name = "CORRUPTED NAME"
        fetched.capabilities.supports_streaming = False

        fresh = self.service.get_provider("anthropic")
        self.assertEqual(fresh.name, "Anthropic")
        self.assertTrue(fresh.capabilities.supports_streaming)

    def test_14_thread_safe_concurrent_access(self) -> None:
        """Verify thread safety under concurrent read and write operations."""
        p = self._sample_provider()
        self.service.register_provider(p)

        def worker(idx: int):
            m = self._sample_model(
                model_id=f"model_{idx}",
                provider_id="anthropic",
                name=f"Model {idx}"
            )
            self.service.register_model(m)
            _ = self.service.get_model(f"model_{idx}", "anthropic")
            _ = self.service.list_models()

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(worker, i) for i in range(20)]
            for fut in concurrent.futures.as_completed(futures):
                fut.result()

        self.assertEqual(len(self.service.list_models()), 20)

    def test_15_replaceable_repository_boundary(self) -> None:
        """Verify custom repository implementation can be cleanly injected."""
        class MockRepo(IProviderModelRegistry):
            def __init__(self):
                self.p = {}
            def register_provider(self, p):
                self.p[p.provider_id] = p
                return p
            def get_provider(self, p_id):
                return self.p.get(p_id)
            def list_providers(self, status=None):
                return list(self.p.values())
            def update_provider(self, p):
                return p
            def delete_provider(self, p_id):
                return True
            def register_model(self, m):
                return m
            def get_model(self, m_id, provider_id=None):
                return None
            def list_models(self, status=None):
                return []
            def list_models_for_provider(self, p_id, status=None):
                return []
            def update_model(self, m):
                return m
            def delete_model(self, m_id, provider_id=None):
                return True
            def get_summary(self):
                from infuse.registry.models import RegistrySummary
                return RegistrySummary()

        mock_repo = MockRepo()
        svc = ProviderModelService(repository=mock_repo)
        p = self._sample_provider()
        svc.register_provider(p)
        self.assertIsNotNone(svc.get_provider("anthropic"))

    def test_16_zero_forbidden_router_and_ranking_methods(self) -> None:
        """Verify prohibited selection, routing, and ranking methods do not exist."""
        import infuse.registry
        prohibited_methods = ["best_model", "best_provider", "select_model", "route", "rank", "choose"]
        for cls in [InMemoryProviderModelRegistry, ProviderModelService, IProviderModelRegistry]:
            for method in prohibited_methods:
                self.assertFalse(
                    hasattr(cls, method),
                    f"Class {cls.__name__} must not expose prohibited method '{method}'."
                )

    def test_17_zero_database_imports_in_registry_package(self) -> None:
        """Verify registry package contains zero database library imports."""
        import infuse.registry
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.registry")]

        forbidden = ["sqlite3", "psycopg2", "asyncpg", "sqlalchemy", "redis", "qdrant_client", "motor", "pymongo"]
        for mod in modules:
            src = inspect.getsource(mod)
            for f in forbidden:
                self.assertNotIn(f"import {f}", src)
                self.assertNotIn(f"from {f}", src)

    def test_18_zero_provider_and_agent_sdk_imports(self) -> None:
        """Verify registry package contains zero provider or agent SDK imports."""
        import infuse.registry
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.registry")]

        forbidden = ["openai", "anthropic", "google.generativeai", "cohere", "langchain", "crewai", "autogen"]
        for mod in modules:
            src = inspect.getsource(mod)
            for f in forbidden:
                self.assertNotIn(f"import {f}", src)
                self.assertNotIn(f"from {f}", src)

    def test_19_zero_routing_pricing_and_governor_logic(self) -> None:
        """Verify registry contains zero routing decisions, pricing calculations, or Governor logic."""
        import infuse.registry
        modules = [m for name, m in sys.modules.items() if name.startswith("infuse.registry")]

        forbidden_patterns = ["select_provider", "route_request", "decide_action", "apply_governance", "calculate_cost"]
        for mod in modules:
            src = inspect.getsource(mod)
            for p in forbidden_patterns:
                self.assertNotIn(p, src)


if __name__ == "__main__":
    unittest.main()
