/**
 * Execution Header & Context Card Component.
 */

export function renderExecutionHeader(summary) {
  return `
    <!-- Top Command & Header -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-3 bg-surface-container-low p-4 rounded-xl shadow-sm border border-outline-variant/20">
      <div>
        <div class="flex items-center gap-2">
          <h1 class="font-headline-lg-mobile text-headline-lg-mobile text-on-surface tracking-tight">Execution</h1>
          <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-surface-container-highest text-primary font-code-sm text-code-sm">
            <span class="w-2 h-2 rounded-full bg-primary animate-pulse"></span>
            LIVE
          </span>
        </div>
        <p class="font-body-md text-body-md text-on-surface-variant mt-0.5">Observe and understand what is happening across your AI execution.</p>
      </div>
      <div class="flex items-center gap-2 self-start md:self-center">
        <div class="relative inline-flex items-center">
          <span class="font-label-sm text-label-sm text-on-surface-variant mr-2">Execution:</span>
          <button class="flex items-center gap-2 bg-surface-container-high hover:bg-surface-container-highest text-on-surface font-code-sm text-code-sm px-3 py-1.5 rounded-lg transition-colors shadow-sm" id="execSelectBtn">
            <span class="font-semibold text-primary">${summary.execution_id}</span>
            <span class="material-symbols-outlined text-[16px] text-on-surface-variant">expand_more</span>
          </button>
        </div>
        <button class="flex items-center gap-1.5 bg-surface-container hover:bg-surface-container-high active:scale-95 text-on-surface font-label-md text-label-md px-3 py-1.5 rounded-lg transition-all shadow-sm" id="refreshBtn">
          <span class="material-symbols-outlined text-[16px] text-primary" id="refreshIcon">refresh</span>
          <span>Refresh</span>
        </button>
      </div>
    </div>

    <!-- Execution Header Card: Current Context -->
    <div class="bg-surface-container rounded-xl p-4 shadow-sm flex flex-col gap-3 border border-outline-variant/15">
      <div class="flex flex-wrap items-center justify-between gap-2 pb-2">
        <div class="flex items-center gap-2 min-w-0">
          <div class="w-8 h-8 rounded-lg bg-surface-container-high flex items-center justify-center text-primary">
            <span class="material-symbols-outlined text-[20px]">smart_toy</span>
          </div>
          <div class="min-w-0">
            <div class="flex items-center gap-2">
              <span class="font-title-md text-title-md text-on-surface">${summary.agent_name}</span>
              <span class="px-2 py-0.5 rounded font-code-sm text-code-sm bg-surface-container-high text-primary">${summary.execution_id}</span>
            </div>
            <p class="font-body-sm text-body-sm text-on-surface-variant truncate max-w-xs md:max-w-md" title="${summary.task_description}">
              Task: ${summary.task_description}
            </p>
          </div>
        </div>
        <div class="flex items-center gap-2 text-right">
          <div class="bg-surface-container-low px-2.5 py-1.5 rounded-lg">
            <div class="font-label-sm text-label-sm text-on-surface-variant uppercase">Runtime</div>
            <div class="font-code-sm text-body-md text-primary font-semibold" id="runtimeCounter">${summary.formatted_runtime}</div>
          </div>
          <div class="bg-surface-container-low px-2.5 py-1.5 rounded-lg">
            <div class="font-label-sm text-label-sm text-on-surface-variant uppercase">Started</div>
            <div class="font-code-sm text-body-md text-on-surface">${summary.started_at.split("T")[1]?.slice(0, 8) || "14:32:18"}</div>
          </div>
        </div>
      </div>
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 bg-surface-container-low p-2.5 rounded-lg">
        <div>
          <span class="font-label-sm text-label-sm text-on-surface-variant block">Provider</span>
          <span class="font-body-md text-body-md text-on-surface font-medium flex items-center gap-1">
            <span class="w-1.5 h-1.5 rounded-full bg-primary"></span>
            ${summary.provider}
          </span>
        </div>
        <div>
          <span class="font-label-sm text-label-sm text-on-surface-variant block">Model</span>
          <span class="font-body-md text-body-md text-on-surface font-medium">${summary.model}</span>
        </div>
        <div>
          <span class="font-label-sm text-label-sm text-on-surface-variant block">Routing Mode</span>
          <span class="font-body-md text-body-md text-on-surface font-medium">${summary.routing_mode}</span>
        </div>
        <div>
          <span class="font-label-sm text-label-sm text-on-surface-variant block">Isolation Pool</span>
          <span class="font-body-md text-body-md text-primary font-medium">${summary.isolation_pool}</span>
        </div>
      </div>
    </div>
  `;
}
