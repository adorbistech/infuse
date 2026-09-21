/**
 * Execution Timeline Component.
 */

export function renderTimeline(timelineEvents) {
  return `
    <div class="bg-surface-container rounded-xl p-4 shadow-sm flex flex-col gap-3 border border-outline-variant/15">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <span class="material-symbols-outlined text-[18px] text-primary">history</span>
          <h2 class="font-title-md text-title-md text-on-surface">Execution Timeline</h2>
        </div>
        <span class="font-code-sm text-code-sm text-on-surface-variant">${timelineEvents.length} events logged</span>
      </div>

      <div class="relative pl-6 space-y-3.5 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-surface-container-highest">
        ${timelineEvents.map((evt, idx) => {
          let dotColor = "bg-primary";
          let badgeHtml = "";
          if (evt.is_state_change) {
            dotColor = "bg-tertiary";
            badgeHtml = `<span class="px-1.5 py-0.2 rounded font-code-sm text-label-sm bg-tertiary-container text-on-tertiary font-semibold ml-2">${evt.badge_label || 'STATE CHANGE'}</span>`;
          } else if (evt.is_governor_decision) {
            dotColor = "bg-primary-container";
            badgeHtml = `<span class="px-1.5 py-0.2 rounded font-code-sm text-label-sm bg-primary/20 text-primary font-semibold ml-2">${evt.badge_label || 'GOVERNOR'}</span>`;
          }

          return `
            <div class="relative flex flex-col gap-0.5">
              <span class="absolute -left-6 top-1 w-2.5 h-2.5 rounded-full ${dotColor} ring-4 ring-surface-container"></span>
              <div class="flex items-center justify-between">
                <div class="flex items-center">
                  <span class="font-title-md text-body-md text-on-surface font-semibold">${evt.title}</span>
                  ${badgeHtml}
                </div>
                <span class="font-code-sm text-label-sm text-on-surface-variant">${evt.time_offset}</span>
              </div>
              <p class="font-body-sm text-body-sm text-on-surface-variant">${evt.description}</p>
            </div>
          `;
        }).join("")}
      </div>
    </div>
  `;
}
