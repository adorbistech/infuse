/**
 * Governor Panel Component (Active regulation banner, rationale callout, decisions list).
 */

export function renderGovernorPanel(governor) {
  return `
    <div class="bg-surface-container rounded-xl p-4 shadow-sm flex flex-col gap-3 border border-outline-variant/15">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <span class="w-6 h-6 rounded-md bg-primary/10 flex items-center justify-center text-primary">
            <span class="material-symbols-outlined text-[16px]">gavel</span>
          </span>
          <h2 class="font-title-md text-title-md text-on-surface">Execution Governor</h2>
        </div>
        <span class="font-code-sm text-code-sm text-on-surface-variant">Sole Control Authority</span>
      </div>

      <!-- Active Action Banner -->
      <div class="bg-surface-container-high p-3 rounded-lg flex items-center justify-between border-l-4 border-primary">
        <div class="flex items-center gap-2.5">
          <span class="px-2 py-0.5 rounded bg-primary/15 text-primary font-code-sm text-code-sm font-semibold uppercase">
            ${governor.current_action}
          </span>
          <div>
            <div class="font-title-md text-body-md text-on-surface">${governor.action_banner_title}</div>
            <div class="font-body-sm text-body-sm text-on-surface-variant">${governor.action_banner_description}</div>
          </div>
        </div>
        <div class="text-right">
          <span class="font-label-sm text-label-sm text-on-surface-variant block uppercase">Trigger Reason</span>
          <span class="font-code-sm text-code-sm text-tertiary font-medium">${governor.reason_codes[0] || 'STANDARD_EVALUATION'}</span>
        </div>
      </div>

      <!-- Previous Decisions List -->
      <div class="space-y-1.5 pt-1">
        <span class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wide">Recent Governor Decision Log</span>
        <div class="space-y-1">
          ${governor.recent_decisions.map(d => `
            <div class="bg-surface-container-low p-2 rounded-lg flex items-center justify-between text-body-sm">
              <div class="flex items-center gap-2">
                <span class="font-code-sm text-label-sm text-on-surface-variant">${d.time}</span>
                <span class="px-1.5 py-0.2 rounded font-code-sm text-label-sm bg-surface-container-highest text-primary font-medium">${d.action}</span>
                <span class="text-on-surface">${d.reason}</span>
              </div>
              <span class="font-code-sm text-label-sm text-on-surface-variant">Applied</span>
            </div>
          `).join("")}
        </div>
      </div>
    </div>
  `;
}
