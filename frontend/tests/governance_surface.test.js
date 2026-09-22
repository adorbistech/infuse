/**
 * Block 03 — Governance / Policy Surface Hardening Verification Test Suite.
 * 
 * Verifies:
 * - All 10 Governance policy sections rendered and correctly bound
 * - GovernancePolicyViewModel integration
 * - Editing, save, cancel/reset, and duplicate lifecycle
 * - Unsaved state detection and draft mode badges
 * - Canonical Governor action vocabulary (all 7 actions)
 * - Policy action matrix explanatory summary
 * - Policy UX validation and malformed value rejection
 * - Provider and model allowlists without provider-selection logic
 * - Zero backend/database coupling
 * - Zero runtime enforcement execution in frontend
 */

import test from "node:test";
import assert from "node:assert/strict";
import { MockDataProvider } from "../src/data/MockDataProvider.js";
import { Store } from "../src/state/store.js";
import { renderPolicyForm, renderGovernorActionBadge, ACTION_OPTIONS } from "../src/components/PolicyForm.js";
import { renderGovernancePage } from "../src/pages/GovernancePage.js";
import {
  GovernancePolicyViewModel,
  GovernorAction,
  validateGovernancePolicy
} from "../src/contracts/viewmodels.js";

test("Block 03 - GovernancePolicyViewModel structure and 10 sections integrity", () => {
  const vm = new GovernancePolicyViewModel();
  const policy = vm.policy;

  // 1. Budget Controls
  assert.equal(typeof policy.budget.max_cost_per_task, "number");
  assert.equal(typeof policy.budget.max_cost_per_day, "number");
  assert.equal(typeof policy.budget.max_cost_per_month, "number");
  assert.equal(policy.budget.currency, "USD");

  // 2. Token Controls
  assert.equal(typeof policy.tokens.max_input_tokens, "number");
  assert.equal(typeof policy.tokens.max_output_tokens, "number");
  assert.equal(typeof policy.tokens.max_total_tokens, "number");

  // 3. Request Controls
  assert.equal(typeof policy.requests.max_rpm, "number");
  assert.equal(typeof policy.requests.max_requests_per_task, "number");

  // 4. Runtime Controls
  assert.equal(typeof policy.runtime.max_execution_time_seconds, "number");

  // 5. Provider & Model Access
  assert.ok(Array.isArray(policy.providers.allowed_providers));
  assert.ok(Array.isArray(policy.providers.allowed_models));
  assert.ok(Array.isArray(policy.providers.blocked_providers));
  assert.ok(Array.isArray(policy.providers.blocked_models));

  // 6. Web Access
  assert.equal(typeof policy.web.enabled, "boolean");
  assert.ok(Array.isArray(policy.web.allowed_domains));
  assert.ok(Array.isArray(policy.web.blocked_domains));
  assert.equal(typeof policy.web.max_web_requests_per_task, "number");

  // 7. Tool Access
  assert.equal(typeof policy.tools.enabled, "boolean");
  assert.ok(Array.isArray(policy.tools.allowed_tools));
  assert.ok(Array.isArray(policy.tools.blocked_tools));
  assert.equal(typeof policy.tools.max_tool_calls_per_task, "number");
  assert.equal(typeof policy.tools.max_consecutive_tool_failures, "number");

  // 8. Retry Policy
  assert.equal(typeof policy.retries.max_retries, "number");
  assert.equal(typeof policy.retries.backoff_factor, "number");
  assert.ok(Array.isArray(policy.retries.retry_on_errors));
  assert.equal(typeof policy.retries.fallback_provider_on_failure, "boolean");

  // 9. Anomaly / Runaway Protection
  assert.equal(typeof policy.anomaly.token_velocity_surge_threshold, "number");
  assert.equal(typeof policy.anomaly.repetitive_loop_threshold, "number");
  assert.equal(typeof policy.anomaly.circuit_breaker_enabled, "boolean");

  // 10. Policy Actions
  assert.equal(policy.actions.budget_action, GovernorAction.OPTIMIZE);
  assert.equal(policy.actions.token_action, GovernorAction.OPTIMIZE);
  assert.equal(policy.actions.request_action, GovernorAction.THROTTLE);
  assert.equal(policy.actions.runtime_action, GovernorAction.STOP);
  assert.equal(policy.actions.provider_failure_action, GovernorAction.SWITCH);
  assert.equal(policy.actions.anomaly_action, GovernorAction.STOP);

  // Available actions list includes all 7 canonical Governor actions
  assert.equal(vm.available_actions.length, 7);
  for (const act of Object.values(GovernorAction)) {
    assert.ok(vm.available_actions.includes(act));
  }
});

test("Block 03 - Canonical Governor Action Vocabulary in Form Options & Badges", () => {
  const canonicalActions = [
    "CONTINUE",
    "OPTIMIZE",
    "ESCALATE",
    "DOWNGRADE",
    "SWITCH",
    "THROTTLE",
    "STOP"
  ];

  // Verify all 7 are present in ACTION_OPTIONS
  const actionValues = ACTION_OPTIONS.map(opt => opt.value);
  for (const act of canonicalActions) {
    assert.ok(actionValues.includes(act), `Action option missing canonical action: ${act}`);
  }

  // Verify badge renderer renders for all 7 canonical actions
  for (const act of canonicalActions) {
    const badgeHtml = renderGovernorActionBadge(act);
    assert.match(badgeHtml, new RegExp(act));
    assert.match(badgeHtml, /font-code-sm/);
  }
});

test("Block 03 - Complete 10 Governance Sections Rendered in PolicyForm", async () => {
  const provider = new MockDataProvider();
  const policyVm = await provider.getGovernancePolicy();
  const html = renderPolicyForm(policyVm);

  // Verify all 10 section headers
  assert.match(html, /1\. Budget Controls/);
  assert.match(html, /2\. Token Controls/);
  assert.match(html, /3\. Request Controls/);
  assert.match(html, /4\. Runtime Controls/);
  assert.match(html, /5\. Provider &amp; Model Access/);
  assert.match(html, /6\. Web Access Controls/);
  assert.match(html, /7\. Tool Access/);
  assert.match(html, /8\. Retry Policy/);
  assert.match(html, /9\. Anomaly &amp; Runaway Protection/);
  assert.match(html, /10\. Policy Action Matrix Summary/);

  // Verify key input names
  assert.match(html, /name="max_cost_per_task"/);
  assert.match(html, /name="max_cost_per_day"/);
  assert.match(html, /name="max_cost_per_month"/);
  assert.match(html, /name="budget_action"/);

  assert.match(html, /name="max_input_tokens"/);
  assert.match(html, /name="max_output_tokens"/);
  assert.match(html, /name="max_total_tokens"/);
  assert.match(html, /name="token_action"/);

  assert.match(html, /name="max_rpm"/);
  assert.match(html, /name="max_requests_per_task"/);
  assert.match(html, /name="request_action"/);

  assert.match(html, /name="max_execution_time_seconds"/);
  assert.match(html, /name="runtime_action"/);

  assert.match(html, /name="allowed_models"/);
  assert.match(html, /name="blocked_models"/);
  assert.match(html, /data-provider-id="anthropic"/);
  assert.match(html, /data-provider-id="openai"/);
  assert.match(html, /data-provider-id="gemini"/);
  assert.match(html, /data-provider-id="deepseek"/);

  assert.match(html, /name="web_enabled"/);
  assert.match(html, /name="max_web_requests_per_task"/);
  assert.match(html, /name="allowed_domains"/);
  assert.match(html, /name="blocked_domains"/);

  assert.match(html, /name="tools_enabled"/);
  assert.match(html, /name="max_tool_calls_per_task"/);
  assert.match(html, /name="max_consecutive_tool_failures"/);
  assert.match(html, /name="allowed_tools"/);
  assert.match(html, /name="blocked_tools"/);

  assert.match(html, /name="max_retries"/);
  assert.match(html, /name="backoff_factor"/);
  assert.match(html, /name="retry_on_errors"/);
  assert.match(html, /name="fallback_provider_on_failure"/);
  assert.match(html, /name="provider_failure_action"/);

  assert.match(html, /name="token_velocity_surge_threshold"/);
  assert.match(html, /name="repetitive_loop_threshold"/);
  assert.match(html, /name="circuit_breaker_enabled"/);
  assert.match(html, /name="anomaly_action"/);

  // Policy Action Matrix rows
  assert.match(html, /Budget Overrun/);
  assert.match(html, /Token Ceiling/);
  assert.match(html, /Rate Ceiling/);
  assert.match(html, /Runtime Expiry/);
  assert.match(html, /Provider Failure/);
  assert.match(html, /Runaway Loop/);
  assert.match(html, /Nominal Flow/);
});

test("Block 03 - UX Validation prevents malformed policy values", () => {
  // Valid policy
  const validVm = new GovernancePolicyViewModel();
  const validCheck = validateGovernancePolicy(validVm.policy);
  assert.equal(validCheck.isValid, true);
  assert.equal(validCheck.errors.length, 0);

  // Negative budget
  const invalidBudget = {
    ...validVm.policy,
    budget: { max_cost_per_task: -5.0 }
  };
  const budgetCheck = validateGovernancePolicy(invalidBudget);
  assert.equal(budgetCheck.isValid, false);
  assert.match(budgetCheck.errors[0], /cannot be negative/i);

  // Negative tokens
  const invalidTokens = {
    ...validVm.policy,
    tokens: { max_input_tokens: -100, max_total_tokens: 500 }
  };
  const tokenCheck = validateGovernancePolicy(invalidTokens);
  assert.equal(tokenCheck.isValid, false);
  assert.match(tokenCheck.errors[0], /cannot be negative/i);

  // Total tokens < input tokens
  const inconsistentTokens = {
    ...validVm.policy,
    tokens: { max_input_tokens: 100000, max_total_tokens: 50000 }
  };
  const inconsistentCheck = validateGovernancePolicy(inconsistentTokens);
  assert.equal(inconsistentCheck.isValid, false);
  assert.match(inconsistentCheck.errors[0], /less than max input tokens/i);

  // Invalid RPM
  const invalidRpm = {
    ...validVm.policy,
    requests: { max_rpm: 0 }
  };
  const rpmCheck = validateGovernancePolicy(invalidRpm);
  assert.equal(rpmCheck.isValid, false);
  assert.match(rpmCheck.errors[0], /at least 1/i);

  // Non-canonical action value
  const invalidAction = {
    ...validVm.policy,
    actions: { budget_action: "EXECUTE_ARBITRARY_PURGE" }
  };
  const actionCheck = validateGovernancePolicy(invalidAction);
  assert.equal(actionCheck.isValid, false);
  assert.match(actionCheck.errors[0], /canonical GovernorAction/i);
});

test("Block 03 - Store policy editing, draft updates, dirty state, reset, duplicate, and save", async () => {
  const store = new Store(new MockDataProvider());
  await store.loadPolicyData();

  assert.equal(store.state.policyData.has_unsaved_changes, false);
  const baselineCost = store.state.policyData.policy.budget.max_cost_per_task;

  // 1. Update Draft
  store.updatePolicyDraft({
    budget: { max_cost_per_task: 42.50 }
  });
  assert.equal(store.state.policyData.has_unsaved_changes, true);
  assert.equal(store.state.policyData.policy.budget.max_cost_per_task, 42.50);

  // Render form in draft mode
  const draftHtml = renderPolicyForm(store.state.policyData);
  assert.match(draftHtml, /Unsaved Draft/);
  assert.match(draftHtml, /Reset Changes/);

  // 2. Reset Changes
  store.resetPolicyChanges();
  assert.equal(store.state.policyData.has_unsaved_changes, false);
  assert.equal(store.state.policyData.policy.budget.max_cost_per_task, baselineCost);
  assert.match(store.state.policyFeedback.message, /discarded/i);

  // 3. Duplicate Policy
  store.duplicatePolicy();
  assert.equal(store.state.policyData.has_unsaved_changes, true);
  assert.match(store.state.policyData.policy.name, /\(Copy\)/);
  assert.match(store.state.policyData.policy.version, /v1\.0\.5/);

  // 4. Save Duplicated Policy
  await store.savePolicy(store.state.policyData.policy);
  assert.equal(store.state.policyData.has_unsaved_changes, false);
  assert.equal(store.state.policyFeedback.type, "success");
  assert.match(store.state.policyFeedback.message, /saved successfully/i);
});

test("Block 03 - Governance UI does NOT contain provider-selection, Governor execution, or database logic", () => {
  const store = new Store(new MockDataProvider());
  
  // Verify that provider allowlist in policy is pure data
  assert.ok(Array.isArray(store.dataProvider.policy.policy.providers.allowed_providers));
  
  // Verify that no provider recommendation, scoring, or selection algorithm exists on store
  assert.equal(typeof store.selectProvider, "undefined");
  assert.equal(typeof store.rankProviders, "undefined");
  assert.equal(typeof store.executeGovernorDecision, "undefined");
  assert.equal(typeof store.enforceBudget, "undefined");
});
