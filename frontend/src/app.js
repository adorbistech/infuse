/**
 * INFUSE Frontend Application Root (Hardened).
 * 
 * Bootstraps store, event listeners, routing, history filters, policy editor, and renders pages into DOM.
 */

import { Store } from "./state/store.js";
import { MockDataProvider } from "./data/MockDataProvider.js";
import { renderHeader } from "./components/Header.js";
import { renderExecutionPage } from "./pages/ExecutionPage.js";
import { renderGovernancePage } from "./pages/GovernancePage.js";

export class InfuseApp {
  constructor(rootElement, dataProvider = new MockDataProvider()) {
    this.root = rootElement;
    this.store = new Store(dataProvider);
  }

  async init() {
    // Setup routing from hash
    const hash = window.location.hash.replace("#", "");
    if (hash === "governance") {
      this.store.setRoute("governance");
    } else {
      this.store.setRoute("execution");
    }

    // Subscribe to store updates
    this.store.subscribe(() => this.render());

    // Load initial data
    await Promise.all([
      this.store.loadExecutionData(),
      this.store.loadPolicyData()
    ]);

    // Attach global DOM event delegation
    this.bindEvents();
    this.render();
  }

  bindEvents() {
    // Global click delegation
    this.root.addEventListener("click", (e) => {
      // Navigation
      const navExec = e.target.closest("#nav-execution-btn");
      if (navExec) {
        window.location.hash = "execution";
        this.store.setRoute("execution");
        return;
      }

      const navGov = e.target.closest("#nav-governance-btn");
      if (navGov) {
        window.location.hash = "governance";
        this.store.setRoute("governance");
        return;
      }

      // Theme toggle
      const themeToggle = e.target.closest("#theme-toggle-btn");
      if (themeToggle) {
        const root = document.documentElement;
        const currentTheme = root.getAttribute("data-theme") || "dark";
        const nextTheme = currentTheme === "dark" ? "light" : "dark";
        root.setAttribute("data-theme", nextTheme);
        if (nextTheme === "dark") {
          root.classList.add("dark");
        } else {
          root.classList.remove("dark");
        }
        this.store.setTheme(nextTheme);
        return;
      }

      // State simulation pill clicked
      const statePill = e.target.closest(".state-pill");
      if (statePill) {
        const targetState = statePill.getAttribute("data-state");
        if (targetState) {
          this.store.updateStateSimulation(targetState);
        }
        return;
      }

      // Runtime engine tab clicked
      const engineTab = e.target.closest(".engine-tab-btn");
      if (engineTab) {
        const tabKey = engineTab.getAttribute("data-tab");
        if (tabKey) {
          this.store.setActiveEngineTab(tabKey);
        }
        return;
      }

      // Refresh button
      const refreshBtn = e.target.closest("#refreshBtn");
      if (refreshBtn) {
        this.store.loadExecutionData();
        return;
      }

      // Select execution row or button
      const selectBtn = e.target.closest(".select-exec-btn");
      if (selectBtn) {
        const execId = selectBtn.getAttribute("data-exec-id");
        if (execId) {
          this.store.loadExecutionData(execId);
        }
        return;
      }

      const execRow = e.target.closest("[data-exec-row]");
      if (execRow && !e.target.closest("button") && !e.target.closest("select") && !e.target.closest("input")) {
        const execId = execRow.getAttribute("data-exec-row");
        if (execId) {
          this.store.loadExecutionData(execId);
        }
        return;
      }

      // Policy action buttons
      const savePolicyBtn = e.target.closest("#save-policy-btn");
      if (savePolicyBtn) {
        this.handleSavePolicy();
        return;
      }

      const cancelPolicyBtn = e.target.closest("#cancel-policy-btn");
      if (cancelPolicyBtn && !cancelPolicyBtn.disabled) {
        this.store.resetPolicyChanges();
        return;
      }

      const duplicatePolicyBtn = e.target.closest("#duplicate-policy-btn");
      if (duplicatePolicyBtn) {
        this.store.duplicatePolicy();
        return;
      }

      const dismissFeedbackBtn = e.target.closest("#dismiss-feedback-btn");
      if (dismissFeedbackBtn) {
        this.store.clearPolicyFeedback();
        return;
      }
    });

    // Global change delegation for selects, checkboxes, and filters
    this.root.addEventListener("change", (e) => {
      // Execution header dropdown change
      if (e.target.id === "execSelectDropdown") {
        const selectedId = e.target.value;
        if (selectedId) {
          this.store.loadExecutionData(selectedId);
        }
        return;
      }

      // State filter dropdown
      if (e.target.id === "historyStateFilter") {
        this.store.setHistoryFilter("state", e.target.value);
        return;
      }

      // Agent filter dropdown
      if (e.target.id === "historyAgentFilter") {
        this.store.setHistoryFilter("agent", e.target.value);
        return;
      }

      // Governance form field changes
      if (e.target.closest("#governance-form")) {
        this.handleGovernanceFormChange();
      }
    });

    // Search and form input events
    this.root.addEventListener("input", (e) => {
      if (e.target.id === "historySearchInput") {
        this.store.setHistoryFilter("query", e.target.value);
        return;
      }

      if (e.target.closest("#governance-form")) {
        this.handleGovernanceFormChange();
      }
    });

    window.addEventListener("hashchange", () => {
      const hash = window.location.hash.replace("#", "");
      if (hash === "governance") {
        this.store.setRoute("governance");
      } else {
        this.store.setRoute("execution");
      }
    });
  }

  extractPolicyFormData(form) {
    if (!form) return null;
    const formData = new FormData(form);

    const providerCheckboxes = form.querySelectorAll(".provider-allow-checkbox:checked");
    const checkedProviders = Array.from(providerCheckboxes)
      .map(cb => cb.getAttribute("data-provider-id"))
      .filter(Boolean);

    const allowedModelsRaw = formData.get("allowed_models") || "";
    const allowedModels = allowedModelsRaw.split(",").map(s => s.trim()).filter(Boolean);

    const blockedModelsRaw = formData.get("blocked_models") || "";
    const blockedModels = blockedModelsRaw.split(",").map(s => s.trim()).filter(Boolean);

    const allowedDomainsRaw = formData.get("allowed_domains") || "*";
    const allowedDomains = allowedDomainsRaw.split(",").map(s => s.trim()).filter(Boolean);

    const blockedDomainsRaw = formData.get("blocked_domains") || "";
    const blockedDomains = blockedDomainsRaw.split(",").map(s => s.trim()).filter(Boolean);

    const allowedToolsRaw = formData.get("allowed_tools") || "*";
    const allowedTools = allowedToolsRaw.split(",").map(s => s.trim()).filter(Boolean);

    const blockedToolsRaw = formData.get("blocked_tools") || "";
    const blockedTools = blockedToolsRaw.split(",").map(s => s.trim()).filter(Boolean);

    const retryErrorsRaw = formData.get("retry_on_errors") || "";
    const retryOnErrors = retryErrorsRaw.split(",").map(s => s.trim()).filter(Boolean);

    const basePolicy = this.store.state.policyData?.policy || {};

    return {
      ...basePolicy,
      budget: {
        ...(basePolicy.budget || {}),
        max_cost_per_task: parseFloat(formData.get("max_cost_per_task")) ?? 10.0,
        max_cost_per_day: parseFloat(formData.get("max_cost_per_day")) ?? 150.0,
        max_cost_per_month: parseFloat(formData.get("max_cost_per_month")) ?? 2500.0,
        currency: "USD"
      },
      tokens: {
        ...(basePolicy.tokens || {}),
        max_input_tokens: parseInt(formData.get("max_input_tokens"), 10) ?? 128000,
        max_output_tokens: parseInt(formData.get("max_output_tokens"), 10) ?? 8192,
        max_total_tokens: parseInt(formData.get("max_total_tokens"), 10) ?? 136192
      },
      requests: {
        ...(basePolicy.requests || {}),
        max_rpm: parseInt(formData.get("max_rpm"), 10) ?? 60,
        max_requests_per_task: parseInt(formData.get("max_requests_per_task"), 10) ?? 25
      },
      runtime: {
        ...(basePolicy.runtime || {}),
        max_execution_time_seconds: parseInt(formData.get("max_execution_time_seconds"), 10) ?? 1800
      },
      providers: {
        ...(basePolicy.providers || {}),
        allowed_providers: checkedProviders.length > 0 ? checkedProviders : ["anthropic", "openai", "gemini", "deepseek"],
        allowed_models: allowedModels.length > 0 ? allowedModels : ["claude-3-5-sonnet", "gpt-4o", "gemini-1.5-pro", "deepseek-chat"],
        blocked_providers: basePolicy.providers?.blocked_providers || [],
        blocked_models: blockedModels
      },
      web: {
        ...(basePolicy.web || {}),
        enabled: form.querySelector('[name="web_enabled"]')?.checked ?? true,
        max_web_requests_per_task: parseInt(formData.get("max_web_requests_per_task"), 10) ?? 20,
        allowed_domains: allowedDomains.length > 0 ? allowedDomains : ["*"],
        blocked_domains: blockedDomains
      },
      tools: {
        ...(basePolicy.tools || {}),
        enabled: form.querySelector('[name="tools_enabled"]')?.checked ?? true,
        max_tool_calls_per_task: parseInt(formData.get("max_tool_calls_per_task"), 10) ?? 50,
        max_consecutive_tool_failures: parseInt(formData.get("max_consecutive_tool_failures"), 10) ?? 3,
        allowed_tools: allowedTools.length > 0 ? allowedTools : ["*"],
        blocked_tools: blockedTools
      },
      retries: {
        ...(basePolicy.retries || {}),
        max_retries: parseInt(formData.get("max_retries"), 10) ?? 3,
        backoff_factor: parseFloat(formData.get("backoff_factor")) ?? 1.5,
        retry_on_errors: retryOnErrors.length > 0 ? retryOnErrors : ["rate_limit", "timeout", "503_service_unavailable"],
        fallback_provider_on_failure: form.querySelector('[name="fallback_provider_on_failure"]')?.checked ?? true
      },
      anomaly: {
        ...(basePolicy.anomaly || {}),
        token_velocity_surge_threshold: parseFloat(formData.get("token_velocity_surge_threshold")) ?? 500,
        repetitive_loop_threshold: parseInt(formData.get("repetitive_loop_threshold"), 10) ?? 4,
        circuit_breaker_enabled: form.querySelector('[name="circuit_breaker_enabled"]')?.checked ?? true
      },
      actions: {
        budget_action: formData.get("budget_action") || "OPTIMIZE",
        token_action: formData.get("token_action") || "OPTIMIZE",
        request_action: formData.get("request_action") || "THROTTLE",
        runtime_action: formData.get("runtime_action") || "STOP",
        provider_failure_action: formData.get("provider_failure_action") || "SWITCH",
        anomaly_action: formData.get("anomaly_action") || "STOP"
      }
    };
  }

  handleGovernanceFormChange() {
    const form = this.root.querySelector("#governance-form");
    if (!form) return;
    const draft = this.extractPolicyFormData(form);
    if (draft) {
      this.store.updatePolicyDraft(draft);
    }
  }

  handleSavePolicy() {
    const form = this.root.querySelector("#governance-form");
    if (!form) return;
    const updated = this.extractPolicyFormData(form);
    if (updated) {
      this.store.savePolicy(updated);
    }
  }

  render() {
    const state = this.store.state;

    // Remember active focused element and selection range
    const activeEl = document.activeElement;
    const activeId = activeEl?.id;
    const activeName = activeEl?.getAttribute("name");
    const activeTagName = activeEl?.tagName;
    const isInputOrSelect = activeTagName === "INPUT" || activeTagName === "SELECT" || activeTagName === "TEXTAREA";
    const cursorStart = (activeEl && (activeTagName === "INPUT" || activeTagName === "TEXTAREA")) ? activeEl.selectionStart : null;
    const cursorEnd = (activeEl && (activeTagName === "INPUT" || activeTagName === "TEXTAREA")) ? activeEl.selectionEnd : null;

    const pageContent = state.route === "governance" 
      ? renderGovernancePage(this.store)
      : renderExecutionPage(this.store);

    this.root.innerHTML = `
      ${renderHeader(state, this.store)}
      <main class="flex flex-col relative w-full pt-16 pb-24 bg-surface min-h-screen">
        <div class="flex flex-col w-full text-on-surface px-3 py-4 max-w-7xl mx-auto">
          ${pageContent}
        </div>
      </main>
    `;

    // Restore active element focus and cursor position if present
    if (isInputOrSelect && (activeId || activeName)) {
      const selector = activeId ? `#${activeId}` : `[name="${activeName}"]`;
      const el = this.root.querySelector(selector);
      if (el) {
        el.focus();
        if (cursorStart !== null && typeof el.setSelectionRange === "function") {
          try {
            el.setSelectionRange(cursorStart, cursorEnd);
          } catch (_) {
            // Ignore for non-range inputs (e.g. number/checkbox)
          }
        }
      }
    }
  }
}
