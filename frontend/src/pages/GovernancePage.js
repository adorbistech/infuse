/**
 * Governance / Policy Settings Page Assembler.
 */

import { renderPolicyForm } from "../components/PolicyForm.js";

export function renderGovernancePage(store) {
  const policyData = store.state.policyData;
  if (!policyData) {
    return `<div class="p-8 text-center text-on-surface-variant font-code-sm">Loading governance policy...</div>`;
  }

  return `
    <div class="space-y-4">
      ${renderPolicyForm(policyData)}
    </div>
  `;
}
