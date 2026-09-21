/**
 * Execution Activity Panel Component (Web, Tools, File ops, Retries).
 */

export function renderActivityPanel(metrics) {
  return `
    <div class="bg-surface-container rounded-xl p-4 shadow-sm border border-outline-variant/15">
      <h3 class="font-title-md text-title-md text-on-surface mb-2">Execution Activity</h3>
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-2">
        <div class="bg-surface-container-low p-2.5 rounded-lg flex items-center gap-2.5">
          <div class="w-7 h-7 rounded bg-surface-container-high flex items-center justify-center text-primary">
            <span class="material-symbols-outlined text-[16px]">language</span>
          </div>
          <div>
            <div class="font-label-sm text-label-sm text-on-surface-variant">Web Activity</div>
            <div class="font-title-md text-body-md text-on-surface font-semibold">${metrics.web_requests_count} calls <span class="font-code-sm text-label-sm text-on-surface-variant font-normal">(2.4MB)</span></div>
          </div>
        </div>

        <div class="bg-surface-container-low p-2.5 rounded-lg flex items-center gap-2.5">
          <div class="w-7 h-7 rounded bg-surface-container-high flex items-center justify-center text-secondary">
            <span class="material-symbols-outlined text-[16px]">terminal</span>
          </div>
          <div>
            <div class="font-label-sm text-label-sm text-on-surface-variant">Tool Invocations</div>
            <div class="font-title-md text-body-md text-on-surface font-semibold">${metrics.tool_calls_count} executed</div>
          </div>
        </div>

        <div class="bg-surface-container-low p-2.5 rounded-lg flex items-center gap-2.5">
          <div class="w-7 h-7 rounded bg-surface-container-high flex items-center justify-center text-primary-container">
            <span class="material-symbols-outlined text-[16px]">folder</span>
          </div>
          <div>
            <div class="font-label-sm text-label-sm text-on-surface-variant">File Operations</div>
            <div class="font-title-md text-body-md text-on-surface font-semibold">18 reads <span class="font-code-sm text-label-sm text-on-surface-variant font-normal">/ 3 writes</span></div>
          </div>
        </div>

        <div class="bg-surface-container-low p-2.5 rounded-lg flex items-center gap-2.5">
          <div class="w-7 h-7 rounded bg-surface-container-high flex items-center justify-center text-tertiary">
            <span class="material-symbols-outlined text-[16px]">replay</span>
          </div>
          <div>
            <div class="font-label-sm text-label-sm text-on-surface-variant">Retries / Backoffs</div>
            <div class="font-title-md text-body-md text-on-surface font-semibold">${metrics.retries_count} handled</div>
          </div>
        </div>
      </div>
    </div>
  `;
}
