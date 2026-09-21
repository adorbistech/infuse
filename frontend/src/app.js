/**
 * INFUSE Frontend Application Root (Hardened).
 * 
 * Bootstraps store, event listeners, routing, history filters, and renders pages into DOM.
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

      // Save policy button
      const savePolicyBtn = e.target.closest("#save-policy-btn");
      if (savePolicyBtn) {
        this.handleSavePolicy();
        return;
      }
    });

    // Global change delegation for selects and search
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
    });

    // Search input event (input event for instant responsiveness)
    this.root.addEventListener("input", (e) => {
      if (e.target.id === "historySearchInput") {
        this.store.setHistoryFilter("query", e.target.value);
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

  handleSavePolicy() {
    const form = this.root.querySelector("#governance-form");
    if (!form) return;
    const formData = new FormData(form);
    const updated = {
      ...this.store.state.policyData.policy,
      budget: {
        max_cost_per_task: parseFloat(formData.get("max_cost_per_task")) || 10.0,
        max_cost_per_day: parseFloat(formData.get("max_cost_per_day")) || 150.0,
        max_cost_per_month: parseFloat(formData.get("max_cost_per_month")) || 2500.0,
        currency: "USD"
      },
      tokens: {
        max_input_tokens: parseInt(formData.get("max_input_tokens"), 10) || 128000,
        max_output_tokens: parseInt(formData.get("max_output_tokens"), 10) || 8192,
        max_total_tokens: parseInt(formData.get("max_total_tokens"), 10) || 136192
      },
      requests: {
        max_rpm: parseInt(formData.get("max_rpm"), 10) || 60,
        max_requests_per_task: parseInt(formData.get("max_requests_per_task"), 10) || 25
      },
      runtime: {
        max_execution_time_seconds: parseInt(formData.get("max_execution_time_seconds"), 10) || 1800
      },
      actions: {
        budget_action: formData.get("budget_action") || "OPTIMIZE",
        token_action: formData.get("token_action") || "OPTIMIZE",
        request_action: formData.get("request_action") || "THROTTLE",
        runtime_action: formData.get("runtime_action") || "STOP",
        provider_failure_action: formData.get("provider_failure_action") || "SWITCH",
        anomaly_action: "STOP"
      }
    };
    this.store.savePolicy(updated);
  }

  render() {
    const state = this.store.state;
    // Remember search focus if present
    const activeSearch = document.activeElement?.id === "historySearchInput";
    const cursorPosition = activeSearch ? document.activeElement.selectionStart : null;

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

    // Restore search input focus and cursor if user was typing
    if (activeSearch) {
      const searchInput = this.root.querySelector("#historySearchInput");
      if (searchInput) {
        searchInput.focus();
        if (cursorPosition !== null) {
          searchInput.setSelectionRange(cursorPosition, cursorPosition);
        }
      }
    }
  }
}
