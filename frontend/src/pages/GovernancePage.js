/**
 * Governance / Policy Settings Page Assembler (Hardened).
 * 
 * Supports Loading, Error, Empty, and Loaded states.
 */

import { renderPolicyForm } from "../components/PolicyForm.js";
import { DataStatus } from "../contracts/viewmodels.js";

export function renderGovernancePage(store) {
  const status = store.state.status;
  const error = store.state.error;
  const policyData = store.state.policyData;

  // 1. Error State
  if (status === DataStatus.ERROR || error) {
    return `
      <div id="governance-error-state" class="glass-panel p-8 rounded-xl border border-error/30 bg-error/10 text-center space-y-4 max-w-2xl mx-auto my-12">
        <div class="inline-flex p-3 rounded-full bg-error/20 text-error mb-2">
          <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
        </div>
        <h2 class="font-headline text-lg font-bold text-on-surface">Governance Policy Unavailable</h2>
        <p class="text-on-surface-variant text-sm font-code-sm max-w-md mx-auto">
          ${error?.message || "Failed to load governance policy."}
        </p>
        ${error?.code ? `<div class="text-xs text-error/80 font-code-sm">Error Code: ${error.code}</div>` : ""}
        <div class="pt-2">
          <button id="retry-gov-btn" class="px-5 py-2 rounded-lg bg-surface-container-highest hover:bg-surface-container-high text-on-surface text-xs font-semibold uppercase tracking-wider transition-colors shadow">
            Retry Loading Policy
          </button>
        </div>
      </div>
    `;
  }

  // 2. Loading State
  if (status === DataStatus.LOADING || (!policyData && status !== DataStatus.EMPTY)) {
    return `
      <div id="governance-loading-state" class="space-y-4 animate-pulse">
        <div class="h-28 bg-surface-container-highest/40 rounded-xl"></div>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="h-44 bg-surface-container-highest/30 rounded-xl"></div>
          <div class="h-44 bg-surface-container-highest/30 rounded-xl"></div>
          <div class="h-44 bg-surface-container-highest/30 rounded-xl"></div>
          <div class="h-44 bg-surface-container-highest/30 rounded-xl"></div>
        </div>
        <div class="p-8 text-center text-on-surface-variant font-code-sm">
          <span class="inline-block animate-spin mr-2">⟳</span> Loading governance policy...
        </div>
      </div>
    `;
  }

  // 3. Empty State
  if (status === DataStatus.EMPTY || !policyData) {
    return `
      <div id="governance-empty-state" class="glass-panel p-12 rounded-xl text-center space-y-4 max-w-lg mx-auto my-12 border border-outline-variant/20">
        <div class="text-4xl text-on-surface-variant">⚖</div>
        <h2 class="font-headline text-lg font-bold text-on-surface">No Governance Policy Configured</h2>
        <p class="text-on-surface-variant text-sm font-code-sm">
          No active governance policy was returned by the data provider.
        </p>
        <div class="pt-2">
          <button id="retry-gov-btn" class="px-5 py-2 rounded-lg bg-primary text-on-primary text-xs font-semibold uppercase tracking-wider transition-colors shadow">
            Initialize Default Policy
          </button>
        </div>
      </div>
    `;
  }

  return `
    <div class="space-y-4">
      ${renderPolicyForm(policyData, store.state.policyFeedback)}
    </div>
  `;
}
