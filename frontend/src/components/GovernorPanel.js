/**
 * Governor Panel Component (Hardened).
 */

import { GovernorAction } from "../contracts/viewmodels.js";

export function renderGovernorPanel(governor) {
  const actionStyles = {
    [GovernorAction.CONTINUE]: {
      badge: "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30",
      border: "border-emerald-500"
    },
    [GovernorAction.OPTIMIZE]: {
      badge: "bg-primary/15 text-primary border border-primary/30",
      border: "border-primary"
    },
    [GovernorAction.ESCALATE]: {
      badge: "bg-secondary/20 text-secondary border border-secondary/40",
      border: "border-secondary"
    },
    [GovernorAction.DOWNGRADE]: {
      badge: "bg-tertiary/20 text-tertiary border border-tertiary/40",
      border: "border-tertiary"
    },
    [GovernorAction.SWITCH]: {
      badge: "bg-primary-container text-on-primary-container font-semibold",
      border: "border-primary-container"
    },
    [GovernorAction.THROTTLE]: {
      badge: "bg-tertiary-container text-on-tertiary font-semibold",
      border: "border-tertiary-container"
    },
    [GovernorAction.STOP]: {
      badge: "bg-error-container text-error font-semibold border border-error/50",
      border: "border-error"
    }
  };

  const currentAction = governor.current_action || GovernorAction.CONTINUE;
  const currentStyle = actionStyles[currentAction] || actionStyles[GovernorAction.CONTINUE];

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
      <div class="bg-surface-container-high p-3 rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-l-4 ${currentStyle.border}">
        <div class="flex items-center gap-2.5">
          <span class="px-2.5 py-1 rounded font-code-sm text-code-sm font-semibold uppercase ${currentStyle.badge}">
            ${currentAction}
          </span>
          <div>
            <div class="font-title-md text-body-md text-on-surface font-semibold">${governor.action_banner_title}</div>
            <div class="font-body-sm text-body-sm text-on-surface-variant">${governor.action_banner_description}</div>
          </div>
        </div>
        <div class="text-left sm:text-right">
          <span class="font-label-sm text-label-sm text-on-surface-variant block uppercase">Trigger Reason</span>
          <span class="font-code-sm text-code-sm text-tertiary font-medium">${governor.reason_codes[0] || 'STANDARD_EVALUATION'}</span>
        </div>
      </div>

      <!-- Previous Decisions List -->
      <div class="space-y-1.5 pt-1">
        <span class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wide">Recent Governor Decision Log</span>
        <div class="space-y-1">
          ${(governor.recent_decisions || []).map(d => {
            const itemStyle = actionStyles[d.action] || actionStyles[GovernorAction.CONTINUE];
            return `
              <div class="bg-surface-container-low p-2 rounded-lg flex items-center justify-between text-body-sm border border-outline-variant/10">
                <div class="flex items-center gap-2">
                  <span class="font-code-sm text-label-sm text-on-surface-variant tabular-nums">${d.time}</span>
                  <span class="px-1.5 py-0.2 rounded font-code-sm text-label-sm ${itemStyle.badge} font-medium">${d.action}</span>
                  <span class="text-on-surface">${d.reason}</span>
                </div>
                <span class="font-code-sm text-label-sm text-emerald-400 font-medium">Applied</span>
              </div>
            `;
          }).join("")}
        </div>
      </div>
    </div>
  `;
}
