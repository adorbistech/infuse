/**
 * Header Component for INFUSE Console.
 */

export function renderHeader(state, store) {
  const isExecutionActive = state.route === "execution";
  const isGovernanceActive = state.route === "governance";

  return `
    <header class="fixed top-0 inset-x-0 z-50 bg-surface/85 backdrop-blur-xl shadow-[0_1px_8px_rgba(0,0,0,0.25)] pt-safe">
      <div class="h-16 px-3 flex items-center justify-between gap-2 max-w-7xl mx-auto">
        <!-- Brand & Logo -->
        <div class="flex items-center gap-2 min-w-0 flex-shrink-0">
          <div class="flex items-center gap-2">
            <span class="font-display text-headline-sm font-bold text-primary tracking-tight">INFUSE</span>
            <span class="font-code-sm text-code-sm uppercase tracking-wider text-primary px-1.5 py-0.5 rounded bg-primary/10 hidden sm:inline-block">
              Execution Intelligence
            </span>
          </div>
        </div>

        <!-- Global Navigation -->
        <nav class="flex items-center gap-1.5 flex-1 justify-center max-w-[240px]" aria-label="Main Navigation">
          <button 
            class="flex-1 h-9 px-3 rounded-lg flex items-center justify-center font-title-md text-body-sm transition-all duration-150 ${
              isExecutionActive 
                ? 'bg-surface-container-high text-primary font-semibold shadow-sm' 
                : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high'
            }" 
            id="nav-execution-btn"
            type="button">
            Execution
          </button>
          <button 
            class="flex-1 h-9 px-3 rounded-lg flex items-center justify-center font-title-md text-body-sm transition-all duration-150 ${
              isGovernanceActive 
                ? 'bg-surface-container-high text-primary font-semibold shadow-sm' 
                : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high'
            }" 
            id="nav-governance-btn"
            type="button">
            Governance
          </button>
        </nav>

        <!-- Status & Utilities -->
        <div class="flex items-center gap-1.5 flex-shrink-0">
          <div class="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-surface-container-high">
            <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span class="font-code-sm text-code-sm text-on-surface">System Operational</span>
          </div>
          <div class="hidden xs:flex items-center px-2 py-1 rounded bg-surface-container font-code-sm text-code-sm text-on-surface-variant">
            workspace: default
          </div>
          <button 
            aria-label="Toggle theme" 
            class="w-9 h-9 flex items-center justify-center text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high rounded-lg transition-colors" 
            id="theme-toggle-btn" 
            type="button">
            <span class="material-symbols-outlined text-[20px]">contrast</span>
          </button>
          <div class="w-8 h-8 rounded-full bg-primary flex items-center justify-center shadow-sm">
            <span class="material-symbols-outlined text-on-primary text-[18px]">person</span>
          </div>
        </div>
      </div>
    </header>
  `;
}
