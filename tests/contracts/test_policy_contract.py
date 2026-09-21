"""Tests for Governance Policy Contract."""

import unittest
from infuse.contracts.policy import (
    GovernancePolicy,
    BudgetControls,
    TokenControls,
    RequestControls,
    RuntimeControls,
    ProviderAccessControls,
    WebAccessControls,
    ToolAccessControls,
    RetryPolicy,
    AnomalyProtection,
    PolicyActionBindings,
)
from infuse.contracts.governor import GovernorAction


class TestPolicyContract(unittest.TestCase):
    """Test policy definitions, default safety configurations, and zero hard-coding."""

    def test_default_policy_instantiation(self):
        policy = GovernancePolicy(policy_id="pol_default")
        self.assertEqual(policy.policy_id, "pol_default")
        self.assertTrue(policy.is_active)
        self.assertEqual(policy.schema_version, "1.0.0")

        # Check default actions without hardcoded business limit values
        self.assertIsNone(policy.budget.max_cost_per_task)
        self.assertIsNone(policy.tokens.max_total_tokens)
        self.assertIsNone(policy.requests.max_rpm)
        self.assertIsNone(policy.runtime.max_execution_time_seconds)

        # Check action mappings
        self.assertEqual(policy.actions.budget_action, GovernorAction.OPTIMIZE)
        self.assertEqual(policy.actions.runtime_action, GovernorAction.STOP)
        self.assertEqual(policy.actions.provider_failure_action, GovernorAction.SWITCH)

    def test_custom_user_policy(self):
        policy = GovernancePolicy(
            policy_id="pol_strict",
            name="Strict CI Policy",
            budget=BudgetControls(max_cost_per_task=2.5, max_cost_per_day=50.0),
            tokens=TokenControls(max_input_tokens=100000, max_output_tokens=4000, max_total_tokens=104000),
            requests=RequestControls(max_rpm=30, max_requests_per_task=10),
            runtime=RuntimeControls(max_execution_time_seconds=300),
            providers=ProviderAccessControls(
                allowed_providers=["anthropic", "deepseek"],
                blocked_models=["gpt-3.5-turbo"]
            ),
            web=WebAccessControls(enabled=False, max_web_requests_per_task=0),
            tools=ToolAccessControls(enabled=True, max_tool_calls_per_task=50),
            retries=RetryPolicy(max_retries=2, fallback_provider_on_failure=True),
            anomaly=AnomalyProtection(circuit_breaker_enabled=True),
            actions=PolicyActionBindings(
                budget_action=GovernorAction.STOP,
                token_action=GovernorAction.THROTTLE
            )
        )
        self.assertEqual(policy.budget.max_cost_per_task, 2.5)
        self.assertFalse(policy.web.enabled)
        self.assertEqual(policy.actions.budget_action, GovernorAction.STOP)
        self.assertEqual(policy.actions.token_action, GovernorAction.THROTTLE)

        # JSON Roundtrip
        json_str = policy.model_dump_json()
        loaded = GovernancePolicy.model_validate_json(json_str)
        self.assertEqual(loaded.budget.max_cost_per_task, 2.5)
        self.assertEqual(loaded.providers.allowed_providers, ["anthropic", "deepseek"])


if __name__ == "__main__":
    unittest.main()
