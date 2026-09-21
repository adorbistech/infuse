/**
 * Provider / Model Health Panel Component.
 */

export function renderHealthPanel(health) {
  const isHealthy = health.status === "HEALTHY";

  return `
    <div class="bg-surface-container rounded-xl p-4 shadow-sm flex flex-col gap-2 border border-outline-variant/15">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <span class="w-2 h-2 rounded-full ${isHealthy ? 'bg-emerald-400' : 'bg-tertiary'} animate-pulse"></span>
          <span class="font-title-md text-title-md text-on-surface">${health.provider} ${health.model}</span>
        </div>
        <span class="font-code-sm text-code-sm ${isHealthy ? 'text-emerald-400' : 'text-tertiary'}">${health.status}</span>
      </div>
      <div class="grid grid-cols-3 gap-2 pt-1 text-body-sm">
        <div class="bg-surface-container-low p-2 rounded-lg">
          <span class="font-label-sm text-label-sm text-on-surface-variant block">Latency</span>
          <span class="font-code-sm text-body-md text-on-surface font-medium">${health.latency_ms.toFixed(0)}ms</span>
        </div>
        <div class="bg-surface-container-low p-2 rounded-lg">
          <span class="font-label-sm text-label-sm text-on-surface-variant block">Availability</span>
          <span class="font-code-sm text-body-md text-on-surface font-medium">${health.availability_percent.toFixed(2)}%</span>
        </div>
        <div class="bg-surface-container-low p-2 rounded-lg">
          <span class="font-label-sm text-label-sm text-on-surface-variant block">Error Rate</span>
          <span class="font-code-sm text-body-md ${health.error_rate_percent > 1 ? 'text-error' : 'text-on-surface'} font-medium">${health.error_rate_percent.toFixed(2)}%</span>
        </div>
      </div>
    </div>
  `;
}
