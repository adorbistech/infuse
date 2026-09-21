/**
 * 8-Card Metrics Grid Component.
 */

export function renderMetricsGrid(metrics) {
  const formatNum = (num) => new Intl.NumberFormat().format(num);

  return `
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
      <!-- Card 1: Input Tokens -->
      <div class="bg-surface-container rounded-xl p-3 shadow-sm flex flex-col justify-between border border-outline-variant/15">
        <span class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">Input Tokens</span>
        <div class="my-1">
          <div class="font-headline-sm text-headline-sm text-on-surface font-semibold" id="m-inTokens">${formatNum(metrics.input_tokens)}</div>
          <div class="font-code-sm text-code-sm text-tertiary flex items-center gap-0.5 mt-0.5">
            <span class="material-symbols-outlined text-[14px]">trending_up</span>
            +8.2% this exec
          </div>
        </div>
        <div class="w-full bg-surface-container-highest h-1 rounded-full overflow-hidden">
          <div class="bg-primary h-full w-[62%]"></div>
        </div>
      </div>

      <!-- Card 2: Cached Tokens -->
      <div class="bg-surface-container rounded-xl p-3 shadow-sm flex flex-col justify-between border border-outline-variant/15">
        <span class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">Cached Tokens</span>
        <div class="my-1">
          <div class="font-headline-sm text-headline-sm text-on-surface font-semibold" id="m-cachedTokens">${formatNum(metrics.cached_tokens)}</div>
          <div class="font-code-sm text-code-sm text-primary flex items-center gap-0.5 mt-0.5">
            <span class="material-symbols-outlined text-[14px]">bolt</span>
            30.1% hit rate
          </div>
        </div>
        <div class="w-full bg-surface-container-highest h-1 rounded-full overflow-hidden">
          <div class="bg-primary-container h-full w-[30%]"></div>
        </div>
      </div>

      <!-- Card 3: Output Tokens -->
      <div class="bg-surface-container rounded-xl p-3 shadow-sm flex flex-col justify-between border border-outline-variant/15">
        <span class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">Output Tokens</span>
        <div class="my-1">
          <div class="font-headline-sm text-headline-sm text-on-surface font-semibold" id="m-outTokens">${formatNum(metrics.output_tokens)}</div>
          <div class="font-code-sm text-code-sm text-on-surface-variant mt-0.5">Tokens generated</div>
        </div>
        <div class="w-full bg-surface-container-highest h-1 rounded-full overflow-hidden">
          <div class="bg-secondary h-full w-[22%]"></div>
        </div>
      </div>

      <!-- Card 4: Total Tokens -->
      <div class="bg-surface-container rounded-xl p-3 shadow-sm flex flex-col justify-between border border-outline-variant/15">
        <span class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">Total Tokens</span>
        <div class="my-1">
          <div class="font-headline-sm text-headline-sm text-primary font-semibold" id="m-totTokens">${formatNum(metrics.total_tokens)}</div>
          <div class="font-code-sm text-code-sm text-on-surface-variant mt-0.5">Total session context</div>
        </div>
        <div class="w-full bg-surface-container-highest h-1 rounded-full overflow-hidden">
          <div class="bg-primary h-full w-[78%]"></div>
        </div>
      </div>

      <!-- Card 5: Current Cost -->
      <div class="bg-surface-container rounded-xl p-3 shadow-sm flex flex-col justify-between border border-outline-variant/15">
        <span class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">Current Cost</span>
        <div class="my-1">
          <div class="font-headline-sm text-headline-sm text-tertiary font-semibold" id="m-cost">$${metrics.current_cost_usd.toFixed(3)}</div>
          <div class="font-code-sm text-code-sm text-on-surface-variant mt-0.5">${metrics.budget_consumed_percent.toFixed(1)}% of task budget</div>
        </div>
        <div class="w-full bg-surface-container-highest h-1 rounded-full overflow-hidden">
          <div class="bg-tertiary-container h-full" style="width: ${Math.min(100, metrics.budget_consumed_percent)}%"></div>
        </div>
      </div>

      <!-- Card 6: Budget Consumed -->
      <div class="bg-surface-container rounded-xl p-3 shadow-sm flex flex-col justify-between border border-outline-variant/15">
        <span class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">Budget Used</span>
        <div class="my-1">
          <div class="font-headline-sm text-headline-sm text-on-surface font-semibold">${metrics.budget_consumed_percent.toFixed(1)}%</div>
          <div class="font-code-sm text-code-sm text-on-surface-variant mt-0.5">Threshold: $${metrics.budget_limit_usd.toFixed(2)} hard cap</div>
        </div>
        <div class="w-full bg-surface-container-highest h-1 rounded-full overflow-hidden">
          <div class="bg-tertiary h-full" style="width: ${Math.min(100, metrics.budget_consumed_percent)}%"></div>
        </div>
      </div>

      <!-- Card 7: Requests / RPM -->
      <div class="bg-surface-container rounded-xl p-3 shadow-sm flex flex-col justify-between border border-outline-variant/15">
        <span class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">Requests</span>
        <div class="my-1">
          <div class="font-headline-sm text-headline-sm text-on-surface font-semibold">${metrics.requests_count} <span class="text-body-md font-normal text-on-surface-variant">reqs</span></div>
          <div class="font-code-sm text-code-sm text-on-surface-variant mt-0.5">${metrics.requests_per_minute.toFixed(1)} RPM avg</div>
        </div>
        <div class="w-full bg-surface-container-highest h-1 rounded-full overflow-hidden">
          <div class="bg-primary h-full w-[45%]"></div>
        </div>
      </div>

      <!-- Card 8: Errors / Retries -->
      <div class="bg-surface-container rounded-xl p-3 shadow-sm flex flex-col justify-between border border-outline-variant/15">
        <span class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">Errors &amp; Retries</span>
        <div class="my-1">
          <div class="font-headline-sm text-headline-sm ${metrics.errors_count > 0 ? 'text-error' : 'text-on-surface'} font-semibold">
            ${metrics.errors_count} / ${metrics.retries_count}
          </div>
          <div class="font-code-sm text-code-sm text-on-surface-variant mt-0.5">${metrics.retries_count > 0 ? 'Transient 429 backoff' : 'Zero unhandled errors'}</div>
        </div>
        <div class="w-full bg-surface-container-highest h-1 rounded-full overflow-hidden">
          <div class="${metrics.errors_count > 0 ? 'bg-error' : 'bg-emerald-500'} h-full w-[100%]"></div>
        </div>
      </div>
    </div>
  `;
}
