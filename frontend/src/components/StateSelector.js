/**
 * State Selector & Status Indicator Component (Hardened).
 */

import { ExecutionState } from "../contracts/viewmodels.js";

export function renderStateSelector(stateViewModel) {
  const currentState = stateViewModel.current_state;

  const stateStyles = {
    [ExecutionState.NORMAL]: {
      badgeBg: "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30",
      dot: "bg-emerald-400",
      pillActive: "bg-emerald-500/20 text-emerald-300 font-semibold border border-emerald-500/50 shadow-sm",
      headerBorder: "border-emerald-500/20"
    },
    [ExecutionState.COST_PRESSURE]: {
      badgeBg: "bg-tertiary-container text-on-tertiary font-semibold border border-tertiary/40",
      dot: "bg-tertiary-container",
      pillActive: "bg-tertiary-container text-on-tertiary font-semibold shadow-sm border border-tertiary/50",
      headerBorder: "border-tertiary-container/30"
    },
    [ExecutionState.RUNAWAY]: {
      badgeBg: "bg-error-container text-error font-semibold border border-error/40",
      dot: "bg-error",
      pillActive: "bg-error-container text-error font-semibold border border-error/60 shadow-sm",
      headerBorder: "border-error/30"
    },
    [ExecutionState.QUALITY_DEGRADED]: {
      badgeBg: "bg-secondary-container text-secondary font-semibold border border-secondary/40",
      dot: "bg-secondary",
      pillActive: "bg-secondary-container text-secondary font-semibold border border-secondary/50 shadow-sm",
      headerBorder: "border-secondary/30"
    },
    [ExecutionState.PROVIDER_CONSTRAINED]: {
      badgeBg: "bg-surface-container-highest text-outline font-semibold border border-outline/40",
      dot: "bg-outline",
      pillActive: "bg-surface-container-highest text-primary font-semibold border border-primary/50 shadow-sm",
      headerBorder: "border-primary/25"
    }
  };

  const currentStyle = stateStyles[currentState] || stateStyles[ExecutionState.NORMAL];

  const states = [
    { key: ExecutionState.NORMAL, label: "NORMAL", dotColor: "bg-emerald-400" },
    { key: ExecutionState.COST_PRESSURE, label: "COST PRESSURE", dotColor: "bg-on-tertiary" },
    { key: ExecutionState.RUNAWAY, label: "RUNAWAY", dotColor: "bg-error" },
    { key: ExecutionState.QUALITY_DEGRADED, label: "QUALITY DEGRADED", dotColor: "bg-secondary" },
    { key: ExecutionState.PROVIDER_CONSTRAINED, label: "PROVIDER CONSTRAINED", dotColor: "bg-outline" }
  ];

  return `
    <div class="bg-surface-container-high rounded-xl p-4 shadow-sm flex flex-col gap-3 border ${currentStyle.headerBorder} transition-colors">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div class="flex items-center gap-2.5">
          <span class="flex h-3.5 w-3.5 relative">
            <span class="animate-ping absolute inline-flex h-full w-full rounded-full ${currentStyle.dot} opacity-75"></span>
            <span class="relative inline-flex rounded-full h-3.5 w-3.5 ${currentStyle.dot}"></span>
          </span>
          <span class="font-title-md text-title-md text-on-surface uppercase tracking-wide">Execution State</span>
          <span class="px-2.5 py-0.5 rounded-full ${currentStyle.badgeBg} font-label-sm text-label-sm tracking-wider">
            ${stateViewModel.state_display_name}
          </span>
        </div>
        <div class="flex items-center gap-2">
          <span class="font-code-sm text-code-sm text-tertiary font-medium">
            Policy boundary threshold: ${stateViewModel.policy_boundary_threshold_percent}% consumed
          </span>
        </div>
      </div>
      <p class="font-body-md text-body-md text-on-surface-variant">
        ${stateViewModel.description}
      </p>

      <!-- Active Reason Codes -->
      ${stateViewModel.reason_codes.length > 0 ? `
        <div class="flex flex-wrap items-center gap-1.5 pt-0.5">
          <span class="font-label-sm text-label-sm text-on-surface-variant uppercase">Signals:</span>
          ${stateViewModel.reason_codes.map(rc => `
            <span class="px-2 py-0.5 rounded font-code-sm text-label-sm bg-surface-container text-primary border border-outline-variant/20">
              ${rc}
            </span>
          `).join("")}
        </div>
      ` : ''}

      <!-- State Pills Selector -->
      <div class="flex flex-wrap gap-2 pt-1 border-t border-outline-variant/15" id="statePillsGroup" role="group" aria-label="Simulate Execution State">
        ${states.map(s => {
          const isActive = s.key === currentState;
          return `
            <button 
              class="state-pill px-3 py-1.5 rounded-lg text-label-sm font-label-sm transition-all ${
                isActive 
                  ? currentStyle.pillActive 
                  : 'bg-surface-container text-on-surface-variant hover:text-on-surface hover:bg-surface-container-highest border border-transparent'
              }" 
              data-state="${s.key}"
              type="button"
              aria-pressed="${isActive}">
              <span class="inline-block w-1.5 h-1.5 rounded-full ${s.dotColor} mr-1.5"></span>
              ${s.label}
            </button>
          `;
        }).join("")}
      </div>
    </div>
  `;
}
