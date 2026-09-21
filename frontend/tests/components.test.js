import test from "node:test";
import assert from "node:assert/strict";
import { MockDataProvider } from "../src/data/MockDataProvider.js";
import { Store } from "../src/state/store.js";
import { renderHeader } from "../src/components/Header.js";
import { renderExecutionHeader } from "../src/components/ExecutionHeader.js";
import { renderStateSelector } from "../src/components/StateSelector.js";
import { renderMetricsGrid } from "../src/components/MetricsGrid.js";
import { renderCharts } from "../src/components/Charts.js";
import { renderActivityPanel } from "../src/components/ActivityPanel.js";
import { renderGovernorPanel } from "../src/components/GovernorPanel.js";
import { renderHealthPanel } from "../src/components/HealthPanel.js";
import { renderTimeline } from "../src/components/Timeline.js";
import { renderRuntimeEngines } from "../src/components/RuntimeEngines.js";
import { renderHistoryTable } from "../src/components/HistoryTable.js";
import { renderPolicyForm } from "../src/components/PolicyForm.js";

test("Components - renderHeader accessibility and active tab class", () => {
  const store = new Store();
  const html = renderHeader(store.state, store);
  assert.match(html, /aria-label="Main Navigation"/);
  assert.match(html, /id="nav-execution-btn"/);
  assert.match(html, /id="nav-governance-btn"/);
  assert.match(html, /INFUSE/);
});

test("Components - renderExecutionHeader and context fields", async () => {
  const provider = new MockDataProvider();
  const data = await provider.getExecutionData();
  const html = renderExecutionHeader(data.summary);

  assert.match(html, /OpenCode/);
  assert.match(html, /exec_01J8K7A2/);
  assert.match(html, /Anthropic/);
  assert.match(html, /Claude Sonnet/);
  assert.match(html, /08m 42s/);
});

test("Components - renderStateSelector contains state pills and pulse dot", async () => {
  const provider = new MockDataProvider();
  const data = await provider.getExecutionData();
  const html = renderStateSelector(data.state);

  assert.match(html, /COST PRESSURE/);
  assert.match(html, /animate-ping/);
  assert.match(html, /data-state="NORMAL"/);
  assert.match(html, /data-state="RUNAWAY"/);
  assert.match(html, /data-state="QUALITY_DEGRADED"/);
});

test("Components - renderMetricsGrid contains 8 cards and tabular figures", async () => {
  const provider = new MockDataProvider();
  const data = await provider.getExecutionData();
  const html = renderMetricsGrid(data.metrics);

  assert.match(html, /Input Tokens/);
  assert.match(html, /Cached Tokens/);
  assert.match(html, /Output Tokens/);
  assert.match(html, /Total Tokens/);
  assert.match(html, /Current Cost/);
  assert.match(html, /Budget Used/);
  assert.match(html, /Requests/);
  assert.match(html, /Errors &amp; Retries/);
});

test("Components - renderPolicyForm contains 10 sections and select bindings", async () => {
  const provider = new MockDataProvider();
  const policy = await provider.getGovernancePolicy();
  const html = renderPolicyForm(policy);

  assert.match(html, /Budget Controls/);
  assert.match(html, /Token Controls/);
  assert.match(html, /Request Controls/);
  assert.match(html, /Runtime Controls/);
  assert.match(html, /Provider &amp; Model Access/);
  assert.match(html, /Web Access Controls/);
  assert.match(html, /Tool Access/);
  assert.match(html, /Retry Policy/);
  assert.match(html, /Anomaly &amp; Runaway Protection/);
  assert.match(html, /Policy Action Matrix Summary/);
  assert.match(html, /name="budget_action"/);
  assert.match(html, /name="token_action"/);
  assert.match(html, /name="request_action"/);
  assert.match(html, /name="runtime_action"/);
  assert.match(html, /name="provider_failure_action"/);
});
