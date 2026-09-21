"""Tests for Frontend ViewModel Contract."""

import unittest
from infuse.contracts.frontend import (
    ExecutionSummaryViewModel,
    ExecutionMetricsViewModel,
    ExecutionStateViewModel,
    GovernorDecisionViewModel,
    ProviderModelHealthViewModel,
    ExecutionTimelineEventViewModel,
    ExecutionHistoryItemViewModel,
    GovernancePolicyViewModel,
)
from infuse.contracts.events import EventType
from infuse.contracts.governor import GovernorAction
from infuse.contracts.policy import GovernancePolicy
from infuse.contracts.state import ExecutionState


class TestFrontendContract(unittest.TestCase):
    """Test ViewModel mappings matching Stitch console requirements."""

    def test_execution_summary_view_model(self):
        vm = ExecutionSummaryViewModel(
            execution_id="exec_01J8K7A2",
            agent_name="OpenCode",
            task_description="Refactor authentication middleware",
            status="RUNNING",
            provider="Anthropic",
            model="Claude Sonnet",
            routing_mode="Auto-Governor v2",
            isolation_pool="eu-central-sandbox",
            runtime_seconds=522,
            formatted_runtime="08m 42s"
        )
        self.assertEqual(vm.execution_id, "exec_01J8K7A2")
        self.assertEqual(vm.formatted_runtime, "08m 42s")
        self.assertTrue(vm.is_live)

    def test_execution_metrics_view_model(self):
        vm = ExecutionMetricsViewModel(
            input_tokens=14200,
            cached_tokens=8500,
            output_tokens=3100,
            total_tokens=17300,
            current_cost_usd=0.185,
            budget_limit_usd=0.25,
            budget_consumed_percent=74.0,
            requests_count=12,
            requests_per_minute=4.5,
            errors_count=0,
            retries_count=1,
            web_requests_count=3,
            tool_calls_count=8
        )
        self.assertEqual(vm.total_tokens, 17300)
        self.assertEqual(vm.budget_consumed_percent, 74.0)

    def test_execution_state_view_model(self):
        vm = ExecutionStateViewModel(
            current_state=ExecutionState.COST_PRESSURE,
            state_display_name="COST PRESSURE",
            description="Execution cost is approaching the configured policy boundary.",
            policy_boundary_threshold_percent=80.0,
            reason_codes=["BUDGET_UTILIZATION_74_PERCENT"]
        )
        self.assertEqual(vm.current_state, ExecutionState.COST_PRESSURE)
        self.assertEqual(len(vm.available_states), 5)

    def test_governor_decision_view_model(self):
        vm = GovernorDecisionViewModel(
            current_action=GovernorAction.OPTIMIZE,
            action_banner_title="Active Regulation: Prompt Compression",
            action_banner_description="Context compression active to remain within task budget.",
            reason_codes=["POLICY_BUDGET_WARNING"]
        )
        self.assertEqual(vm.current_action, GovernorAction.OPTIMIZE)

    def test_timeline_event_view_model(self):
        vm = ExecutionTimelineEventViewModel(
            event_id="evt_01",
            time_offset="+01:24",
            event_type=EventType.STATE_CHANGED,
            title="State Transition: COST PRESSURE",
            description="Execution cost reached 70% threshold.",
            is_state_change=True,
            badge_label="COST PRESSURE"
        )
        self.assertTrue(vm.is_state_change)
        self.assertEqual(vm.time_offset, "+01:24")

    def test_history_item_view_model(self):
        vm = ExecutionHistoryItemViewModel(
            execution_id="exec_past_1",
            agent_name="Claude Code",
            task_preview="Audit API routes",
            provider="Anthropic",
            model="Claude Haiku",
            status="COMPLETED",
            state=ExecutionState.NORMAL,
            total_tokens=4500,
            cost_usd=0.006,
            runtime_formatted="01m 15s"
        )
        self.assertEqual(vm.total_tokens, 4500)
        self.assertEqual(vm.status, "COMPLETED")

    def test_governance_policy_view_model(self):
        policy = GovernancePolicy(policy_id="pol_01")
        vm = GovernancePolicyViewModel(
            policy=policy,
            guardrail_strictness_index="99.98% Strict",
            is_editing=False
        )
        self.assertEqual(vm.policy.policy_id, "pol_01")
        self.assertEqual(len(vm.available_actions), 5)


if __name__ == "__main__":
    unittest.main()
