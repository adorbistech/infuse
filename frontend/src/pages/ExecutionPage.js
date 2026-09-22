/**
 * Execution / Information Page Assembler (Hardened).
 * 
 * Supports Loading, Error, Empty, and Loaded states.
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
import { DataStatus } from "../contracts/viewmodels.js";

export function renderExecutionPage(store) {
  const status = store.state.status;
  const error = store.state.error;
  const data = store.state.executionData;

  // 1. Error State
  if (status === DataStatus.ERROR || error) {
    return `
      <div id="execution-error-state" class="glass-panel p-8 rounded-xl border border-error/30 bg-error/10 text-center space-y-4 max-w-2xl mx-auto my-12">
        <div class="inline-flex p-3 rounded-full bg-error/20 text-error mb-2">
          <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
        </div>
        <h2 class="font-headline text-lg font-bold text-on-surface">Execution Telemetry Unavailable</h2>
        <p class="text-on-surface-variant text-sm font-code-sm max-w-md mx-auto">
          ${error?.message || "Failed to load execution telemetry."}
        </p>
        ${error?.code ? `<div class="text-xs text-error/80 font-code-sm">Error Code: ${error.code}</div>` : ""}
        <div class="pt-2">
          <button id="retry-exec-btn" class="px-5 py-2 rounded-lg bg-surface-container-highest hover:bg-surface-container-high text-on-surface text-xs font-semibold uppercase tracking-wider transition-colors shadow">
            Retry Loading
          </button>
        </div>
      </div>
    `;
  }

  // 2. Loading State
  if (status === DataStatus.LOADING || (!data && status !== DataStatus.EMPTY)) {
    return `
      <div id="execution-loading-state" class="space-y-4 animate-pulse">
        <div class="h-20 bg-surface-container-highest/40 rounded-xl"></div>
        <div class="h-14 bg-surface-container-highest/30 rounded-xl"></div>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div class="h-28 bg-surface-container-highest/30 rounded-xl"></div>
          <div class="h-28 bg-surface-container-highest/30 rounded-xl"></div>
          <div class="h-28 bg-surface-container-highest/30 rounded-xl"></div>
          <div class="h-28 bg-surface-container-highest/30 rounded-xl"></div>
        </div>
        <div class="p-8 text-center text-on-surface-variant font-code-sm">
          <span class="inline-block animate-spin mr-2">⟳</span> Loading execution telemetry...
        </div>
      </div>
    `;
  }

  // 3. Empty State
  if (status === DataStatus.EMPTY || !data) {
    return `
      <div id="execution-empty-state" class="glass-panel p-12 rounded-xl text-center space-y-4 max-w-lg mx-auto my-12 border border-outline-variant/20">
        <div class="text-4xl text-on-surface-variant">∅</div>
        <h2 class="font-headline text-lg font-bold text-on-surface">No Execution Telemetry Found</h2>
        <p class="text-on-surface-variant text-sm font-code-sm">
          No execution telemetry is currently available for ID "${store.state.executionId}".
        </p>
        <div class="pt-2">
          <button id="load-default-exec-btn" class="px-5 py-2 rounded-lg bg-primary text-on-primary text-xs font-semibold uppercase tracking-wider transition-colors shadow">
            Load Default Execution
          </button>
        </div>
      </div>
    `;
  }

  // 4. Loaded State
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
