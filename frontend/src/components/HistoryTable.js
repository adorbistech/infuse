/**
 * Execution History Table Component.
 */

export function renderHistoryTable(historyItems) {
  return `
    <div class="bg-surface-container rounded-xl p-4 shadow-sm flex flex-col gap-3 border border-outline-variant/15">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div class="flex items-center gap-2">
          <span class="material-symbols-outlined text-[18px] text-primary">view_list</span>
          <h2 class="font-title-md text-title-md text-on-surface">Execution History</h2>
        </div>
        <div class="flex items-center gap-2">
          <input 
            type="text" 
            placeholder="Search executions..." 
            class="h-8 px-3 rounded-lg bg-surface-container-low text-on-surface font-code-sm text-code-sm placeholder-on-surface-variant/50 focus:outline-none focus:ring-1 focus:ring-primary border border-outline-variant/20"
          />
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
            </tr>
          </thead>
          <tbody class="divide-y divide-outline-variant/10">
            ${historyItems.map((item) => `
              <tr class="hover:bg-surface-container-high/50 transition-colors">
                <td class="py-2.5 px-3 font-code-sm text-code-sm text-primary font-semibold">${item.execution_id}</td>
                <td class="py-2.5 px-3 font-title-md text-body-sm text-on-surface">${item.agent_name}</td>
                <td class="py-2.5 px-3 text-on-surface-variant truncate max-w-xs" title="${item.task_preview}">${item.task_preview}</td>
                <td class="py-2.5 px-3 font-code-sm text-label-sm text-on-surface-variant">${item.model}</td>
                <td class="py-2.5 px-3">
                  <span class="px-2 py-0.5 rounded-full font-code-sm text-label-sm ${
                    item.state === 'NORMAL' ? 'bg-emerald-500/15 text-emerald-400' :
                    item.state === 'COST_PRESSURE' ? 'bg-tertiary-container text-on-tertiary' :
                    item.state === 'RUNAWAY' ? 'bg-error-container text-error' :
                    item.state === 'QUALITY_DEGRADED' ? 'bg-secondary-container text-secondary' :
                    'bg-surface-container-highest text-outline'
                  }">
                    ${item.state}
                  </span>
                </td>
                <td class="py-2.5 px-3 text-right font-code-sm text-body-sm text-on-surface">${item.total_tokens.toLocaleString()}</td>
                <td class="py-2.5 px-3 text-right font-code-sm text-body-sm text-tertiary font-medium">$${item.cost_usd.toFixed(3)}</td>
                <td class="py-2.5 px-3 text-right font-code-sm text-body-sm text-on-surface-variant">${item.runtime_formatted}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    </div>
  `;
}
