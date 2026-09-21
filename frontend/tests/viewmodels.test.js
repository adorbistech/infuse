import test from "node:test";
import assert from "node:assert/strict";
import {
  ExecutionSummaryViewModel,
  ExecutionMetricsViewModel,
  ExecutionStateViewModel,
  GovernorDecisionViewModel,
  ProviderModelHealthViewModel,
  ExecutionTimelineEventViewModel,
  ExecutionHistoryItemViewModel,
  GovernancePolicyViewModel,
  ExecutionState,
  GovernorAction,
  EventType
} from "../src/contracts/viewmodels.js";

test("ViewModel Contracts - ExecutionState enum completeness", () => {
  const states = Object.values(ExecutionState);
  assert.deepEqual(states.sort(), [
    "COST_PRESSURE",
    "NORMAL",
    "PROVIDER_CONSTRAINED",
    "QUALITY_DEGRADED",
    "RUNAWAY"
  ]);
});

test("ViewModel Contracts - GovernorAction enum completeness", () => {
  const actions = Object.values(GovernorAction);
  assert.deepEqual(actions.sort(), [
    "CONTINUE",
    "DOWNGRADE",
    "ESCALATE",
    "OPTIMIZE",
    "STOP",
    "SWITCH",
    "THROTTLE"
  ]);
});

test("ViewModel Contracts - ExecutionSummaryViewModel defaults and custom fields", () => {
  const vm = new ExecutionSummaryViewModel({
    execution_id: "exec_123",
    agent_name: "Claude Code",
    task_description: "Run benchmark audit",
    provider: "Anthropic",
    model: "Claude Sonnet"
  });
  assert.equal(vm.execution_id, "exec_123");
  assert.equal(vm.agent_name, "Claude Code");
  assert.equal(vm.status, "RUNNING");
  assert.equal(vm.is_live, true);
});

test("ViewModel Contracts - ExecutionMetricsViewModel fields and percentage calculations", () => {
  const vm = new ExecutionMetricsViewModel({
    input_tokens: 50000,
    cached_tokens: 15000,
    output_tokens: 5000,
    total_tokens: 55000,
    current_cost_usd: 0.25,
    budget_limit_usd: 1.00,
    budget_consumed_percent: 25.0
  });
  assert.equal(vm.total_tokens, 55000);
  assert.equal(vm.current_cost_usd, 0.25);
  assert.equal(vm.budget_consumed_percent, 25.0);
});

test("ViewModel Contracts - GovernancePolicyViewModel structure and action bindings", () => {
  const vm = new GovernancePolicyViewModel();
  assert.ok(vm.policy.policy_id);
  assert.equal(vm.policy.budget.currency, "USD");
  assert.equal(vm.policy.actions.budget_action, GovernorAction.OPTIMIZE);
  assert.equal(vm.policy.actions.runtime_action, GovernorAction.STOP);
  assert.equal(vm.guardrail_strictness_index, "99.98% Strict");
});
