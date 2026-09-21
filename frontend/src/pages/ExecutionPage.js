/**
 * Execution / Information Page Assembler (Hardened).
 */

import { renderExecutionHeader } from "../components/ExecutionHeader.js";
import { renderStateSelector } from "../components/StateSelector.js";
import { renderMetricsGrid } from "../components/MetricsGrid.js";
import { renderCharts } from "../components/Charts.js";
import { renderActivityPanel } from "../components/ActivityPanel.js";
import { renderGovernorPanel } from "../components/GovernorPanel.js";
import { renderHealthPanel } from "../components/HealthPanel.js";
import { renderTimeline } from "../components/Timeline.js";
import { renderRuntimeEngines } from "../components/RuntimeEngines.js";
import { renderHistoryTable } from "../components/HistoryTable.js";

export function renderExecutionPage(store) {
  const data = store.state.executionData;
  if (!data) {
    return `<div class="p-8 text-center text-on-surface-variant font-code-sm">Loading execution telemetry...</div>`;
  }

  const { query, state, agent } = store.state.historyFilter;

  return `
    <div class="space-y-4">
      ${renderExecutionHeader(data.summary, data.history)}
      ${renderStateSelector(data.state)}
      ${renderMetricsGrid(data.metrics)}
      ${renderCharts(data.metrics)}
      ${renderActivityPanel(data.metrics)}
      ${renderGovernorPanel(data.governor)}
      ${renderHealthPanel(data.health)}

      <!-- 2-Column Layout: Timeline & Runtime Engines -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-3">
        <div class="lg:col-span-2">
          ${renderTimeline(data.timeline)}
        </div>
        <div class="lg:col-span-1">
          ${renderRuntimeEngines(store.state.activeEngineTab, data)}
        </div>
      </div>

      ${renderHistoryTable(data.history, data.summary.execution_id, query, state, agent)}
    </div>
  `;
}
