/**
 * Execution Header & Context Card Component (Hardened).
 */

export function renderExecutionHeader(summary, allExecutions = []) {
  const executionList = allExecutions.length > 0 ? allExecutions : [
    { execution_id: summary.execution_id, agent_name: summary.agent_name }
  ];

  return `
    <!-- Top Command & Header -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-3 bg-surface-container-low p-4 rounded-xl shadow-sm border border-outline-variant/20">
      <div>
        <div class="flex items-center gap-2">
          <h1 class="font-headline-lg-mobile text-headline-lg-mobile text-on-surface tracking-tight">Execution</h1>
          <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-surface-container-highest text-primary font-code-sm text-code-sm border border-primary/20">
            <span class="w-2 h-2 rounded-full ${summary.is_live ? 'bg-primary animate-pulse' : 'bg-on-surface-variant'}"></span>
            ${summary.is_live ? 'LIVE' : 'ARCHIVED'}
          </span>
        </div>
        <p class="font-body-md text-body-md text-on-surface-variant mt-0.5">Observe and understand what is happening across your AI execution.</p>
      </div>
      <div class="flex items-center gap-2 self-start md:self-center">
        <div class="relative inline-flex items-center">
          <label for="execSelectDropdown" class="font-label-sm text-label-sm text-on-surface-variant mr-2">Execution:</label>
          <div class="relative">
            <select id="execSelectDropdown" class="appearance-none bg-surface-container-high hover:bg-surface-container-highest text-primary font-code-sm text-code-sm pl-3 pr-8 py-1.5 rounded-lg transition-colors shadow-sm border border-outline-variant/30 focus:outline-none focus:ring-1 focus:ring-primary cursor-pointer">
              ${executionList.map(item => `
                <option value="${item.execution_id}" ${item.execution_id === summary.execution_id ? 'selected' : ''}>
                  ${item.execution_id} (${item.agent_name})
                </option>
              `).join("")}
            </select>
            <span class="material-symbols-outlined absolute right-2 top-2 text-[16px] text-on-surface-variant pointer-events-none">expand_more</span>
          </div>
        </div>
        <button class="flex items-center gap-1.5 bg-surface-container hover:bg-surface-container-high active:scale-95 text-on-surface font-label-md text-label-md px-3 py-1.5 rounded-lg transition-all shadow-sm border border-outline-variant/20" id="refreshBtn" title="Refresh Telemetry">
          <span class="material-symbols-outlined text-[16px] text-primary" id="refreshIcon">refresh</span>
          <span>Refresh</span>
        </button>
      </div>
    </div>

    <!-- Execution Header Card: Current Context -->
    <div class="bg-surface-container rounded-xl p-4 shadow-sm flex flex-col gap-3 border border-outline-variant/15">
      <div class="flex flex-wrap items-center justify-between gap-2 pb-2">
        <div class="flex items-center gap-3 min-w-0">
          <div class="w-10 h-10 rounded-lg bg-surface-container-high flex items-center justify-center text-primary shadow-sm border border-outline-variant/20">
            <span class="material-symbols-outlined text-[24px]">smart_toy</span>
          </div>
          <div class="min-w-0">
            <div class="flex items-center gap-2">
              <span class="font-title-md text-title-md text-on-surface font-semibold">${summary.agent_name}</span>
              <span class="px-2 py-0.5 rounded font-code-sm text-code-sm bg-surface-container-high text-primary border border-primary/20">${summary.execution_id}</span>
            </div>
            <p class="font-body-sm text-body-sm text-on-surface-variant truncate max-w-xs md:max-w-xl" title="${summary.task_description}">
              Task: ${summary.task_description}
            </p>
          </div>
        </div>
        <div class="flex items-center gap-2 text-right">
          <div class="bg-surface-container-low px-3 py-1.5 rounded-lg border border-outline-variant/10">
            <div class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">Runtime</div>
            <div class="font-code-sm text-body-md text-primary font-semibold" id="runtimeCounter">${summary.formatted_runtime}</div>
          </div>
          <div class="bg-surface-container-low px-3 py-1.5 rounded-lg border border-outline-variant/10">
            <div class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">Started</div>
            <div class="font-code-sm text-body-md text-on-surface">${summary.started_at.split("T")[1]?.slice(0, 8) || "14:32:18"} UTC</div>
          </div>
        </div>
      </div>
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 bg-surface-container-low p-2.5 rounded-lg border border-outline-variant/10">
        <div>
          <span class="font-label-sm text-label-sm text-on-surface-variant block uppercase tracking-wider">Provider</span>
          <span class="font-body-md text-body-md text-on-surface font-medium flex items-center gap-1.5 mt-0.5">
            <span class="w-1.5 h-1.5 rounded-full bg-primary"></span>
            ${summary.provider}
          </span>
        </div>
        <div>
          <span class="font-label-sm text-label-sm text-on-surface-variant block uppercase tracking-wider">Model</span>
          <span class="font-body-md text-body-md text-on-surface font-medium mt-0.5">${summary.model}</span>
        </div>
        <div>
          <span class="font-label-sm text-label-sm text-on-surface-variant block uppercase tracking-wider">Routing Mode</span>
          <span class="font-body-md text-body-md text-on-surface font-medium mt-0.5">${summary.routing_mode}</span>
        </div>
        <div>
          <span class="font-label-sm text-label-sm text-on-surface-variant block uppercase tracking-wider">Isolation Pool</span>
          <span class="font-body-md text-body-md text-primary font-medium mt-0.5">${summary.isolation_pool}</span>
        </div>
      </div>
    </div>
  `;
}
