import test from "node:test";
import assert from "node:assert/strict";
import { MockDataProvider } from "../src/data/MockDataProvider.js";
import { ExecutionState, GovernorAction } from "../src/contracts/viewmodels.js";

test("MockDataProvider - Initial execution data generation", async () => {
  const provider = new MockDataProvider();
  const data = await provider.getExecutionData();

  assert.ok(data.summary);
  assert.ok(data.metrics);
  assert.ok(data.state);
  assert.ok(data.governor);
  assert.ok(data.health);
  assert.ok(Array.isArray(data.timeline));
  assert.ok(Array.isArray(data.history));

  assert.equal(data.summary.execution_id, "exec_01J8K7A2");
  assert.equal(data.state.current_state, ExecutionState.COST_PRESSURE);
  assert.equal(data.governor.current_action, GovernorAction.OPTIMIZE);
});

test("MockDataProvider - State transitions across all 5 states", async () => {
  const provider = new MockDataProvider();

  // Test NORMAL
  let data = await provider.triggerStateChange("exec_01J8K7A2", ExecutionState.NORMAL);
  assert.equal(data.state.current_state, ExecutionState.NORMAL);
  assert.equal(data.governor.current_action, GovernorAction.CONTINUE);
  assert.equal(data.health.status, "HEALTHY");

  // Test RUNAWAY
  data = await provider.triggerStateChange("exec_01J8K7A2", ExecutionState.RUNAWAY);
  assert.equal(data.state.current_state, ExecutionState.RUNAWAY);
  assert.equal(data.governor.current_action, GovernorAction.STOP);

  // Test QUALITY_DEGRADED
  data = await provider.triggerStateChange("exec_01J8K7A2", ExecutionState.QUALITY_DEGRADED);
  assert.equal(data.state.current_state, ExecutionState.QUALITY_DEGRADED);
  assert.equal(data.governor.current_action, GovernorAction.ESCALATE);

  // Test PROVIDER_CONSTRAINED
  data = await provider.triggerStateChange("exec_01J8K7A2", ExecutionState.PROVIDER_CONSTRAINED);
  assert.equal(data.state.current_state, ExecutionState.PROVIDER_CONSTRAINED);
  assert.equal(data.governor.current_action, GovernorAction.SWITCH);
  assert.equal(data.health.status, "DEGRADED");
});

test("MockDataProvider - Policy fetching and saving", async () => {
  const provider = new MockDataProvider();
  const initial = await provider.getGovernancePolicy();
  assert.equal(initial.policy.policy_id, "pol_default");

  const updated = await provider.saveGovernancePolicy({
    ...initial.policy,
    budget: { max_cost_per_task: 5.0, currency: "USD" }
  });
  assert.equal(updated.policy.budget.max_cost_per_task, 5.0);
});
