/**
 * Governance Policy Configuration Form Component (10 Sections Hardened).
 * 
 * Provides full UI representation of the 10 Governance Policy sections.
 * Strictly represents policy boundaries without performing runtime enforcement.
 */

import { GovernorAction } from "../contracts/viewmodels.js";

export const ACTION_OPTIONS = [
  { value: GovernorAction.CONTINUE, label: "CONTINUE — Permit execution without intervention" },
  { value: GovernorAction.OPTIMIZE, label: "OPTIMIZE — Compress prompts & reduce context window" },
  { value: GovernorAction.ESCALATE, label: "ESCALATE — Elevate model tier / reasoning depth" },
  { value: GovernorAction.DOWNGRADE, label: "DOWNGRADE — Route to lower-cost model tier" },
  { value: GovernorAction.SWITCH, label: "SWITCH — Dynamic failover to backup provider" },
  { value: GovernorAction.THROTTLE, label: "THROTTLE — Rate-limit request pacing" },
  { value: GovernorAction.STOP, label: "STOP — Hard circuit-breaker termination" }
];

/**
 * Render a canonical Governor Action badge for tables and previews.
 */
export function renderGovernorActionBadge(action) {
  switch (action) {
    case GovernorAction.CONTINUE:
      return `<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-code-sm font-semibold bg-surface-container-highest text-on-surface border border-outline-variant/30">CONTINUE</span>`;
    case GovernorAction.OPTIMIZE:
      return `<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-code-sm font-semibold bg-primary/15 text-primary border border-primary/30">OPTIMIZE</span>`;
    case GovernorAction.ESCALATE:
      return `<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-code-sm font-semibold bg-secondary-container/60 text-on-secondary-container border border-secondary-container">ESCALATE</span>`;
    case GovernorAction.DOWNGRADE:
      return `<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-code-sm font-semibold bg-surface-container-high text-on-surface-variant border border-outline-variant/20">DOWNGRADE</span>`;
    case GovernorAction.SWITCH:
      return `<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-code-sm font-semibold bg-primary-container text-on-primary-container border border-primary-container">SWITCH</span>`;
    case GovernorAction.THROTTLE:
      return `<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-code-sm font-semibold bg-tertiary-container/30 text-tertiary border border-tertiary-container/50">THROTTLE</span>`;
    case GovernorAction.STOP:
      return `<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-code-sm font-semibold bg-error-container text-error border border-error/40">STOP</span>`;
    default:
      return `<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-code-sm bg-surface-container-high text-on-surface-variant">${action || "UNKNOWN"}</span>`;
  }
}

export function renderPolicyForm(policyViewModel, feedback = null) {
  const policy = policyViewModel.policy || {};
  const budget = policy.budget || {};
  const tokens = policy.tokens || {};
  const requests = policy.requests || {};
  const runtime = policy.runtime || {};
  const providers = policy.providers || {};
  const web = policy.web || {};
  const tools = policy.tools || {};
  const retries = policy.retries || {};
  const anomaly = policy.anomaly || {};
  const actions = policy.actions || {};
  const hasUnsaved = !!policyViewModel.has_unsaved_changes;
  const validationErrors = policyViewModel.validation_errors || [];

  const allowedProvidersList = Array.isArray(providers.allowed_providers) 
    ? providers.allowed_providers 
    : ["anthropic", "openai", "gemini", "deepseek"];

  const renderSelect = (name, currentValue) => `
    <div class="relative">
      <select name="${name}" id="${name}" class="w-full h-10 px-3 pr-9 rounded-lg bg-surface-container-lowest text-on-surface font-label-md text-label-md appearance-none focus:outline-none focus:ring-1 focus:ring-primary border border-outline-variant/20">
        ${ACTION_OPTIONS.map(opt => `
          <option value="${opt.value}" ${opt.value === currentValue ? 'selected' : ''}>${opt.label}</option>
        `).join("")}
      </select>
      <span class="material-symbols-outlined absolute right-3 top-2.5 text-on-surface-variant pointer-events-none text-[18px]">expand_more</span>
    </div>
  `;

  return `
    <div class="space-y-4">
      <!-- Page Header -->
      <header class="flex flex-col space-y-1 bg-surface-container-low p-4 rounded-xl border border-outline-variant/20">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-2">
            <span class="material-symbols-outlined text-primary text-[22px]" aria-hidden="true">shield</span>
            <h1 class="font-headline-lg-mobile text-headline-lg-mobile text-on-surface tracking-tight">Governance</h1>
          </div>
          <div class="flex items-center gap-2">
            ${hasUnsaved ? `
              <span class="px-2.5 py-1 rounded-full bg-tertiary-container/30 text-tertiary font-code-sm text-code-sm flex items-center gap-1.5 border border-tertiary/40">
                <span class="w-1.5 h-1.5 rounded-full bg-tertiary animate-ping"></span>
                Unsaved Draft
              </span>
            ` : `
              <span class="px-2.5 py-1 rounded-full bg-surface-container-high text-primary font-code-sm text-code-sm uppercase tracking-wider flex items-center gap-1.5 shadow-sm">
                <span class="w-1.5 h-1.5 rounded-full bg-primary animate-pulse"></span>
                Runtime Guard
              </span>
            `}
          </div>
        </div>
        <p class="font-body-md text-body-md text-on-surface-variant">
          Define execution boundaries, token budgets, and deterministic Governor actions for autonomous agents.
        </p>
      </header>

      <!-- Feedback Alert Banner -->
      ${feedback ? `
        <div class="p-3.5 rounded-xl border flex items-center justify-between gap-3 ${
          feedback.type === 'error' 
            ? 'bg-error-container/20 border-error/40 text-error' 
            : feedback.type === 'info'
            ? 'bg-secondary-container/20 border-secondary-container text-secondary'
            : 'bg-primary/10 border-primary/30 text-primary'
        }" id="policy-feedback-banner" role="alert">
          <div class="flex items-center gap-2.5 font-body-sm text-body-sm">
            <span class="material-symbols-outlined text-[20px]">${feedback.type === 'error' ? 'error' : 'check_circle'}</span>
            <span>${feedback.message}</span>
          </div>
          <button type="button" id="dismiss-feedback-btn" class="text-on-surface-variant hover:text-on-surface p-1 rounded transition-colors" aria-label="Dismiss message">
            <span class="material-symbols-outlined text-[18px]">close</span>
          </button>
        </div>
      ` : ''}

      <!-- Validation Errors Banner -->
      ${validationErrors.length > 0 ? `
        <div class="p-3.5 rounded-xl bg-error-container/20 border border-error/40 text-error space-y-1.5" role="alert">
          <div class="flex items-center gap-2 font-title-md text-title-md font-semibold">
            <span class="material-symbols-outlined text-[20px]">warning</span>
            <span>Policy Validation Issues</span>
          </div>
          <ul class="list-disc list-inside space-y-0.5 font-code-sm text-code-sm pl-1">
            ${validationErrors.map(err => `<li>${err}</li>`).join('')}
          </ul>
        </div>
      ` : ''}

      <!-- Active Policy Overview Card -->
      <section class="w-full rounded-xl bg-surface-container p-4 space-y-3.5 shadow-md border border-outline-variant/15" aria-labelledby="policy-overview-title">
        <div class="flex items-start justify-between">
          <div class="space-y-1">
            <div class="flex items-center gap-2">
              <span id="policy-overview-title" class="font-title-md text-title-md text-on-surface">${policy.name || 'Default Execution Policy'}</span>
              <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full ${hasUnsaved ? 'bg-tertiary/15 text-tertiary' : 'bg-primary/15 text-primary'} font-label-sm text-label-sm">
                <span class="w-1.5 h-1.5 rounded-full ${hasUnsaved ? 'bg-tertiary' : 'bg-primary'}"></span>
                ${hasUnsaved ? 'Draft Mode' : 'Active'}
              </span>
            </div>
            <div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-on-surface-variant font-code-sm text-code-sm">
              <span>Ver: <strong class="text-on-surface">${policy.version || 'v1.0.4'}</strong></span>
              <span>•</span>
              <span>Policy ID: <strong class="text-primary">${policy.policy_id || 'pol_default'}</strong></span>
              <span>•</span>
              <span>Last Saved: <span class="text-on-surface">${policyViewModel.last_saved_at || 'Just now'}</span></span>
            </div>
          </div>
          <div class="w-9 h-9 rounded-lg bg-surface-container-high flex items-center justify-center text-primary" aria-hidden="true">
            <span class="material-symbols-outlined text-[20px]">verified_user</span>
          </div>
        </div>

        <!-- Strictness Indicator -->
        <div class="space-y-1 pt-1">
          <div class="flex justify-between font-label-sm text-label-sm text-on-surface-variant">
            <span>Guardrail Enforcement Index</span>
            <span class="font-code-sm text-code-sm text-primary font-semibold">${policyViewModel.guardrail_strictness_index || '99.98% Strict'}</span>
          </div>
          <div class="w-full h-1.5 rounded-full bg-surface-container-lowest overflow-hidden">
            <div class="h-full rounded-full bg-primary w-[98%] transition-all duration-500"></div>
          </div>
        </div>

        <!-- Action Controls Bar -->
        <div class="flex flex-wrap items-center gap-2 pt-1">
          <button class="flex-1 min-w-[140px] h-9 rounded-lg bg-primary text-on-primary font-label-md text-label-md font-semibold flex items-center justify-center gap-1.5 shadow-sm active:opacity-90 hover:brightness-110 transition-all focus:outline-none focus:ring-2 focus:ring-primary" id="save-policy-btn" type="button" aria-label="Save Active Policy">
            <span class="material-symbols-outlined text-[18px]">save</span>
            Save Active Policy
          </button>
          
          <button class="flex-1 min-w-[140px] h-9 rounded-lg ${hasUnsaved ? 'bg-error-container/30 text-error border border-error/40 hover:bg-error-container/50' : 'bg-surface-container-high text-on-surface-variant opacity-60 cursor-not-allowed'} font-label-md text-label-md flex items-center justify-center gap-1.5 transition-colors focus:outline-none focus:ring-1 focus:ring-error" id="cancel-policy-btn" type="button" ${hasUnsaved ? '' : 'disabled'} aria-label="Cancel or reset unsaved policy changes">
            <span class="material-symbols-outlined text-[18px]">undo</span>
            Reset Changes
          </button>

          <button class="flex-1 min-w-[140px] h-9 rounded-lg bg-surface-container-high text-on-surface font-label-md text-label-md flex items-center justify-center gap-1.5 hover:bg-surface-container-highest transition-colors focus:outline-none focus:ring-1 focus:ring-primary" id="duplicate-policy-btn" type="button" aria-label="Duplicate policy as new revision draft">
            <span class="material-symbols-outlined text-[18px]">content_copy</span>
            Duplicate Policy
          </button>
        </div>
      </section>

      <!-- Policy Formulation Form -->
      <form class="space-y-4" id="governance-form" onsubmit="event.preventDefault();">
        
        <!-- Section 1: Budget Controls -->
        <section class="rounded-xl bg-surface-container p-4 space-y-3.5 shadow-sm border border-outline-variant/15" aria-labelledby="section-budget-title">
          <div class="flex items-center justify-between">
            <div class="flex items-center space-x-2">
              <span class="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center text-primary" aria-hidden="true">
                <span class="material-symbols-outlined text-[18px]">attach_money</span>
              </span>
              <div>
                <h2 id="section-budget-title" class="font-title-md text-title-md text-on-surface">1. Budget Controls</h2>
                <p class="font-body-sm text-body-sm text-on-surface-variant">Define financial limits and monetary spend ceilings.</p>
              </div>
            </div>
            <span class="font-code-sm text-code-sm px-2 py-0.5 rounded bg-surface-container-high text-on-surface-variant">${budget.currency || 'USD'} ($)</span>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-2.5 pt-1">
            <div class="space-y-1">
              <label for="max_cost_per_task" class="font-label-sm text-label-sm text-on-surface-variant">Max Cost / Task ($)</label>
              <input type="number" step="0.5" min="0" id="max_cost_per_task" name="max_cost_per_task" class="w-full h-10 px-3 rounded-lg bg-surface-container-lowest text-on-surface font-code-sm text-code-sm border border-outline-variant/20 focus:outline-none focus:ring-1 focus:ring-primary" value="${budget.max_cost_per_task ?? 10.00}" />
            </div>
            <div class="space-y-1">
              <label for="max_cost_per_day" class="font-label-sm text-label-sm text-on-surface-variant">Max Cost / Day ($)</label>
              <input type="number" step="10" min="0" id="max_cost_per_day" name="max_cost_per_day" class="w-full h-10 px-3 rounded-lg bg-surface-container-lowest text-on-surface font-code-sm text-code-sm border border-outline-variant/20 focus:outline-none focus:ring-1 focus:ring-primary" value="${budget.max_cost_per_day ?? 150.00}" />
            </div>
            <div class="space-y-1">
              <label for="max_cost_per_month" class="font-label-sm text-label-sm text-on-surface-variant">Max Cost / Month ($)</label>
              <input type="number" step="100" min="0" id="max_cost_per_month" name="max_cost_per_month" class="w-full h-10 px-3 rounded-lg bg-surface-container-lowest text-on-surface font-code-sm text-code-sm border border-outline-variant/20 focus:outline-none focus:ring-1 focus:ring-primary" value="${budget.max_cost_per_month ?? 2500.00}" />
            </div>
          </div>
          <div class="space-y-1.5 pt-1">
            <label for="budget_action" class="font-label-sm text-label-sm text-on-surface-variant">Action when budget limit reached</label>
            ${renderSelect("budget_action", actions.budget_action || GovernorAction.OPTIMIZE)}
          </div>
        </section>

        <!-- Section 2: Token Controls -->
        <section class="rounded-xl bg-surface-container p-4 space-y-3.5 shadow-sm border border-outline-variant/15" aria-labelledby="section-tokens-title">
          <div class="flex items-center justify-between">
            <div class="flex items-center space-x-2">
              <span class="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center text-primary" aria-hidden="true">
                <span class="material-symbols-outlined text-[18px]">toll</span>
              </span>
              <div>
                <h2 id="section-tokens-title" class="font-title-md text-title-md text-on-surface">2. Token Controls</h2>
                <p class="font-body-sm text-body-sm text-on-surface-variant">Set context window ceilings and prompt/output constraints.</p>
              </div>
            </div>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-2.5 pt-1">
            <div class="space-y-1">
              <label for="max_input_tokens" class="font-label-sm text-label-sm text-on-surface-variant">Max Input Tokens</label>
              <input type="number" step="1000" min="0" id="max_input_tokens" name="max_input_tokens" class="w-full h-10 px-3 rounded-lg bg-surface-container-lowest text-on-surface font-code-sm text-code-sm border border-outline-variant/20 focus:outline-none focus:ring-1 focus:ring-primary" value="${tokens.max_input_tokens ?? 128000}" />
            </div>
            <div class="space-y-1">
              <label for="max_output_tokens" class="font-label-sm text-label-sm text-on-surface-variant">Max Output Tokens</label>
              <input type="number" step="512" min="0" id="max_output_tokens" name="max_output_tokens" class="w-full h-10 px-3 rounded-lg bg-surface-container-lowest text-on-surface font-code-sm text-code-sm border border-outline-variant/20 focus:outline-none focus:ring-1 focus:ring-primary" value="${tokens.max_output_tokens ?? 8192}" />
            </div>
            <div class="space-y-1">
              <label for="max_total_tokens" class="font-label-sm text-label-sm text-on-surface-variant">Max Total Tokens</label>
              <input type="number" step="1000" min="0" id="max_total_tokens" name="max_total_tokens" class="w-full h-10 px-3 rounded-lg bg-surface-container-lowest text-on-surface font-code-sm text-code-sm border border-outline-variant/20 focus:outline-none focus:ring-1 focus:ring-primary" value="${tokens.max_total_tokens ?? 136192}" />
            </div>
          </div>
          <div class="space-y-1.5 pt-1">
            <label for="token_action" class="font-label-sm text-label-sm text-on-surface-variant">Action when token ceiling reached</label>
            ${renderSelect("token_action", actions.token_action || GovernorAction.OPTIMIZE)}
          </div>
        </section>

        <!-- Section 3: Request Controls -->
        <section class="rounded-xl bg-surface-container p-4 space-y-3.5 shadow-sm border border-outline-variant/15" aria-labelledby="section-requests-title">
          <div class="flex items-center space-x-2">
            <span class="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center text-primary" aria-hidden="true">
              <span class="material-symbols-outlined text-[18px]">speed</span>
            </span>
            <div>
              <h2 id="section-requests-title" class="font-title-md text-title-md text-on-surface">3. Request Controls</h2>
              <p class="font-body-sm text-body-sm text-on-surface-variant">Govern API request rates and task-level invocation limits.</p>
            </div>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-1">
            <div class="space-y-1">
              <label for="max_rpm" class="font-label-sm text-label-sm text-on-surface-variant">Max Requests / Minute (RPM)</label>
              <input type="number" min="1" id="max_rpm" name="max_rpm" class="w-full h-10 px-3 rounded-lg bg-surface-container-lowest text-on-surface font-code-sm text-code-sm border border-outline-variant/20 focus:outline-none focus:ring-1 focus:ring-primary" value="${requests.max_rpm ?? 60}" />
            </div>
            <div class="space-y-1">
              <label for="max_requests_per_task" class="font-label-sm text-label-sm text-on-surface-variant">Max Requests / Task</label>
              <input type="number" min="1" id="max_requests_per_task" name="max_requests_per_task" class="w-full h-10 px-3 rounded-lg bg-surface-container-lowest text-on-surface font-code-sm text-code-sm border border-outline-variant/20 focus:outline-none focus:ring-1 focus:ring-primary" value="${requests.max_requests_per_task ?? 25}" />
            </div>
          </div>
          <div class="space-y-1.5 pt-1">
            <label for="request_action" class="font-label-sm text-label-sm text-on-surface-variant">Action when request ceiling reached</label>
            ${renderSelect("request_action", actions.request_action || GovernorAction.THROTTLE)}
          </div>
        </section>

        <!-- Section 4: Runtime Controls -->
        <section class="rounded-xl bg-surface-container p-4 space-y-3.5 shadow-sm border border-outline-variant/15" aria-labelledby="section-runtime-title">
          <div class="flex items-center space-x-2">
            <span class="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center text-primary" aria-hidden="true">
              <span class="material-symbols-outlined text-[18px]">timer</span>
            </span>
            <div>
              <h2 id="section-runtime-title" class="font-title-md text-title-md text-on-surface">4. Runtime Controls</h2>
              <p class="font-body-sm text-body-sm text-on-surface-variant">Set wall-clock execution limits to prevent un-converging or hung agent runs.</p>
            </div>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-1">
            <div class="space-y-1">
              <label for="max_execution_time_seconds" class="font-label-sm text-label-sm text-on-surface-variant">Max Execution Time (Seconds)</label>
              <input type="number" min="1" id="max_execution_time_seconds" name="max_execution_time_seconds" class="w-full h-10 px-3 rounded-lg bg-surface-container-lowest text-on-surface font-code-sm text-code-sm border border-outline-variant/20 focus:outline-none focus:ring-1 focus:ring-primary" value="${runtime.max_execution_time_seconds ?? 1800}" />
            </div>
            <div class="space-y-1.5">
              <label for="runtime_action" class="font-label-sm text-label-sm text-on-surface-variant">Action when runtime expires</label>
              ${renderSelect("runtime_action", actions.runtime_action || GovernorAction.STOP)}
            </div>
          </div>
        </section>

        <!-- Section 5: Provider & Model Access -->
        <section class="rounded-xl bg-surface-container p-4 space-y-4 shadow-sm border border-outline-variant/15" aria-labelledby="section-providers-title">
          <div class="flex items-center space-x-2">
            <span class="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center text-primary" aria-hidden="true">
              <span class="material-symbols-outlined text-[18px]">cloud_sync</span>
            </span>
            <div>
              <h2 id="section-providers-title" class="font-title-md text-title-md text-on-surface">5. Provider &amp; Model Access</h2>
              <p class="font-body-sm text-body-sm text-on-surface-variant">Represent permitted provider and model execution allowlists.</p>
            </div>
          </div>

          <!-- Provider Family Allowlist Checkboxes -->
          <div class="space-y-1.5">
            <span class="font-label-sm text-label-sm text-on-surface-variant">Permitted Provider Families</span>
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-2">
              ${[
                { id: "anthropic", label: "Anthropic" },
                { id: "openai", label: "OpenAI" },
                { id: "gemini", label: "Google Gemini" },
                { id: "deepseek", label: "DeepSeek" }
              ].map(p => {
                const isAllowed = allowedProvidersList.includes(p.id) || allowedProvidersList.includes(p.label.toLowerCase()) || allowedProvidersList.includes("*");
                return `
                  <label class="flex items-center gap-2 p-2.5 bg-surface-container-low rounded-lg cursor-pointer hover:bg-surface-container-high transition-colors border border-outline-variant/10">
                    <input type="checkbox" name="provider_toggle_${p.id}" data-provider-id="${p.id}" ${isAllowed ? 'checked' : ''} class="provider-allow-checkbox w-4 h-4 rounded bg-surface-container-lowest text-primary border border-outline-variant/30 focus:ring-primary" />
                    <span class="font-body-md text-body-md text-on-surface">${p.label}</span>
                  </label>
                `;
              }).join("")}
            </div>
          </div>

          <!-- Explicit Allow/Block Inputs -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-1">
            <div class="space-y-1">
              <label for="allowed_models" class="font-label-sm text-label-sm text-on-surface-variant">Allowed Models (Comma-separated)</label>
              <input type="text" id="allowed_models" name="allowed_models" class="w-full h-10 px-3 rounded-lg bg-surface-container-lowest text-on-surface font-code-sm text-code-sm border border-outline-variant/20 focus:outline-none focus:ring-1 focus:ring-primary" value="${(providers.allowed_models || ['claude-3-5-sonnet', 'gpt-4o', 'gemini-1.5-pro', 'deepseek-chat']).join(', ')}" />
            </div>
            <div class="space-y-1">
              <label for="blocked_models" class="font-label-sm text-label-sm text-on-surface-variant">Blocked Models (Comma-separated)</label>
              <input type="text" id="blocked_models" name="blocked_models" class="w-full h-10 px-3 rounded-lg bg-surface-container-lowest text-on-surface font-code-sm text-code-sm border border-outline-variant/20 focus:outline-none focus:ring-1 focus:ring-primary" value="${(providers.blocked_models || []).join(', ')}" placeholder="e.g. gpt-3.5-turbo, text-davinci" />
            </div>
          </div>

          <div class="p-2.5 rounded-lg bg-surface-container-lowest/70 border border-outline-variant/15 text-on-surface-variant font-code-sm text-xs flex items-center gap-2">
            <span class="material-symbols-outlined text-[16px] text-primary" aria-hidden="true">info</span>
            <span>Policy representation only. INFUSE does not rank, recommend, or calculate provider preferences.</span>
          </div>
        </section>

        <!-- Section 6: Web Access Controls -->
        <section class="rounded-xl bg-surface-container p-4 space-y-3.5 shadow-sm border border-outline-variant/15" aria-labelledby="section-web-title">
          <div class="flex items-center justify-between">
            <div class="flex items-center space-x-2">
              <span class="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center text-primary" aria-hidden="true">
                <span class="material-symbols-outlined text-[18px]">public</span>
              </span>
              <div>
                <h2 id="section-web-title" class="font-title-md text-title-md text-on-surface">6. Web Access Controls</h2>
                <p class="font-body-sm text-body-sm text-on-surface-variant">Manage outbound network connections and domain browsing bounds.</p>
              </div>
            </div>
            <label class="flex items-center gap-2 cursor-pointer font-label-sm text-label-sm text-on-surface">
              <input type="checkbox" name="web_enabled" ${web.enabled !== false ? 'checked' : ''} class="w-4 h-4 rounded bg-surface-container-lowest text-primary border border-outline-variant/30 focus:ring-primary" />
              <span>Web Access Enabled</span>
            </label>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-2.5 pt-1">
            <div class="space-y-1">
              <label for="max_web_requests_per_task" class="font-label-sm text-label-sm text-on-surface-variant">Max Web Requests / Task</label>
              <input type="number" min="0" id="max_web_requests_per_task" name="max_web_requests_per_task" class="w-full h-10 px-3 rounded-lg bg-surface-container-lowest text-on-surface font-code-sm text-code-sm border border-outline-variant/20 focus:outline-none focus:ring-1 focus:ring-primary" value="${web.max_web_requests_per_task ?? 20}" />
            </div>
            <div class="space-y-1 sm:col-span-2">
              <label for="allowed_domains" class="font-label-sm text-label-sm text-on-surface-variant">Allowed Domains (Wildcard * allowed)</label>
              <input type="text" id="allowed_domains" name="allowed_domains" class="w-full h-10 px-3 rounded-lg bg-surface-container-lowest text-on-surface font-code-sm text-code-sm border border-outline-variant/20 focus:outline-none focus:ring-1 focus:ring-primary" value="${(web.allowed_domains || ['*']).join(', ')}" />
            </div>
          </div>
          <div class="space-y-1">
            <label for="blocked_domains" class="font-label-sm text-label-sm text-on-surface-variant">Blocked Domains (Comma-separated)</label>
            <input type="text" id="blocked_domains" name="blocked_domains" class="w-full h-10 px-3 rounded-lg bg-surface-container-lowest text-on-surface font-code-sm text-code-sm border border-outline-variant/20 focus:outline-none focus:ring-1 focus:ring-primary" value="${(web.blocked_domains || ['*.internal', '*.crypto-mining.pool']).join(', ')}" />
          </div>
        </section>

        <!-- Section 7: Tool Access -->
        <section class="rounded-xl bg-surface-container p-4 space-y-3.5 shadow-sm border border-outline-variant/15" aria-labelledby="section-tools-title">
          <div class="flex items-center justify-between">
            <div class="flex items-center space-x-2">
              <span class="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center text-primary" aria-hidden="true">
                <span class="material-symbols-outlined text-[18px]">build</span>
              </span>
              <div>
                <h2 id="section-tools-title" class="font-title-md text-title-md text-on-surface">7. Tool Access</h2>
                <p class="font-body-sm text-body-sm text-on-surface-variant">Control function calling permissions, failure ceilings, and loop bounds.</p>
              </div>
            </div>
            <label class="flex items-center gap-2 cursor-pointer font-label-sm text-label-sm text-on-surface">
              <input type="checkbox" name="tools_enabled" ${tools.enabled !== false ? 'checked' : ''} class="w-4 h-4 rounded bg-surface-container-lowest text-primary border border-outline-variant/30 focus:ring-primary" />
              <span>Tool Usage Enabled</span>
            </label>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-1">
            <div class="space-y-1">
              <label for="max_tool_calls_per_task" class="font-label-sm text-label-sm text-on-surface-variant">Max Tool Calls / Task</label>
              <input type="number" min="0" id="max_tool_calls_per_task" name="max_tool_calls_per_task" class="w-full h-10 px-3 rounded-lg bg-surface-container-lowest text-on-surface font-code-sm text-code-sm border border-outline-variant/20 focus:outline-none focus:ring-1 focus:ring-primary" value="${tools.max_tool_calls_per_task ?? 50}" />
            </div>
            <div class="space-y-1">
              <label for="max_consecutive_tool_failures" class="font-label-sm text-label-sm text-on-surface-variant">Max Consecutive Tool Failures</label>
              <input type="number" min="1" id="max_consecutive_tool_failures" name="max_consecutive_tool_failures" class="w-full h-10 px-3 rounded-lg bg-surface-container-lowest text-on-surface font-code-sm text-code-sm border border-outline-variant/20 focus:outline-none focus:ring-1 focus:ring-primary" value="${tools.max_consecutive_tool_failures ?? 3}" />
            </div>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            <div class="space-y-1">
              <label for="allowed_tools" class="font-label-sm text-label-sm text-on-surface-variant">Allowed Tools (Comma-separated, * wildcard)</label>
              <input type="text" id="allowed_tools" name="allowed_tools" class="w-full h-10 px-3 rounded-lg bg-surface-container-lowest text-on-surface font-code-sm text-code-sm border border-outline-variant/20 focus:outline-none focus:ring-1 focus:ring-primary" value="${(tools.allowed_tools || ['*']).join(', ')}" />
            </div>
            <div class="space-y-1">
              <label for="blocked_tools" class="font-label-sm text-label-sm text-on-surface-variant">Blocked Tools (Comma-separated)</label>
              <input type="text" id="blocked_tools" name="blocked_tools" class="w-full h-10 px-3 rounded-lg bg-surface-container-lowest text-on-surface font-code-sm text-code-sm border border-outline-variant/20 focus:outline-none focus:ring-1 focus:ring-primary" value="${(tools.blocked_tools || ['shell_root_exec', 'eval_raw_code']).join(', ')}" />
            </div>
          </div>
        </section>

        <!-- Section 8: Retry Policy -->
        <section class="rounded-xl bg-surface-container p-4 space-y-3.5 shadow-sm border border-outline-variant/15" aria-labelledby="section-retries-title">
          <div class="flex items-center space-x-2">
            <span class="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center text-primary" aria-hidden="true">
              <span class="material-symbols-outlined text-[18px]">replay</span>
            </span>
            <div>
              <h2 id="section-retries-title" class="font-title-md text-title-md text-on-surface">8. Retry Policy</h2>
              <p class="font-body-sm text-body-sm text-on-surface-variant">Configure automated retry backoffs and provider failover rules.</p>
            </div>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-2.5 pt-1">
            <div class="space-y-1">
              <label for="max_retries" class="font-label-sm text-label-sm text-on-surface-variant">Max Retries</label>
              <input type="number" min="0" id="max_retries" name="max_retries" class="w-full h-10 px-3 rounded-lg bg-surface-container-lowest text-on-surface font-code-sm text-code-sm border border-outline-variant/20 focus:outline-none focus:ring-1 focus:ring-primary" value="${retries.max_retries ?? 3}" />
            </div>
            <div class="space-y-1">
              <label for="backoff_factor" class="font-label-sm text-label-sm text-on-surface-variant">Backoff Multiplier</label>
              <input type="number" step="0.1" min="1.0" id="backoff_factor" name="backoff_factor" class="w-full h-10 px-3 rounded-lg bg-surface-container-lowest text-on-surface font-code-sm text-code-sm border border-outline-variant/20 focus:outline-none focus:ring-1 focus:ring-primary" value="${retries.backoff_factor ?? 1.5}" />
            </div>
            <div class="space-y-1.5">
              <label for="provider_failure_action" class="font-label-sm text-label-sm text-on-surface-variant">On Failure Action</label>
              ${renderSelect("provider_failure_action", actions.provider_failure_action || GovernorAction.SWITCH)}
            </div>
          </div>
          <div class="space-y-1">
            <label for="retry_on_errors" class="font-label-sm text-label-sm text-on-surface-variant">Retry On Error Types (Comma-separated)</label>
            <input type="text" id="retry_on_errors" name="retry_on_errors" class="w-full h-10 px-3 rounded-lg bg-surface-container-lowest text-on-surface font-code-sm text-code-sm border border-outline-variant/20 focus:outline-none focus:ring-1 focus:ring-primary" value="${(retries.retry_on_errors || ['rate_limit', 'timeout', '503_service_unavailable']).join(', ')}" />
          </div>
          <div class="pt-0.5">
            <label class="flex items-center gap-2 cursor-pointer font-label-sm text-label-sm text-on-surface">
              <input type="checkbox" name="fallback_provider_on_failure" ${retries.fallback_provider_on_failure !== false ? 'checked' : ''} class="w-4 h-4 rounded bg-surface-container-lowest text-primary border border-outline-variant/30 focus:ring-primary" />
              <span>Automatically switch to fallback provider on unrecoverable failure</span>
            </label>
          </div>
        </section>

        <!-- Section 9: Anomaly & Runaway Protection -->
        <section class="rounded-xl bg-surface-container p-4 space-y-3.5 shadow-sm border border-outline-variant/15" aria-labelledby="section-anomaly-title">
          <div class="flex items-center justify-between">
            <div class="flex items-center space-x-2">
              <span class="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center text-primary" aria-hidden="true">
                <span class="material-symbols-outlined text-[18px]">warning</span>
              </span>
              <div>
                <h2 id="section-anomaly-title" class="font-title-md text-title-md text-on-surface">9. Anomaly &amp; Runaway Protection</h2>
                <p class="font-body-sm text-body-sm text-on-surface-variant">Represent runaway prevention thresholds for infinite loops and token velocity surges.</p>
              </div>
            </div>
            <label class="flex items-center gap-2 cursor-pointer font-label-sm text-label-sm text-on-surface">
              <input type="checkbox" name="circuit_breaker_enabled" ${anomaly.circuit_breaker_enabled !== false ? 'checked' : ''} class="w-4 h-4 rounded bg-surface-container-lowest text-primary border border-outline-variant/30 focus:ring-primary" />
              <span>Circuit Breaker Active</span>
            </label>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-2.5 pt-1">
            <div class="space-y-1">
              <label for="token_velocity_surge_threshold" class="font-label-sm text-label-sm text-on-surface-variant">Token Surge Velocity (tokens/s)</label>
              <input type="number" min="0" id="token_velocity_surge_threshold" name="token_velocity_surge_threshold" class="w-full h-10 px-3 rounded-lg bg-surface-container-lowest text-on-surface font-code-sm text-code-sm border border-outline-variant/20 focus:outline-none focus:ring-1 focus:ring-primary" value="${anomaly.token_velocity_surge_threshold ?? 500}" />
            </div>
            <div class="space-y-1">
              <label for="repetitive_loop_threshold" class="font-label-sm text-label-sm text-on-surface-variant">Repetitive Tool Loop Threshold</label>
              <input type="number" min="1" id="repetitive_loop_threshold" name="repetitive_loop_threshold" class="w-full h-10 px-3 rounded-lg bg-surface-container-lowest text-on-surface font-code-sm text-code-sm border border-outline-variant/20 focus:outline-none focus:ring-1 focus:ring-primary" value="${anomaly.repetitive_loop_threshold ?? 4}" />
            </div>
            <div class="space-y-1.5">
              <label for="anomaly_action" class="font-label-sm text-label-sm text-on-surface-variant">Action on Runaway / Anomaly</label>
              ${renderSelect("anomaly_action", actions.anomaly_action || GovernorAction.STOP)}
            </div>
          </div>
        </section>

        <!-- Section 10: Policy Action Matrix -->
        <section class="rounded-xl bg-surface-container p-4 space-y-3.5 shadow-sm border border-outline-variant/15" aria-labelledby="section-matrix-title">
          <div class="flex items-center space-x-2">
            <span class="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center text-primary" aria-hidden="true">
              <span class="material-symbols-outlined text-[18px]">rule</span>
            </span>
            <div>
              <h2 id="section-matrix-title" class="font-title-md text-title-md text-on-surface">10. Policy Action Matrix Summary</h2>
              <p class="font-body-sm text-body-sm text-on-surface-variant">Deterministic Governor action bindings per trigger condition.</p>
            </div>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full text-left text-body-sm border-collapse" aria-label="Policy Action Matrix">
              <thead>
                <tr class="border-b border-outline-variant/20 text-on-surface-variant font-label-sm text-label-sm uppercase">
                  <th scope="col" class="py-2.5 px-3">Trigger Condition</th>
                  <th scope="col" class="py-2.5 px-3">Configured Ceiling</th>
                  <th scope="col" class="py-2.5 px-3">Bound Governor Action</th>
                  <th scope="col" class="py-2.5 px-3">Behavioral Regulation</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-outline-variant/10 font-code-sm text-code-sm">
                <tr>
                  <td class="py-2.5 px-3 text-on-surface font-medium">Budget Overrun</td>
                  <td class="py-2.5 px-3 text-tertiary font-bold">$${budget.max_cost_per_task ?? 10.00} USD</td>
                  <td class="py-2.5 px-3">${renderGovernorActionBadge(actions.budget_action || GovernorAction.OPTIMIZE)}</td>
                  <td class="py-2.5 px-3 text-on-surface-variant text-xs">Prompt compression &amp; context pruning to prevent financial breach.</td>
                </tr>
                <tr>
                  <td class="py-2.5 px-3 text-on-surface font-medium">Token Ceiling</td>
                  <td class="py-2.5 px-3 text-on-surface font-bold">${Number(tokens.max_total_tokens ?? 136192).toLocaleString()} tokens</td>
                  <td class="py-2.5 px-3">${renderGovernorActionBadge(actions.token_action || GovernorAction.OPTIMIZE)}</td>
                  <td class="py-2.5 px-3 text-on-surface-variant text-xs">Context window compaction &amp; semantic message pruning.</td>
                </tr>
                <tr>
                  <td class="py-2.5 px-3 text-on-surface font-medium">Rate Ceiling</td>
                  <td class="py-2.5 px-3 text-on-surface font-bold">${requests.max_rpm ?? 60} RPM</td>
                  <td class="py-2.5 px-3">${renderGovernorActionBadge(actions.request_action || GovernorAction.THROTTLE)}</td>
                  <td class="py-2.5 px-3 text-on-surface-variant text-xs">Rate pacing queue inserted prior to provider dispatch.</td>
                </tr>
                <tr>
                  <td class="py-2.5 px-3 text-on-surface font-medium">Runtime Expiry</td>
                  <td class="py-2.5 px-3 text-on-surface font-bold">${runtime.max_execution_time_seconds ?? 1800}s</td>
                  <td class="py-2.5 px-3">${renderGovernorActionBadge(actions.runtime_action || GovernorAction.STOP)}</td>
                  <td class="py-2.5 px-3 text-on-surface-variant text-xs">Immediate run halt to prevent hung worker processes.</td>
                </tr>
                <tr>
                  <td class="py-2.5 px-3 text-on-surface font-medium">Provider Failure</td>
                  <td class="py-2.5 px-3 text-on-surface font-bold">5xx / 429 Unrecoverable</td>
                  <td class="py-2.5 px-3">${renderGovernorActionBadge(actions.provider_failure_action || GovernorAction.SWITCH)}</td>
                  <td class="py-2.5 px-3 text-on-surface-variant text-xs">Dynamic failover to configured alternate provider model.</td>
                </tr>
                <tr>
                  <td class="py-2.5 px-3 text-on-surface font-medium">Runaway Loop</td>
                  <td class="py-2.5 px-3 text-error font-bold">&gt;${anomaly.repetitive_loop_threshold ?? 4} Repetitions</td>
                  <td class="py-2.5 px-3">${renderGovernorActionBadge(actions.anomaly_action || GovernorAction.STOP)}</td>
                  <td class="py-2.5 px-3 text-on-surface-variant text-xs">Circuit-breaker trip on un-converging repetitive iterations.</td>
                </tr>
                <tr>
                  <td class="py-2.5 px-3 text-on-surface font-medium">Nominal Flow</td>
                  <td class="py-2.5 px-3 text-on-surface-variant">Within all thresholds</td>
                  <td class="py-2.5 px-3">${renderGovernorActionBadge(GovernorAction.CONTINUE)}</td>
                  <td class="py-2.5 px-3 text-on-surface-variant text-xs">Standard unthrottled execution with observability telemetry.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

      </form>
    </div>
  `;
}
