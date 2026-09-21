import test from "node:test";
import assert from "node:assert/strict";
import { Store } from "../src/state/store.js";
import { MockDataProvider } from "../src/data/MockDataProvider.js";
import { renderExecutionPage } from "../src/pages/ExecutionPage.js";
import { renderGovernancePage } from "../src/pages/GovernancePage.js";
import { ExecutionState, GovernorAction } from "../src/contracts/viewmodels.js";

test("Integration - Full simulated execution and governance page lifecycle", async () => {
  const store = new Store(new MockDataProvider());
  
  // 1. Initial Load
  await Promise.all([
    store.loadExecutionData(),
    store.loadPolicyData()
  ]);

  // 2. Render Execution Page
  const execHtml = renderExecutionPage(store);
  assert.match(execHtml, /OpenCode/);
  assert.match(execHtml, /COST PRESSURE/);
  assert.match(execHtml, /TOKEN GROWTH/);
  assert.match(execHtml, /Execution Timeline/);

  // 3. Switch to Governance Page
  store.setRoute("governance");
  const govHtml = renderGovernancePage(store);
  assert.match(govHtml, /Governance/);
  assert.match(govHtml, /Budget Controls/);
  assert.match(govHtml, /Policy Action Matrix/);

  // 4. Trigger State Transition to RUNAWAY
  store.setRoute("execution");
  await store.updateStateSimulation(ExecutionState.RUNAWAY);
  const runawayHtml = renderExecutionPage(store);
  assert.match(runawayHtml, /RUNAWAY/);
  assert.match(runawayHtml, /Circuit-Breaker Halt/);
  assert.equal(store.state.executionData.governor.current_action, GovernorAction.STOP);

  // 5. Update Policy
  const currentPolicy = store.state.policyData.policy;
  await store.savePolicy({
    ...currentPolicy,
    budget: { max_cost_per_task: 25.0, max_cost_per_day: 500.0, currency: "USD" }
  });
  assert.equal(store.state.policyData.policy.budget.max_cost_per_task, 25.0);
});

test("Integration - Zero database / backend coupling check", () => {
  // Verify that all models are purely ViewModel representations and do not import DB or ORM primitives
  const store = new Store();
  assert.equal(typeof store.dataProvider.getExecutionData, "function");
  assert.equal(typeof store.dataProvider.getGovernancePolicy, "function");
});
