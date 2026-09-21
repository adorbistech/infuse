import test from "node:test";
import assert from "node:assert/strict";
import { Store } from "../src/state/store.js";
import { MockDataProvider } from "../src/data/MockDataProvider.js";
import { ExecutionState, GovernorAction } from "../src/contracts/viewmodels.js";

test("Store - Initial state and subscribers", () => {
  const store = new Store();
  assert.equal(store.state.route, "execution");
  assert.equal(store.state.theme, "dark");
  assert.equal(store.state.activeEngineTab, "token");

  let notifyCount = 0;
  const unsubscribe = store.subscribe(() => {
    notifyCount++;
  });

  store.setRoute("governance");
  assert.equal(store.state.route, "governance");
  assert.equal(notifyCount, 1);

  store.setTheme("light");
  assert.equal(store.state.theme, "light");
  assert.equal(notifyCount, 2);

  unsubscribe();
  store.setRoute("execution");
  assert.equal(notifyCount, 2); // No extra call after unsub
});

test("Store - Load execution and policy data", async () => {
  const store = new Store(new MockDataProvider());
  await Promise.all([
    store.loadExecutionData(),
    store.loadPolicyData()
  ]);

  assert.ok(store.state.executionData);
  assert.ok(store.state.policyData);
  assert.equal(store.state.executionData.summary.agent_name, "OpenCode");
  assert.equal(store.state.policyData.policy.policy_id, "pol_default");
});

test("Store - Trigger simulation state change", async () => {
  const store = new Store(new MockDataProvider());
  await store.loadExecutionData();

  await store.updateStateSimulation(ExecutionState.RUNAWAY);
  assert.equal(store.state.executionData.state.current_state, ExecutionState.RUNAWAY);
  assert.equal(store.state.executionData.governor.current_action, GovernorAction.STOP);
});
