/**
 * Runtime Engine Inspector Component (Tabbed view for Token, Economics, Health, Governor).
 */

export function renderRuntimeEngines(activeTab, executionData) {
  const tabs = [
    { key: "token", label: "Token Observer" },
    { key: "economics", label: "Economics" },
    { key: "health", label: "Health Engine" },
    { key: "governor", label: "Governor" }
  ];

  let tabContent = "";

  if (activeTab === "token") {
    tabContent = `
      <div class="space-y-2 text-body-sm font-code-sm">
        <div class="flex justify-between border-b border-outline-variant/15 pb-1">
          <span class="text-on-surface-variant">Observer State:</span>
          <span class="text-emerald-400">ACTIVE_STREAMING</span>
        </div>
        <div class="flex justify-between border-b border-outline-variant/15 pb-1">
          <span class="text-on-surface-variant">Input Velocity:</span>
          <span class="text-on-surface">342 tokens/sec</span>
        </div>
        <div class="flex justify-between border-b border-outline-variant/15 pb-1">
          <span class="text-on-surface-variant">Cache Hit Rate:</span>
          <span class="text-primary font-semibold">30.1%</span>
        </div>
        <div class="flex justify-between border-b border-outline-variant/15 pb-1">
          <span class="text-on-surface-variant">Reconciliation:</span>
          <span class="text-on-surface">Authoritative (Provider Sync)</span>
        </div>
      </div>
    `;
  } else if (activeTab === "economics") {
    tabContent = `
      <div class="space-y-2 text-body-sm font-code-sm">
        <div class="flex justify-between border-b border-outline-variant/15 pb-1">
          <span class="text-on-surface-variant">Current Burn Rate:</span>
          <span class="text-tertiary font-semibold">$0.021 / min</span>
        </div>
        <div class="flex justify-between border-b border-outline-variant/15 pb-1">
          <span class="text-on-surface-variant">Projected Final Cost:</span>
          <span class="text-on-surface">$0.245 USD</span>
        </div>
        <div class="flex justify-between border-b border-outline-variant/15 pb-1">
          <span class="text-on-surface-variant">Pacing Budget Alert:</span>
          <span class="text-tertiary">TRIGGERED @ 70% ($0.175)</span>
        </div>
        <div class="flex justify-between border-b border-outline-variant/15 pb-1">
          <span class="text-on-surface-variant">Policy Target:</span>
          <span class="text-on-surface">OPTIMIZE (Context Compaction)</span>
        </div>
      </div>
    `;
  } else if (activeTab === "health") {
    tabContent = `
      <div class="space-y-2 text-body-sm font-code-sm">
        <div class="flex justify-between border-b border-outline-variant/15 pb-1">
          <span class="text-on-surface-variant">Upstream Provider:</span>
          <span class="text-on-surface font-semibold">Anthropic API v1</span>
        </div>
        <div class="flex justify-between border-b border-outline-variant/15 pb-1">
          <span class="text-on-surface-variant">P95 Latency:</span>
          <span class="text-on-surface">840ms</span>
        </div>
        <div class="flex justify-between border-b border-outline-variant/15 pb-1">
          <span class="text-on-surface-variant">Consecutive Failures:</span>
          <span class="text-emerald-400">0</span>
        </div>
        <div class="flex justify-between border-b border-outline-variant/15 pb-1">
          <span class="text-on-surface-variant">Fallback Availability:</span>
          <span class="text-primary">Ready (DeepSeek V4.1)</span>
        </div>
      </div>
    `;
  } else {
    tabContent = `
      <div class="space-y-2 text-body-sm font-code-sm">
        <div class="flex justify-between border-b border-outline-variant/15 pb-1">
          <span class="text-on-surface-variant">Decision Authority:</span>
          <span class="text-primary font-semibold">Central Governor</span>
        </div>
        <div class="flex justify-between border-b border-outline-variant/15 pb-1">
          <span class="text-on-surface-variant">Active Evaluation:</span>
          <span class="text-on-surface">Rule: MAX_BUDGET_PACING</span>
        </div>
        <div class="flex justify-between border-b border-outline-variant/15 pb-1">
          <span class="text-on-surface-variant">Boundary Capability:</span>
          <span class="text-on-surface">supports_next_step_switch: true</span>
        </div>
        <div class="flex justify-between border-b border-outline-variant/15 pb-1">
          <span class="text-on-surface-variant">Control Outcome:</span>
          <span class="text-emerald-400">ACCEPTED_AND_ENFORCED</span>
        </div>
      </div>
    `;
  }

  return `
    <div class="bg-surface-container rounded-xl p-4 shadow-sm flex flex-col gap-3 border border-outline-variant/15">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <span class="material-symbols-outlined text-[18px] text-primary">hub</span>
          <h2 class="font-title-md text-title-md text-on-surface">Runtime Engines</h2>
        </div>
        <span class="font-code-sm text-code-sm text-on-surface-variant">Signal Telemetry</span>
      </div>

      <!-- Tab Buttons -->
      <div class="flex gap-1 bg-surface-container-low p-1 rounded-lg">
        ${tabs.map(t => {
          const isActive = t.key === activeTab;
          return `
            <button 
              class="engine-tab-btn flex-1 py-1 px-2 rounded-md font-label-sm text-label-sm transition-all ${
                isActive ? 'bg-surface-container-high text-primary font-semibold shadow-sm' : 'text-on-surface-variant hover:text-on-surface'
              }" 
              data-tab="${t.key}">
              ${t.label}
            </button>
          `;
        }).join("")}
      </div>

      <!-- Content Area -->
      <div class="bg-surface-container-low p-3 rounded-lg">
        ${tabContent}
      </div>
    </div>
  `;
}
