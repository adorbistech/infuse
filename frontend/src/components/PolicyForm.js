/**
 * Governance Policy Configuration Form Component (10 Sections).
 */

export function renderPolicyForm(policyViewModel) {
  const policy = policyViewModel.policy;
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

  const actionOptions = [
    { value: "OPTIMIZE", label: "Optimize (Compress prompts, reduce context window)" },
    { value: "SWITCH", label: "Switch (Route to cheaper tier model)" },
    { value: "THROTTLE", label: "Throttle (Rate-limit request rate)" },
    { value: "STOP", label: "Stop (Hard circuit-breaker halt)" },
    { value: "CONTINUE", label: "Continue (Alert & Log only)" }
  ];

  const renderSelect = (name, currentValue) => `
    <div class="relative">
      <select name="${name}" class="w-full h-10 px-3 pr-9 rounded-lg bg-surface-container-lowest text-on-surface font-label-md text-label-md appearance-none focus:outline-none focus:ring-1 focus:ring-primary border border-outline-variant/20">
        ${actionOptions.map(opt => `
          <option value="${opt.value}" ${opt.value === currentValue ? 'selected' : ''}>${opt.label}</option>
        `).join("")}
      </select>
      <span class="material-symbols-outlined absolute right-3 top-2.5 text-on-surface-variant pointer-events-none text-[18px]">expand_more</span>
    </div>
  `;

  return `
    <div class="space-y-4">
      <!-- Page Header -->
      <div class="flex flex-col space-y-1 bg-surface-container-low p-4 rounded-xl border border-outline-variant/20">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-2">
            <span class="material-symbols-outlined text-primary text-[22px]">shield</span>
            <h1 class="font-headline-lg-mobile text-headline-lg-mobile text-on-surface tracking-tight">Governance</h1>
          </div>
          <span class="px-2.5 py-1 rounded-full bg-surface-container-high text-primary font-code-sm text-code-sm uppercase tracking-wider flex items-center gap-1.5 shadow-sm">
            <span class="w-1.5 h-1.5 rounded-full bg-primary animate-pulse"></span>
            Runtime Guard
          </span>
        </div>
        <p class="font-body-md text-body-md text-on-surface-variant">
          Define the execution boundaries that INFUSE must enforce across autonomous agents.
        </p>
      </div>

      <!-- Active Policy Overview Card -->
      <div class="w-full rounded-xl bg-surface-container p-4 space-y-3.5 shadow-md border border-outline-variant/15">
        <div class="flex items-start justify-between">
          <div class="space-y-1">
            <div class="flex items-center gap-2">
              <span class="font-title-md text-title-md text-on-surface">${policy.name || 'Default Execution Policy'}</span>
              <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-primary/15 text-primary font-label-sm text-label-sm">
                <span class="w-1.5 h-1.5 rounded-full bg-primary"></span>
                Active
              </span>
            </div>
            <div class="flex items-center gap-3 text-on-surface-variant font-code-sm text-code-sm">
              <span>Ver: <strong class="text-on-surface">${policy.version || 'v1.0.4'}</strong></span>
              <span>•</span>
              <span>Policy ID: <strong class="text-primary">${policy.policy_id}</strong></span>
            </div>
          </div>
          <div class="w-9 h-9 rounded-lg bg-surface-container-high flex items-center justify-center text-primary">
            <span class="material-symbols-outlined text-[20px]">verified_user</span>
          </div>
        </div>

        <!-- Strictness Indicator -->
        <div class="space-y-1 pt-1">
          <div class="flex justify-between font-label-sm text-label-sm text-on-surface-variant">
            <span>Guardrail Enforcement Index</span>
            <span class="font-code-sm text-code-sm text-primary">${policyViewModel.guardrail_strictness_index}</span>
          </div>
          <div class="w-full h-1.5 rounded-full bg-surface-container-lowest overflow-hidden">
            <div class="h-full rounded-full bg-primary w-[98%] transition-all duration-500"></div>
          </div>
        </div>

        <div class="flex items-center gap-2 pt-1">
          <button class="flex-1 h-9 rounded-lg bg-primary text-on-primary font-label-md text-label-md font-semibold flex items-center justify-center gap-1.5 shadow-sm active:opacity-90 transition-opacity" id="save-policy-btn" type="button">
            <span class="material-symbols-outlined text-[18px]">save</span>
            Save Active Policy
          </button>
          <button class="flex-1 h-9 rounded-lg bg-surface-container-high text-on-surface font-label-md text-label-md flex items-center justify-center gap-1.5 active:bg-surface-container-highest transition-colors" id="duplicate-policy-btn" type="button">
            <span class="material-symbols-outlined text-[18px]">content_copy</span>
            Duplicate Policy
          </button>
        </div>
      </div>

      <!-- Policy Formulation Form -->
      <form class="space-y-4" id="governance-form" onsubmit="event.preventDefault();">
        <!-- Section 1: Budget Controls -->
        <section class="rounded-xl bg-surface-container p-4 space-y-3.5 shadow-sm border border-outline-variant/15">
          <div class="flex items-center justify-between">
            <div class="flex items-center space-x-2">
              <span class="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
                <span class="material-symbols-outlined text-[18px]">attach_money</span>
              </span>
              <div>
                <h2 class="font-title-md text-title-md text-on-surface">Budget Controls</h2>
                <p class="font-body-sm text-body-sm text-on-surface-variant">Define financial boundaries for execution.</p>
              </div>
            </div>
            <span class="font-code-sm text-code-sm px-2 py-0.5 rounded bg-surface-container-high text-on-surface-variant">USD ($)</span>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-2.5 pt-1">
            <div class="space-y-1">
              <label class="font-label-sm text-label-sm text-on-surface-variant">Max Cost / Task</label>
              <input type="number" step="0.5" name="max_cost_per_task" class="w-full h-10 px-3 rounded-lg bg-surface-container-lowest text-on-surface font-code-sm text-code-sm border border-outline-variant/20 focus:outline-none focus:ring-1 focus:ring-primary" value="${budget.max_cost_per_task ?? 10.00}" />
            </div>
            <div class="space-y-1">
              <label class="font-label-sm text-label-sm text-on-surface-variant">Max Cost / Day</label>
              <input type="number" step="10" name="max_cost_per_day" class="w-full h-10 px-3 rounded-lg bg-surface-container-lowest text-on-surface font-code-sm text-code-sm border border-outline-variant/20 focus:outline-none focus:ring-1 focus:ring-primary" value="${budget.max_cost_per_day ?? 150.00}" />
            </div>
            <div class="space-y-1">
              <label class="font-label-sm text-label-sm text-on-surface-variant">Max Cost / Month</label>
              <input type="number" step="100" name="max_cost_per_month" class="w-full h-10 px-3 rounded-lg bg-surface-container-lowest text-on-surface font-code-sm text-code-sm border border-outline-variant/20 focus:outline-none focus:ring-1 focus:ring-primary" value="${budget.max_cost_per_month ?? 2500.00}" />
            </div>
          </div>
          <div class="space-y-1.5 pt-1">
            <label class="font-label-sm text-label-sm text-on-surface-variant">Action when budget limit reached</label>
            ${renderSelect("budget_action", actions.budget_action || "OPTIMIZE")}
          </div>
        </section>

        <!-- Section 2: Token Controls -->
        <section class="rounded-xl bg-surface-container p-4 space-y-3.5 shadow-sm border border-outline-variant/15">
          <div class="flex items-center justify-between">
            <div class="flex items-center space-x-2">
              <span class="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
                <span class="material-symbols-outlined text-[18px]">toll</span>
              </span>
              <div>
                <h2 class="font-title-md text-title-md text-on-surface">Token Controls</h2>
                <p class="font-body-sm text-body-sm text-on-surface-variant">Set context window ceilings and output constraints.</p>
              </div>
            </div>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-2.5 pt-1">
            <div class="space-y-1">
              <label class="font-label-sm text-label-sm text-on-surface-variant">Max Input Tokens</label>
              <input type="number" step="1000" name="max_input_tokens" class="w-full h-10 px-3 rounded-lg bg-surface-container-lowest text-on-surface font-code-sm text-code-sm border border-outline-variant/20 focus:outline-none focus:ring-1 focus:ring-primary" value="${tokens.max_input_tokens ?? 128000}" />
            </div>
            <div class="space-y-1">
              <label class="font-label-sm text-label-sm text-on-surface-variant">Max Output Tokens</label>
              <input type="number" step="512" name="max_output_tokens" class="w-full h-10 px-3 rounded-lg bg-surface-container-lowest text-on-surface font-code-sm text-code-sm border border-outline-variant/20 focus:outline-none focus:ring-1 focus:ring-primary" value="${tokens.max_output_tokens ?? 8192}" />
            </div>
            <div class="space-y-1">
              <label class="font-label-sm text-label-sm text-on-surface-variant">Max Total Tokens</label>
              <input type="number" step="1000" name="max_total_tokens" class="w-full h-10 px-3 rounded-lg bg-surface-container-lowest text-on-surface font-code-sm text-code-sm border border-outline-variant/20 focus:outline-none focus:ring-1 focus:ring-primary" value="${tokens.max_total_tokens ?? 136192}" />
            </div>
          </div>
          <div class="space-y-1.5 pt-1">
            <label class="font-label-sm text-label-sm text-on-surface-variant">Action when token limit reached</label>
            ${renderSelect("token_action", actions.token_action || "OPTIMIZE")}
          </div>
        </section>

        <!-- Section 3: Request Controls -->
        <section class="rounded-xl bg-surface-container p-4 space-y-3.5 shadow-sm border border-outline-variant/15">
          <div class="flex items-center space-x-2">
            <span class="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
              <span class="material-symbols-outlined text-[18px]">speed</span>
            </span>
            <div>
              <h2 class="font-title-md text-title-md text-on-surface">Request Controls</h2>
              <p class="font-body-sm text-body-sm text-on-surface-variant">Govern API request rates and concurrency.</p>
            </div>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-1">
            <div class="space-y-1">
              <label class="font-label-sm text-label-sm text-on-surface-variant">Max Requests / Minute (RPM)</label>
              <input type="number" name="max_rpm" class="w-full h-10 px-3 rounded-lg bg-surface-container-lowest text-on-surface font-code-sm text-code-sm border border-outline-variant/20 focus:outline-none focus:ring-1 focus:ring-primary" value="${requests.max_rpm ?? 60}" />
            </div>
            <div class="space-y-1">
              <label class="font-label-sm text-label-sm text-on-surface-variant">Max Requests / Task</label>
              <input type="number" name="max_requests_per_task" class="w-full h-10 px-3 rounded-lg bg-surface-container-lowest text-on-surface font-code-sm text-code-sm border border-outline-variant/20 focus:outline-none focus:ring-1 focus:ring-primary" value="${requests.max_requests_per_task ?? 25}" />
            </div>
          </div>
          <div class="space-y-1.5 pt-1">
            <label class="font-label-sm text-label-sm text-on-surface-variant">Action when request ceiling reached</label>
            ${renderSelect("request_action", actions.request_action || "THROTTLE")}
          </div>
        </section>

        <!-- Section 4: Runtime Controls -->
        <section class="rounded-xl bg-surface-container p-4 space-y-3.5 shadow-sm border border-outline-variant/15">
          <div class="flex items-center space-x-2">
            <span class="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
              <span class="material-symbols-outlined text-[18px]">timer</span>
            </span>
            <div>
              <h2 class="font-title-md text-title-md text-on-surface">Runtime Controls</h2>
              <p class="font-body-sm text-body-sm text-on-surface-variant">Set wall-clock execution limits to prevent hung runs.</p>
            </div>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-1">
            <div class="space-y-1">
              <label class="font-label-sm text-label-sm text-on-surface-variant">Max Execution Time (Seconds)</label>
              <input type="number" name="max_execution_time_seconds" class="w-full h-10 px-3 rounded-lg bg-surface-container-lowest text-on-surface font-code-sm text-code-sm border border-outline-variant/20 focus:outline-none focus:ring-1 focus:ring-primary" value="${runtime.max_execution_time_seconds ?? 1800}" />
            </div>
            <div class="space-y-1.5">
              <label class="font-label-sm text-label-sm text-on-surface-variant">Action when runtime expires</label>
              ${renderSelect("runtime_action", actions.runtime_action || "STOP")}
            </div>
          </div>
        </section>

        <!-- Section 5: Provider & Model Access -->
        <section class="rounded-xl bg-surface-container p-4 space-y-4 shadow-sm border border-outline-variant/15">
          <div class="flex items-center space-x-2">
            <span class="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
              <span class="material-symbols-outlined text-[18px]">cloud_sync</span>
            </span>
            <div>
              <h2 class="font-title-md text-title-md text-on-surface">Provider &amp; Model Access</h2>
              <p class="font-body-sm text-body-sm text-on-surface-variant">Control which external AI providers are permitted.</p>
            </div>
          </div>
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1">
            ${['Anthropic', 'OpenAI', 'Google Gemini', 'DeepSeek'].map(p => `
              <label class="flex items-center gap-2 p-2.5 bg-surface-container-low rounded-lg cursor-pointer hover:bg-surface-container-high transition-colors">
                <input type="checkbox" checked class="w-4 h-4 rounded bg-surface-container-lowest text-primary border border-outline-variant/30 focus:ring-primary" />
                <span class="font-body-md text-body-md text-on-surface">${p}</span>
              </label>
            `).join("")}
          </div>
        </section>

        <!-- Section 6: Web Access Controls -->
        <section class="rounded-xl bg-surface-container p-4 space-y-3.5 shadow-sm border border-outline-variant/15">
          <div class="flex items-center space-x-2">
            <span class="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
              <span class="material-symbols-outlined text-[18px]">public</span>
            </span>
            <div>
              <h2 class="font-title-md text-title-md text-on-surface">Web Access Controls</h2>
              <p class="font-body-sm text-body-sm text-on-surface-variant">Manage outbound network connections for autonomous agents.</p>
            </div>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-1">
            <div class="space-y-1">
              <label class="font-label-sm text-label-sm text-on-surface-variant">Max Web Requests / Task</label>
              <input type="number" name="max_web_requests_per_task" class="w-full h-10 px-3 rounded-lg bg-surface-container-lowest text-on-surface font-code-sm text-code-sm border border-outline-variant/20" value="${web.max_web_requests_per_task ?? 20}" />
            </div>
            <div class="space-y-1">
              <label class="font-label-sm text-label-sm text-on-surface-variant">Allowed Domains (Wildcard * allowed)</label>
              <input type="text" name="allowed_domains" class="w-full h-10 px-3 rounded-lg bg-surface-container-lowest text-on-surface font-code-sm text-code-sm border border-outline-variant/20" value="${(web.allowed_domains || ['*']).join(', ')}" />
            </div>
          </div>
        </section>

        <!-- Section 7: Tool Access -->
        <section class="rounded-xl bg-surface-container p-4 space-y-3.5 shadow-sm border border-outline-variant/15">
          <div class="flex items-center space-x-2">
            <span class="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
              <span class="material-symbols-outlined text-[18px]">build</span>
            </span>
            <div>
              <h2 class="font-title-md text-title-md text-on-surface">Tool Access</h2>
              <p class="font-body-sm text-body-sm text-on-surface-variant">Control function calling and tool execution bounds.</p>
            </div>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-1">
            <div class="space-y-1">
              <label class="font-label-sm text-label-sm text-on-surface-variant">Max Tool Calls / Task</label>
              <input type="number" name="max_tool_calls_per_task" class="w-full h-10 px-3 rounded-lg bg-surface-container-lowest text-on-surface font-code-sm text-code-sm border border-outline-variant/20" value="${tools.max_tool_calls_per_task ?? 50}" />
            </div>
            <div class="space-y-1">
              <label class="font-label-sm text-label-sm text-on-surface-variant">Max Consecutive Tool Failures</label>
              <input type="number" name="max_consecutive_tool_failures" class="w-full h-10 px-3 rounded-lg bg-surface-container-lowest text-on-surface font-code-sm text-code-sm border border-outline-variant/20" value="${tools.max_consecutive_tool_failures ?? 3}" />
            </div>
          </div>
        </section>

        <!-- Section 8: Retry Policy -->
        <section class="rounded-xl bg-surface-container p-4 space-y-3.5 shadow-sm border border-outline-variant/15">
          <div class="flex items-center space-x-2">
            <span class="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
              <span class="material-symbols-outlined text-[18px]">replay</span>
            </span>
            <div>
              <h2 class="font-title-md text-title-md text-on-surface">Retry Policy</h2>
              <p class="font-body-sm text-body-sm text-on-surface-variant">Configure automated retry backoffs and provider failover.</p>
            </div>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-2.5 pt-1">
            <div class="space-y-1">
              <label class="font-label-sm text-label-sm text-on-surface-variant">Max Retries</label>
              <input type="number" name="max_retries" class="w-full h-10 px-3 rounded-lg bg-surface-container-lowest text-on-surface font-code-sm text-code-sm border border-outline-variant/20" value="${retries.max_retries ?? 3}" />
            </div>
            <div class="space-y-1">
              <label class="font-label-sm text-label-sm text-on-surface-variant">Backoff Multiplier</label>
              <input type="number" step="0.1" name="backoff_factor" class="w-full h-10 px-3 rounded-lg bg-surface-container-lowest text-on-surface font-code-sm text-code-sm border border-outline-variant/20" value="${retries.backoff_factor ?? 1.5}" />
            </div>
            <div class="space-y-1.5">
              <label class="font-label-sm text-label-sm text-on-surface-variant">On Failure Action</label>
              ${renderSelect("provider_failure_action", actions.provider_failure_action || "SWITCH")}
            </div>
          </div>
        </section>

        <!-- Section 9: Anomaly & Runaway Protection -->
        <section class="rounded-xl bg-surface-container p-4 space-y-3.5 shadow-sm border border-outline-variant/15">
          <div class="flex items-center space-x-2">
            <span class="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
              <span class="material-symbols-outlined text-[18px]">warning</span>
            </span>
            <div>
              <h2 class="font-title-md text-title-md text-on-surface">Anomaly &amp; Runaway Protection</h2>
              <p class="font-body-sm text-body-sm text-on-surface-variant">Automated circuit-breakers for infinite agent loops.</p>
            </div>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-1">
            <div class="space-y-1">
              <label class="font-label-sm text-label-sm text-on-surface-variant">Token Surge Velocity (tokens/sec)</label>
              <input type="number" name="token_velocity_surge_threshold" class="w-full h-10 px-3 rounded-lg bg-surface-container-lowest text-on-surface font-code-sm text-code-sm border border-outline-variant/20" value="${anomaly.token_velocity_surge_threshold ?? 500}" />
            </div>
            <div class="space-y-1">
              <label class="font-label-sm text-label-sm text-on-surface-variant">Repetitive Tool Loop Threshold</label>
              <input type="number" name="repetitive_loop_threshold" class="w-full h-10 px-3 rounded-lg bg-surface-container-lowest text-on-surface font-code-sm text-code-sm border border-outline-variant/20" value="${anomaly.repetitive_loop_threshold ?? 4}" />
            </div>
          </div>
        </section>

        <!-- Section 10: Policy Action Matrix -->
        <section class="rounded-xl bg-surface-container p-4 space-y-3.5 shadow-sm border border-outline-variant/15">
          <div class="flex items-center space-x-2">
            <span class="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
              <span class="material-symbols-outlined text-[18px]">rule</span>
            </span>
            <div>
              <h2 class="font-title-md text-title-md text-on-surface">Policy Action Matrix Summary</h2>
              <p class="font-body-sm text-body-sm text-on-surface-variant">Deterministic Governor action bindings per trigger condition.</p>
            </div>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full text-left text-body-sm border-collapse">
              <thead>
                <tr class="border-b border-outline-variant/20 text-on-surface-variant font-label-sm text-label-sm uppercase">
                  <th class="py-2 px-3">Trigger Condition</th>
                  <th class="py-2 px-3">Configured Ceiling</th>
                  <th class="py-2 px-3">Bound Governor Action</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-outline-variant/10 font-code-sm text-code-sm">
                <tr>
                  <td class="py-2 px-3 text-on-surface font-medium">Budget Overrun</td>
                  <td class="py-2 px-3 text-tertiary">$${budget.max_cost_per_task ?? 10.00} USD</td>
                  <td class="py-2 px-3"><span class="px-2 py-0.5 rounded bg-primary/15 text-primary">${actions.budget_action || 'OPTIMIZE'}</span></td>
                </tr>
                <tr>
                  <td class="py-2 px-3 text-on-surface font-medium">Token Ceiling</td>
                  <td class="py-2 px-3 text-on-surface">${(tokens.max_total_tokens ?? 136192).toLocaleString()} tokens</td>
                  <td class="py-2 px-3"><span class="px-2 py-0.5 rounded bg-primary/15 text-primary">${actions.token_action || 'OPTIMIZE'}</span></td>
                </tr>
                <tr>
                  <td class="py-2 px-3 text-on-surface font-medium">Rate Ceiling</td>
                  <td class="py-2 px-3 text-on-surface">${requests.max_rpm ?? 60} RPM</td>
                  <td class="py-2 px-3"><span class="px-2 py-0.5 rounded bg-surface-container-highest text-primary">${actions.request_action || 'THROTTLE'}</span></td>
                </tr>
                <tr>
                  <td class="py-2 px-3 text-on-surface font-medium">Runtime Expiry</td>
                  <td class="py-2 px-3 text-on-surface">${runtime.max_execution_time_seconds ?? 1800}s</td>
                  <td class="py-2 px-3"><span class="px-2 py-0.5 rounded bg-error-container text-error">${actions.runtime_action || 'STOP'}</span></td>
                </tr>
                <tr>
                  <td class="py-2 px-3 text-on-surface font-medium">Provider Failure</td>
                  <td class="py-2 px-3 text-on-surface">5xx / 429 Unrecoverable</td>
                  <td class="py-2 px-3"><span class="px-2 py-0.5 rounded bg-primary-container text-on-primary-container">${actions.provider_failure_action || 'SWITCH'}</span></td>
                </tr>
                <tr>
                  <td class="py-2 px-3 text-on-surface font-medium">Runaway Loop</td>
                  <td class="py-2 px-3 text-error">&gt;4 Identical Loops</td>
                  <td class="py-2 px-3"><span class="px-2 py-0.5 rounded bg-error-container text-error">${actions.anomaly_action || 'STOP'}</span></td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </form>
    </div>
  `;
}
