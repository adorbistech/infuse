"""Comprehensive Unit & Architectural Test Suite for Block 06 Policy Manager."""

import copy
import inspect
import sys
import unittest
from starlette.testclient import TestClient

from infuse.api.app import create_app
from infuse.api.repositories.interfaces import IPolicyRepository
from infuse.api.repositories.memory import InMemoryPolicyRepository
from infuse.api.services.default import DefaultPolicyService
from infuse.contracts.governor import GovernorAction
from infuse.contracts.policy import (
    BudgetControls,
    GovernancePolicy,
    PolicyActionBindings,
    ProviderAccessControls,
    RequestControls,
    RetryPolicy,
    RuntimeControls,
    TokenControls,
    ToolAccessControls,
    WebAccessControls,
)
from infuse.policy.errors import (
    PolicyConflictError,
    PolicyManagerError,
    PolicyNotFoundError,
    PolicyValidationError,
)
from infuse.policy.interfaces import IPolicyManager
from infuse.policy.manager import PolicyManager
from infuse.policy.normalization import normalize_policy
from infuse.policy.validation import validate_policy
from infuse.version import SCHEMA_VERSION


class TestPolicyManager(unittest.TestCase):
    """Test suite verifying Policy Manager lifecycle, validation, versioning, and boundaries."""

    def setUp(self) -> None:
        self.repo = InMemoryPolicyRepository(seed_defaults=True)
        self.manager = PolicyManager(repository=self.repo)

    def test_01_initialization(self) -> None:
        """Verify Policy Manager initializes cleanly with repository dependency."""
        self.assertIsNotNone(self.manager)
        active = self.manager.get_active_policy()
        self.assertIsNotNone(active)
        self.assertEqual(active.policy_id, "pol_default")

    def test_02_create_valid_policy(self) -> None:
        """Verify creation of a valid policy persists and is retrievable."""
        policy = GovernancePolicy(
            policy_id="pol_prod_01",
            name="Production Tier Policy",
            version="1.0.0",
            budget=BudgetControls(max_cost_per_task=25.0, currency="USD"),
            tokens=TokenControls(max_total_tokens=150000)
        )
        created = self.manager.create_policy(policy)
        self.assertEqual(created.policy_id, "pol_prod_01")
        self.assertEqual(created.version, "1.0.0")

        retrieved = self.manager.get_policy("pol_prod_01")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "Production Tier Policy")
        self.assertEqual(retrieved.budget.max_cost_per_task, 25.0)

    def test_03_reject_invalid_policy_empty_id(self) -> None:
        """Verify policy with empty or whitespace policy_id is rejected."""
        policy = GovernancePolicy(policy_id="   ", name="Empty ID Policy")
        with self.assertRaises(PolicyValidationError) as ctx:
            self.manager.create_policy(policy)
        self.assertTrue(any("policy_id" in v for v in ctx.exception.violations))

    def test_04_canonical_schema_validation(self) -> None:
        """Verify all 10 governance sections adhere to canonical constraints."""
        policy = GovernancePolicy(
            policy_id="pol_canonical",
            name="Canonical Policy",
            budget=BudgetControls(max_cost_per_task=10.0, max_cost_per_day=50.0, max_cost_per_month=500.0),
            tokens=TokenControls(max_input_tokens=20000, max_output_tokens=10000, max_total_tokens=30000),
            requests=RequestControls(max_rpm=60, max_requests_per_task=20),
            runtime=RuntimeControls(max_execution_time_seconds=300),
            providers=ProviderAccessControls(allowed_providers=["Anthropic", "OpenAI"]),
            web=WebAccessControls(enabled=True, max_web_requests_per_task=5),
            tools=ToolAccessControls(enabled=True, max_tool_calls_per_task=15),
            retries=RetryPolicy(max_retries=3, backoff_factor=2.0),
            actions=PolicyActionBindings(budget_action=GovernorAction.THROTTLE)
        )
        created = self.manager.create_policy(policy)
        self.assertEqual(created.policy_id, "pol_canonical")

    def test_05_schema_version_preserved(self) -> None:
        """Verify schema_version is normalized to canonical '1.0.0'."""
        policy = GovernancePolicy(policy_id="pol_version_check", name="Ver Check")
        created = self.manager.create_policy(policy)
        self.assertEqual(created.schema_version, SCHEMA_VERSION)

    def test_06_normalization_strings_and_lists(self) -> None:
        """Verify normalization trims strings, converts currency to uppercase, and deduplicates lists."""
        policy = GovernancePolicy(
            policy_id="  pol_norm_test  ",
            name="  Un-trimmed Name  ",
            budget=BudgetControls(currency="  eur  "),
            providers=ProviderAccessControls(
                allowed_providers=["Anthropic", " Anthropic ", "OpenAI", ""]
            ),
            web=WebAccessControls(
                allowed_domains=[" adorbis.com ", "adorbis.com", "api.github.com "]
            )
        )
        norm = normalize_policy(policy)
        self.assertEqual(norm.policy_id, "pol_norm_test")
        self.assertEqual(norm.name, "Un-trimmed Name")
        self.assertEqual(norm.budget.currency, "EUR")
        self.assertEqual(norm.providers.allowed_providers, ["Anthropic", "OpenAI"])
        self.assertEqual(norm.web.allowed_domains, ["adorbis.com", "api.github.com"])

    def test_07_deterministic_normalization(self) -> None:
        """Verify normalizing multiple times yields idempotent and identical results."""
        policy = GovernancePolicy(
            policy_id="pol_idem",
            name="Idempotent Policy",
            budget=BudgetControls(currency="usd"),
            providers=ProviderAccessControls(allowed_providers=["A", "B", "A"])
        )
        norm1 = normalize_policy(policy)
        norm2 = normalize_policy(norm1)
        self.assertEqual(norm1.model_dump(), norm2.model_dump())

    def test_08_duplicate_creation_rejected_conflict(self) -> None:
        """Verify creating a policy with existing ID raises PolicyConflictError."""
        policy = GovernancePolicy(policy_id="pol_dup", name="Original")
        self.manager.create_policy(policy)

        with self.assertRaises(PolicyConflictError):
            self.manager.create_policy(policy)

    def test_09_policy_update_creates_new_revision(self) -> None:
        """Verify updating a policy creates a new incremented revision and preserves history."""
        policy = GovernancePolicy(
            policy_id="pol_evolving",
            name="Evolving Policy V1",
            version="1.0.0",
            budget=BudgetControls(max_cost_per_task=5.0)
        )
        self.manager.create_policy(policy)

        # Update policy
        updated = self.manager.update_policy(
            "pol_evolving",
            GovernancePolicy(
                policy_id="pol_evolving",
                name="Evolving Policy V2",
                version="1.0.0",  # Same initial version, PolicyManager should auto-bump
                budget=BudgetControls(max_cost_per_task=10.0)
            )
        )
        self.assertEqual(updated.version, "1.0.1")
        self.assertEqual(updated.budget.max_cost_per_task, 10.0)

        # Latest policy is 1.0.1
        latest = self.manager.get_policy("pol_evolving")
        self.assertEqual(latest.version, "1.0.1")
        self.assertEqual(latest.budget.max_cost_per_task, 10.0)

    def test_10_historical_revision_remains_immutable(self) -> None:
        """Verify previous historical revision remains untouched after update."""
        policy = GovernancePolicy(
            policy_id="pol_immutable_test",
            name="Immutable Baseline",
            version="1.0.0",
            budget=BudgetControls(max_cost_per_task=5.0)
        )
        self.manager.create_policy(policy)

        # Retrieve v1.0.0
        v1 = self.manager.get_policy("pol_immutable_test", version="1.0.0")
        self.assertEqual(v1.budget.max_cost_per_task, 5.0)

        # Update to v1.0.1
        self.manager.update_policy(
            "pol_immutable_test",
            GovernancePolicy(
                policy_id="pol_immutable_test",
                name="Updated Revision",
                budget=BudgetControls(max_cost_per_task=50.0)
            )
        )

        # Historical v1.0.0 must still have max_cost_per_task == 5.0
        v1_after = self.manager.get_policy("pol_immutable_test", version="1.0.0")
        self.assertEqual(v1_after.budget.max_cost_per_task, 5.0)
        self.assertEqual(v1_after.name, "Immutable Baseline")

    def test_11_caller_mutation_does_not_corrupt_storage(self) -> None:
        """Verify modifying a returned policy object does not alter stored repository state."""
        policy = GovernancePolicy(
            policy_id="pol_tamper_check",
            name="Original Object",
            budget=BudgetControls(max_cost_per_task=10.0)
        )
        self.manager.create_policy(policy)

        retrieved = self.manager.get_policy("pol_tamper_check")
        retrieved.budget.max_cost_per_task = 999999.0  # Attempt in-memory tampering

        fresh = self.manager.get_policy("pol_tamper_check")
        self.assertEqual(fresh.budget.max_cost_per_task, 10.0)

    def test_12_active_policy_management(self) -> None:
        """Verify activating a policy designates it as active and deactivates others."""
        p1 = GovernancePolicy(policy_id="pol_act_1", name="Policy 1", is_active=True)
        self.manager.create_policy(p1, activate=True)
        self.assertEqual(self.manager.get_active_policy().policy_id, "pol_act_1")

        p2 = GovernancePolicy(policy_id="pol_act_2", name="Policy 2", is_active=False)
        self.manager.create_policy(p2)
        self.assertEqual(self.manager.get_active_policy().policy_id, "pol_act_1")

        # Activate p2
        self.manager.activate_policy("pol_act_2")
        active = self.manager.get_active_policy()
        self.assertEqual(active.policy_id, "pol_act_2")

        # p1 should now be inactive
        p1_retrieved = self.manager.get_policy("pol_act_1")
        self.assertFalse(p1_retrieved.is_active)

    def test_13_policy_history_retrieval(self) -> None:
        """Verify get_policy_history returns all revisions in order."""
        policy = GovernancePolicy(policy_id="pol_hist", name="V1", version="1.0.0")
        self.manager.create_policy(policy)

        self.manager.update_policy("pol_hist", GovernancePolicy(policy_id="pol_hist", name="V2"))
        self.manager.update_policy("pol_hist", GovernancePolicy(policy_id="pol_hist", name="V3"))

        history = self.manager.get_policy_history("pol_hist")
        self.assertEqual(len(history), 3)
        self.assertEqual([h.version for h in history], ["1.0.0", "1.0.1", "1.0.2"])
        self.assertEqual([h.name for h in history], ["V1", "V2", "V3"])

    def test_14_non_existent_policy_lookup_returns_none(self) -> None:
        """Verify looking up a non-existent policy returns None."""
        self.assertIsNone(self.manager.get_policy("pol_does_not_exist"))
        self.assertIsNone(self.manager.get_policy("pol_does_not_exist", version="2.0.0"))

    def test_15_update_non_existent_policy_raises_not_found(self) -> None:
        """Verify updating a non-existent policy raises PolicyNotFoundError."""
        with self.assertRaises(PolicyNotFoundError):
            self.manager.update_policy(
                "pol_ghost",
                GovernancePolicy(policy_id="pol_ghost", name="Ghost Policy")
            )

    def test_16_invalid_range_and_budget_hierarchy_validation(self) -> None:
        """Verify max_cost_per_day < max_cost_per_task is caught and rejected."""
        policy = GovernancePolicy(
            policy_id="pol_bad_budget",
            name="Bad Budget",
            budget=BudgetControls(max_cost_per_task=100.0, max_cost_per_day=10.0)
        )
        with self.assertRaises(PolicyValidationError) as ctx:
            self.manager.create_policy(policy)
        self.assertTrue(any("max_cost_per_day" in v for v in ctx.exception.violations))

    def test_17_invalid_token_hierarchy_validation(self) -> None:
        """Verify max_total_tokens < max_input_tokens is rejected."""
        policy = GovernancePolicy(
            policy_id="pol_bad_tokens",
            name="Bad Tokens",
            tokens=TokenControls(max_input_tokens=50000, max_total_tokens=10000)
        )
        with self.assertRaises(PolicyValidationError) as ctx:
            self.manager.create_policy(policy)
        self.assertTrue(any("max_total_tokens" in v for v in ctx.exception.violations))

    def test_18_overlapping_allowlist_and_blocklist_validation(self) -> None:
        """Verify provider present in both allowlist and blocklist is rejected."""
        policy = GovernancePolicy(
            policy_id="pol_bad_prov",
            name="Overlapping Provider",
            providers=ProviderAccessControls(
                allowed_providers=["OpenAI", "Anthropic"],
                blocked_providers=["Anthropic", "Cohere"]
            )
        )
        with self.assertRaises(PolicyValidationError) as ctx:
            self.manager.create_policy(policy)
        self.assertTrue(any("Providers cannot be both allowed and blocked" in v for v in ctx.exception.violations))

    def test_19_invalid_retry_backoff_validation(self) -> None:
        """Verify retry backoff_factor < 1.0 is rejected."""
        policy = GovernancePolicy(
            policy_id="pol_bad_retry",
            name="Bad Retry",
            retries=RetryPolicy(backoff_factor=0.5)
        )
        with self.assertRaises(PolicyValidationError) as ctx:
            self.manager.create_policy(policy)
        self.assertTrue(any("backoff_factor" in v for v in ctx.exception.violations))

    def test_20_policy_service_delegates_to_policy_manager(self) -> None:
        """Verify DefaultPolicyService wraps PolicyManager and translates exceptions."""
        service = DefaultPolicyService(policy_manager=self.manager)
        active = service.get_active_policy()
        self.assertIsNotNone(active)

        # Update via service
        updated = service.update_policy(
            "pol_default",
            GovernancePolicy(
                policy_id="pol_default",
                name="Service Updated Policy",
                budget=BudgetControls(max_cost_per_task=42.0)
            )
        )
        self.assertEqual(updated.name, "Service Updated Policy")
        self.assertEqual(updated.budget.max_cost_per_task, 42.0)

    def test_21_http_get_and_put_policies_integration(self) -> None:
        """Verify HTTP endpoints /v1/policies and PUT /v1/policies/{id} work end-to-end with PolicyManager."""
        service = DefaultPolicyService(policy_manager=self.manager)
        app = create_app(policy_service=service)
        client = TestClient(app)

        # GET /v1/policies
        res_get = client.get("/v1/policies")
        self.assertEqual(res_get.status_code, 200)
        data = res_get.json()
        self.assertIn("active_policy", data)
        self.assertIn("policies", data)

        # PUT /v1/policies/{id}
        put_payload = {
            "policy_id": "pol_default",
            "name": "HTTP Updated Policy",
            "budget": {"max_cost_per_task": 12.5, "currency": "USD"}
        }
        res_put = client.put("/v1/policies/pol_default", json=put_payload)
        self.assertEqual(res_put.status_code, 200)
        put_data = res_put.json()
        self.assertEqual(put_data["name"], "HTTP Updated Policy")
        self.assertEqual(put_data["budget"]["max_cost_per_task"], 12.5)

    def test_22_repository_replacement_isolation(self) -> None:
        """Verify custom repository implementation can be injected into PolicyManager."""
        class CustomPolicyRepository(IPolicyRepository):
            def __init__(self):
                self._storage = {}
            def get_active(self):
                return None
            def get_by_id(self, policy_id):
                return self._storage.get(policy_id)
            def get_revision(self, policy_id, version):
                return None
            def get_history(self, policy_id):
                return []
            def save(self, policy):
                self._storage[policy.policy_id] = policy
                return policy
            def set_active(self, policy_id, version=None):
                return self._storage[policy_id]
            def list_all(self, include_historical=False):
                return list(self._storage.values())

        custom_repo = CustomPolicyRepository()
        pm = PolicyManager(repository=custom_repo)
        pm.create_policy(GovernancePolicy(policy_id="pol_custom", name="Custom Repo Policy"))
        self.assertIsNotNone(pm.get_policy("pol_custom"))

    def test_23_zero_database_imports_in_policy_package(self) -> None:
        """Verify policy package contains zero database library imports."""
        import infuse.policy
        policy_modules = [m for name, m in sys.modules.items() if name.startswith("infuse.policy")]

        forbidden = ["sqlite3", "psycopg2", "asyncpg", "sqlalchemy", "redis", "qdrant_client", "motor", "pymongo"]
        for mod in policy_modules:
            src = inspect.getsource(mod)
            for f in forbidden:
                self.assertNotIn(f"import {f}", src)
                self.assertNotIn(f"from {f}", src)

    def test_24_zero_provider_and_agent_sdk_imports(self) -> None:
        """Verify policy package contains zero provider or agent SDK imports."""
        import infuse.policy
        policy_modules = [m for name, m in sys.modules.items() if name.startswith("infuse.policy")]

        forbidden = ["openai", "anthropic", "google.generativeai", "cohere", "langchain", "crewai", "autogen"]
        for mod in policy_modules:
            src = inspect.getsource(mod)
            for f in forbidden:
                self.assertNotIn(f"import {f}", src)
                self.assertNotIn(f"from {f}", src)

    def test_25_zero_governor_execution_logic_in_policy_manager(self) -> None:
        """Verify Policy Manager contains zero runtime Governor execution logic."""
        import infuse.policy
        policy_modules = [m for name, m in sys.modules.items() if name.startswith("infuse.policy")]

        forbidden_patterns = ["decide_action", "apply_throttle", "trip_breaker", "terminate_execution"]
        for mod in policy_modules:
            src = inspect.getsource(mod)
            for p in forbidden_patterns:
                self.assertNotIn(p, src)

    def test_26_zero_pricing_calculation_in_policy_manager(self) -> None:
        """Verify Policy Manager contains zero token pricing calculation formulas."""
        import infuse.policy
        policy_modules = [m for name, m in sys.modules.items() if name.startswith("infuse.policy")]

        forbidden_patterns = ["calculate_cost", "cost_per_1k_tokens", "price_per_million"]
        for mod in policy_modules:
            src = inspect.getsource(mod)
            for p in forbidden_patterns:
                self.assertNotIn(p, src)


if __name__ == "__main__":
    unittest.main()
