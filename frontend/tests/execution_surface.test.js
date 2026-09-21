import test from "node:test";
import assert from "node:assert/strict";
import { MockDataProvider } from "../src/data/MockDataProvider.js";
import { Store } from "../src/state/store.js";
import { renderExecutionPage } from "../src/pages/ExecutionPage.js";
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
import { ExecutionState, GovernorAction } from "../src/contracts/viewmodels.js";

test("Block 02 Execution Surface - Complete 11 sections rendered in ExecutionPage", async () => {
  const store = new Store(new MockDataProvider());
  await store.loadExecutionData();

  const html = renderExecutionPage(store);

  // 1. Execution Context
  assert.match(html, /OpenCode/);
  assert.match(html, /exec_01J8K7A2/);
  assert.match(html, /Isolation Pool/);

  // 2. Execution State
  assert.match(html, /Execution State/);
  assert.match(html, /COST PRESSURE/);

  // 3. Execution Metrics (8 Cards)
  assert.match(html, /Input Tokens/);
  assert.match(html, /Cached Tokens/);
  assert.match(html, /Output Tokens/);
  assert.match(html, /Total Tokens/);
  assert.match(html, /Current Cost/);
  assert.match(html, /Budget Used/);
  assert.match(html, /Requests/);
  assert.match(html, /Errors &amp; Retries/);

  // 4. Token Growth
  assert.match(html, /TOKEN GROWTH/);

  // 5. Cost Over Time
  assert.match(html, /COST OVER TIME/);
  assert.match(html, /Warning \(\$0\.20\)/);

  // 6. Execution Activity
  assert.match(html, /Execution Activity/);
  assert.match(html, /Web Activity/);
  assert.match(html, /Tool Invocations/);
  assert.match(html, /File Operations/);
  assert.match(html, /Retries \/ Backoffs/);

  // 7. Governor Panel
  assert.match(html, /Execution Governor/);
  assert.match(html, /OPTIMIZE/);
  assert.match(html, /Recent Governor Decision Log/);

  // 8. Provider / Model Health
  assert.match(html, /Anthropic Claude Sonnet/);
  assert.match(html, /HEALTHY/);
  assert.match(html, /Latency/);

  // 9. Execution Timeline
  assert.match(html, /Execution Timeline/);
  assert.match(html, /Execution Started/);

  // 10. Runtime Engine Inspection
  assert.match(html, /Runtime Engines/);
  assert.match(html, /Token Observer/);
  assert.match(html, /Economics/);
  assert.match(html, /Health Engine/);
  assert.match(html, /Governor/);

  // 11. Execution History
  assert.match(html, /Execution History/);
  assert.match(html, /Claude Code/);
  assert.match(html, /Codex/);
  assert.match(html, /Hermes/);
});

test("Block 02 Execution State - Rendering all 5 canonical states", async () => {
  const provider = new MockDataProvider();

  for (const state of Object.values(ExecutionState)) {
    const data = await provider.triggerStateChange("exec_01J8K7A2", state);
    const html = renderStateSelector(data.state);
    assert.match(html, new RegExp(state.replace("_", " ")));
    assert.match(html, /data-state=/);
  }
});

test("Block 02 Governor Actions - Rendering canonical action vocabulary", () => {
  const actions = Object.values(GovernorAction);
  for (const action of actions) {
    const html = renderGovernorPanel({
      current_action: action,
      action_banner_title: `Action: ${action}`,
      action_banner_description: `Description for ${action}`,
      reason_codes: ["TEST_TRIGGER_CODE"],
      recent_decisions: [{ time: "12:00", action, reason: "Test rationale" }]
    });
    assert.match(html, new RegExp(action));
    assert.match(html, /TEST_TRIGGER_CODE/);
  }
});

test("Block 02 History Filtering - Multi-dimensional search & filtering", async () => {
  const provider = new MockDataProvider();
  const data = await provider.getExecutionData();
  const history = data.history;

  // 1. Filter by query "Swagger"
  const htmlQuery = renderHistoryTable(history, "exec_01J8K7A2", "Swagger", "ALL", "ALL");
  assert.match(htmlQuery, /exec_01J8J691/);
  assert.doesNotMatch(htmlQuery, /exec_01J8H432/);

  // 2. Filter by state "RUNAWAY"
  const htmlState = renderHistoryTable(history, "exec_01J8K7A2", "", "RUNAWAY", "ALL");
  assert.match(htmlState, /exec_01J8G219/);
  assert.doesNotMatch(htmlState, /exec_01J8J691/);

  // 3. Filter by agent "Hermes"
  const htmlAgent = renderHistoryTable(history, "exec_01J8K7A2", "", "ALL", "Hermes");
  assert.match(htmlAgent, /exec_01J8F104/);
  assert.doesNotMatch(htmlAgent, /exec_01J8K7A2/);

  // 4. Empty match returns friendly notice
  const htmlNone = renderHistoryTable(history, "exec_01J8K7A2", "nonexistent-query-12345", "ALL", "ALL");
  assert.match(htmlNone, /No execution runs match/);
});

test("Block 02 Runtime Engine Inspection - Rendering all 4 tabs", async () => {
  const provider = new MockDataProvider();
  const data = await provider.getExecutionData();

  // Tab 1: Token
  const tokenHtml = renderRuntimeEngines("token", data);
  assert.match(tokenHtml, /ACTIVE_STREAMING/);
  assert.match(tokenHtml, /Cache Hit Rate/);

  // Tab 2: Economics
  const econHtml = renderRuntimeEngines("economics", data);
  assert.match(econHtml, /Burn Rate/);
  assert.match(econHtml, /Pacing Budget Alert/);

  // Tab 3: Health
  const healthHtml = renderRuntimeEngines("health", data);
  assert.match(healthHtml, /Anthropic API/);
  assert.match(healthHtml, /P95 Latency/);

  // Tab 4: Governor
  const govHtml = renderRuntimeEngines("governor", data);
  assert.match(govHtml, /Central Governor/);
  assert.match(govHtml, /ACCEPTED_AND_ENFORCED/);
});
