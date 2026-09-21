/**
 * Visualization Charts Component (Hardened SVG Token Growth & Cost vs Budget).
 */

export function renderCharts(metrics) {
  const tokenSeries = metrics.token_growth_series && metrics.token_growth_series.length > 0 
    ? metrics.token_growth_series 
    : [
        { time: "14:32", tokens: 12000 },
        { time: "14:35", tokens: 38000 },
        { time: "14:38", tokens: 52000 },
        { time: "14:41", tokens: metrics.total_tokens || 69480 }
      ];

  const costSeries = metrics.cost_series && metrics.cost_series.length > 0
    ? metrics.cost_series
    : [
        { time: "14:32", cost: 0.02 },
        { time: "14:35", cost: 0.09 },
        { time: "14:38", cost: 0.15 },
        { time: "14:41", cost: metrics.current_cost_usd || 0.184 }
      ];

  return `
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-3">
      <!-- Chart 1: Token Growth -->
      <div class="bg-surface-container rounded-xl p-4 shadow-sm flex flex-col gap-3 border border-outline-variant/15">
        <div class="flex items-center justify-between">
          <div>
            <h2 class="font-title-md text-title-md text-on-surface">TOKEN GROWTH</h2>
            <p class="font-body-sm text-body-sm text-on-surface-variant">Cumulative context growth throughout multi-step trajectory</p>
          </div>
          <span class="font-code-sm text-code-sm text-primary font-semibold tabular-nums">${metrics.total_tokens.toLocaleString()} tokens</span>
        </div>

        <!-- SVG Line/Area Graph -->
        <div class="relative w-full h-44 bg-surface-container-low rounded-lg p-2 flex flex-col justify-end overflow-hidden" role="region" aria-label="Token Growth Time Series Chart">
          <svg class="w-full h-full overflow-visible" preserveAspectRatio="none" viewBox="0 0 400 120" role="img" aria-label="Token growth trajectory curve">
            <defs>
              <linearGradient id="tokenGrad" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stop-color="#adc6ff" stop-opacity="0.35"></stop>
                <stop offset="100%" stop-color="#adc6ff" stop-opacity="0.0"></stop>
              </linearGradient>
            </defs>
            <!-- Area -->
            <polygon fill="url(#tokenGrad)" points="10,110 50,95 120,80 180,60 250,45 320,30 380,15 380,110 10,110"></polygon>
            <!-- Line -->
            <polyline fill="none" points="10,110 50,95 120,80 180,60 250,45 320,30 380,15" stroke="#adc6ff" stroke-linecap="round" stroke-width="2.5"></polyline>
            <!-- Output Tokens Line (Lower volume dashed) -->
            <polyline fill="none" points="10,115 50,110 120,105 180,95 250,85 320,75 380,65" stroke="#d0bcff" stroke-dasharray="3,3" stroke-width="1.5"></polyline>
            <!-- Active point dot -->
            <circle cx="380" cy="15" fill="#adc6ff" r="4.5" stroke="#101419" stroke-width="2"></circle>
          </svg>
          <div class="flex justify-between font-label-sm text-label-sm text-on-surface-variant/70 pt-1 border-t border-outline-variant/20 mt-1 tabular-nums">
            ${tokenSeries.map(p => `<span>${p.time}</span>`).join("")}
          </div>
        </div>
      </div>

      <!-- Chart 2: Cost Over Time with Budget Line -->
      <div class="bg-surface-container rounded-xl p-4 shadow-sm flex flex-col gap-3 border border-outline-variant/15">
        <div class="flex items-center justify-between">
          <div>
            <h2 class="font-title-md text-title-md text-on-surface">COST OVER TIME</h2>
            <p class="font-body-sm text-body-sm text-on-surface-variant">Real-time financial burn vs configured policy boundary</p>
          </div>
          <div class="flex items-center gap-2">
            <span class="inline-flex items-center gap-1 font-label-sm text-label-sm text-tertiary">
              <span class="w-2 h-0.5 bg-tertiary"></span>
              Warning ($0.20)
            </span>
            <span class="font-code-sm text-code-sm text-on-surface font-semibold tabular-nums">$${metrics.current_cost_usd.toFixed(3)}</span>
          </div>
        </div>

        <!-- SVG Cost Chart with Threshold -->
        <div class="relative w-full h-44 bg-surface-container-low rounded-lg p-2 flex flex-col justify-end overflow-hidden" role="region" aria-label="Cost Over Time Time Series Chart">
          <svg class="w-full h-full overflow-visible" preserveAspectRatio="none" viewBox="0 0 400 120" role="img" aria-label="Cost over time vs budget limit curve">
            <defs>
              <linearGradient id="costGrad" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stop-color="#df7412" stop-opacity="0.35"></stop>
                <stop offset="100%" stop-color="#df7412" stop-opacity="0.0"></stop>
              </linearGradient>
            </defs>
            <!-- Budget Warning Boundary Reference ($0.20 threshold line) -->
            <line stroke="#ffb786" stroke-dasharray="4,4" stroke-opacity="0.8" stroke-width="1.5" x1="0" x2="400" y1="35" y2="35"></line>
            <!-- Cost Area -->
            <polygon fill="url(#costGrad)" points="10,115 60,110 130,95 200,75 280,55 350,42 380,38 380,115 10,115"></polygon>
            <!-- Cost Polyline -->
            <polyline fill="none" points="10,115 60,110 130,95 200,75 280,55 350,42 380,38" stroke="#df7412" stroke-linecap="round" stroke-width="2.5"></polyline>
            <!-- Marker dot -->
            <circle cx="380" cy="38" fill="#ffb786" r="4.5" stroke="#101419" stroke-width="2"></circle>
          </svg>
          <div class="flex justify-between font-label-sm text-label-sm text-on-surface-variant/70 pt-1 border-t border-outline-variant/20 mt-1 tabular-nums">
            <span>$0.00</span>
            <span>$0.05</span>
            <span>$0.10</span>
            <span class="text-tertiary font-semibold tabular-nums">$${metrics.current_cost_usd.toFixed(3)} (Current)</span>
          </div>
        </div>
      </div>
    </div>
  `;
}
