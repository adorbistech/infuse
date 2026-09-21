/**
 * State Selector & Status Indicator Component.
 */

import { ExecutionState } from "../contracts/viewmodels.js";

export function renderStateSelector(stateViewModel) {
  const currentState = stateViewModel.current_state;

  const stateStyles = {
    [ExecutionState.NORMAL]: {
      badgeBg: "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30",
      dot: "bg-emerald-400",
      pillActive: "bg-emerald-500/20 text-emerald-300 font-semibold border border-emerald-500/40"
    },
    [ExecutionState.COST_PRESSURE]: {
      badgeBg: "bg-tertiary-container text-on-tertiary font-semibold",
      dot: "bg-tertiary-container",
      pillActive: "bg-tertiary-container text-on-tertiary font-semibold shadow-sm"
    },
    [ExecutionState.RUNAWAY]: {
      badgeBg: "bg-error-container text-error font-semibold border border-error/30",
      dot: "bg-error",
      pillActive: "bg-error-container text-error font-semibold border border-error/50 shadow-sm"
    },
    [ExecutionState.QUALITY_DEGRADED]: {
      badgeBg: "bg-secondary-container text-secondary font-semibold border border-secondary/30",
      dot: "bg-secondary",
      pillActive: "bg-secondary-container text-secondary font-semibold shadow-sm"
    },
    [ExecutionState.PROVIDER_CONSTRAINED]: {
      badgeBg: "bg-surface-container-highest text-outline font-semibold border border-outline/30",
      dot: "bg-outline",
      pillActive: "bg-surface-container-highest text-primary font-semibold border border-primary/40 shadow-sm"
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
    <div class="bg-surface-container-high rounded-xl p-4 shadow-sm flex flex-col gap-3 border border-outline-variant/20">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div class="flex items-center gap-2.5">
          <span class="flex h-3 w-3 relative">
            <span class="animate-ping absolute inline-flex h-full w-full rounded-full ${currentStyle.dot} opacity-75"></span>
            <span class="relative inline-flex rounded-full h-3 w-3 ${currentStyle.dot}"></span>
          </span>
          <span class="font-title-md text-title-md text-on-surface uppercase tracking-wide">Execution State</span>
          <span class="px-2.5 py-0.5 rounded-full ${currentStyle.badgeBg} font-label-sm text-label-sm tracking-wider">
            ${stateViewModel.state_display_name}
          </span>
        </div>
        <span class="font-code-sm text-code-sm text-tertiary font-medium">
          Policy boundary threshold: ${stateViewModel.policy_boundary_threshold_percent}% consumed
        </span>
      </div>
      <p class="font-body-md text-body-md text-on-surface-variant">
        ${stateViewModel.description}
      </p>

      <!-- State Pills Selector -->
      <div class="flex flex-wrap gap-2 pt-1" id="statePillsGroup">
        ${states.map(s => {
          const isActive = s.key === currentState;
          return `
            <button 
              class="state-pill px-2.5 py-1 rounded-md text-label-sm font-label-sm transition-all ${
                isActive 
                  ? currentStyle.pillActive 
                  : 'bg-surface-container text-on-surface-variant hover:text-on-surface hover:bg-surface-container-highest'
              }" 
              data-state="${s.key}">
              <span class="inline-block w-1.5 h-1.5 rounded-full ${s.dotColor} mr-1.5"></span>
              ${s.label}
            </button>
          `;
        }).join("")}
      </div>
    </div>
  `;
}
