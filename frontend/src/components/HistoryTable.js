/**
 * Execution History Table Component (Hardened with multi-filter and row selection).
 */

export function renderHistoryTable(historyItems, activeExecutionId = "", filterQuery = "", filterState = "ALL", filterAgent = "ALL") {
  // Client-side filtering
  const filtered = historyItems.filter(item => {
    // State filter
    if (filterState !== "ALL" && item.state !== filterState) {
      return false;
    }
    // Agent filter
    if (filterAgent !== "ALL" && item.agent_name !== filterAgent) {
      return false;
    }
    // Query search
    if (filterQuery.trim()) {
      const q = filterQuery.toLowerCase();
      const match = 
        item.execution_id.toLowerCase().includes(q) ||
        item.agent_name.toLowerCase().includes(q) ||
        item.task_preview.toLowerCase().includes(q) ||
        item.provider.toLowerCase().includes(q) ||
        item.model.toLowerCase().includes(q);
      if (!match) return false;
    }
    return true;
  });

  const uniqueAgents = Array.from(new Set(historyItems.map(h => h.agent_name)));

  return `
    <div class="bg-surface-container rounded-xl p-4 shadow-sm flex flex-col gap-3 border border-outline-variant/15">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
        <div class="flex items-center gap-2">
          <span class="material-symbols-outlined text-[18px] text-primary">view_list</span>
          <h2 class="font-title-md text-title-md text-on-surface">Execution History</h2>
          <span class="px-2 py-0.5 rounded-full bg-surface-container-high text-primary font-code-sm text-code-sm">
            ${filtered.length} of ${historyItems.length}
          </span>
        </div>

        <!-- Filters Bar -->
        <div class="flex flex-wrap items-center gap-2">
          <!-- Text Search -->
          <div class="relative">
            <span class="material-symbols-outlined absolute left-2.5 top-2 text-[16px] text-on-surface-variant pointer-events-none">search</span>
            <input 
              type="text" 
              id="historySearchInput"
              placeholder="Search ID, agent, task..." 
              value="${filterQuery}"
              class="h-8 pl-8 pr-3 rounded-lg bg-surface-container-low text-on-surface font-code-sm text-code-sm placeholder-on-surface-variant/50 focus:outline-none focus:ring-1 focus:ring-primary border border-outline-variant/20 w-44 sm:w-56"
            />
          </div>

          <!-- State Filter -->
          <select id="historyStateFilter" class="h-8 px-2 rounded-lg bg-surface-container-low text-on-surface font-code-sm text-code-sm border border-outline-variant/20 focus:outline-none focus:ring-1 focus:ring-primary cursor-pointer">
            <option value="ALL" ${filterState === 'ALL' ? 'selected' : ''}>State: All</option>
            <option value="NORMAL" ${filterState === 'NORMAL' ? 'selected' : ''}>Normal</option>
            <option value="COST_PRESSURE" ${filterState === 'COST_PRESSURE' ? 'selected' : ''}>Cost Pressure</option>
            <option value="RUNAWAY" ${filterState === 'RUNAWAY' ? 'selected' : ''}>Runaway</option>
            <option value="QUALITY_DEGRADED" ${filterState === 'QUALITY_DEGRADED' ? 'selected' : ''}>Quality Degraded</option>
            <option value="PROVIDER_CONSTRAINED" ${filterState === 'PROVIDER_CONSTRAINED' ? 'selected' : ''}>Provider Constrained</option>
          </select>

          <!-- Agent Filter -->
          <select id="historyAgentFilter" class="h-8 px-2 rounded-lg bg-surface-container-low text-on-surface font-code-sm text-code-sm border border-outline-variant/20 focus:outline-none focus:ring-1 focus:ring-primary cursor-pointer">
            <option value="ALL" ${filterAgent === 'ALL' ? 'selected' : ''}>Agent: All</option>
            ${uniqueAgents.map(ag => `
              <option value="${ag}" ${filterAgent === ag ? 'selected' : ''}>${ag}</option>
            `).join("")}
          </select>
        </div>
      </div>

      <!-- Table Wrapper -->
      <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse text-body-sm">
          <thead>
            <tr class="border-b border-outline-variant/20 text-on-surface-variant font-label-sm text-label-sm uppercase tracking-wider">
              <th class="py-2.5 px-3">Execution ID</th>
              <th class="py-2.5 px-3">Agent</th>
              <th class="py-2.5 px-3">Task Preview</th>
              <th class="py-2.5 px-3">Model</th>
              <th class="py-2.5 px-3">State</th>
              <th class="py-2.5 px-3 text-right">Tokens</th>
              <th class="py-2.5 px-3 text-right">Cost</th>
              <th class="py-2.5 px-3 text-right">Runtime</th>
              <th class="py-2.5 px-3 text-center">Action</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-outline-variant/10">
            ${filtered.length === 0 ? `
              <tr>
                <td colspan="9" class="py-6 text-center text-on-surface-variant font-code-sm">
                  No execution runs match the current filter criteria.
                </td>
              </tr>
            ` : filtered.map((item) => {
              const isSelected = item.execution_id === activeExecutionId;
              const stateBadgeStyle = 
                item.state === 'NORMAL' ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30' :
                item.state === 'COST_PRESSURE' ? 'bg-tertiary-container text-on-tertiary font-semibold' :
                item.state === 'RUNAWAY' ? 'bg-error-container text-error font-semibold' :
                item.state === 'QUALITY_DEGRADED' ? 'bg-secondary-container text-secondary font-semibold' :
                'bg-surface-container-highest text-outline';

              return `
                <tr class="hover:bg-surface-container-high/60 transition-colors cursor-pointer ${isSelected ? 'bg-surface-container-high/90 border-l-4 border-primary' : ''}" data-exec-row="${item.execution_id}">
                  <td class="py-2.5 px-3 font-code-sm text-code-sm text-primary font-semibold">${item.execution_id}</td>
                  <td class="py-2.5 px-3 font-title-md text-body-sm text-on-surface">${item.agent_name}</td>
                  <td class="py-2.5 px-3 text-on-surface-variant truncate max-w-xs md:max-w-md" title="${item.task_preview}">${item.task_preview}</td>
                  <td class="py-2.5 px-3 font-code-sm text-label-sm text-on-surface-variant">${item.model}</td>
                  <td class="py-2.5 px-3">
                    <span class="px-2 py-0.5 rounded-full font-code-sm text-label-sm ${stateBadgeStyle}">
                      ${item.state}
                    </span>
                  </td>
                  <td class="py-2.5 px-3 text-right font-code-sm text-body-sm text-on-surface tabular-nums">${item.total_tokens.toLocaleString()}</td>
                  <td class="py-2.5 px-3 text-right font-code-sm text-body-sm text-tertiary font-medium tabular-nums">$${item.cost_usd.toFixed(3)}</td>
                  <td class="py-2.5 px-3 text-right font-code-sm text-body-sm text-on-surface-variant tabular-nums">${item.runtime_formatted}</td>
                  <td class="py-2.5 px-3 text-center">
                    <button class="px-2 py-1 rounded bg-surface-container-high hover:bg-surface-container-highest text-primary font-code-sm text-label-sm transition-colors border border-outline-variant/20 select-exec-btn" data-exec-id="${item.execution_id}">
                      ${isSelected ? 'Active' : 'Inspect'}
                    </button>
                  </td>
                </tr>
              `;
            }).join("")}
          </tbody>
        </table>
      </div>
    </div>
  `;
}
