/**
 * Central Reactive Store for INFUSE Frontend (Hardened).
 * 
 * Manages UI state, selected routes, active view models, filters, theme, and subscribers.
 */

import { MockDataProvider } from "../data/MockDataProvider.js";

export class Store {
  constructor(dataProvider = new MockDataProvider()) {
    this.dataProvider = dataProvider;
    this.state = {
      route: "execution", // "execution" | "governance"
      theme: "dark",
      executionId: "exec_01J8K7A2",
      activeEngineTab: "token", // "token" | "economics" | "health" | "governor"
      historyFilter: {
        query: "",
        state: "ALL",
        agent: "ALL"
      },
      executionData: null,
      policyData: null,
      isLoading: false,
      error: null
    };
    this.subscribers = new Set();
  }

  subscribe(callback) {
    this.subscribers.add(callback);
    return () => this.subscribers.delete(callback);
  }

  notify() {
    for (const sub of this.subscribers) {
      try {
        sub(this.state);
      } catch (err) {
        console.error("Store subscriber notification error:", err);
      }
    }
  }

  setRoute(route) {
    if (this.state.route !== route) {
      this.state.route = route;
      this.notify();
    }
  }

  setTheme(theme) {
    this.state.theme = theme;
    this.notify();
  }

  setActiveEngineTab(tab) {
    this.state.activeEngineTab = tab;
    this.notify();
  }

  setHistoryFilter(filterKey, value) {
    this.state.historyFilter[filterKey] = value;
    this.notify();
  }

  async loadExecutionData(executionId = this.state.executionId) {
    this.state.isLoading = true;
    this.state.executionId = executionId;
    this.notify();
    try {
      this.state.executionData = await this.dataProvider.getExecutionData(executionId);
      this.state.error = null;
    } catch (err) {
      this.state.error = err.message || "Failed to load execution data";
    } finally {
      this.state.isLoading = false;
      this.notify();
    }
  }

  async loadPolicyData() {
    this.state.isLoading = true;
    this.notify();
    try {
      this.state.policyData = await this.dataProvider.getGovernancePolicy();
      this.state.error = null;
    } catch (err) {
      this.state.error = err.message || "Failed to load governance policy";
    } finally {
      this.state.isLoading = false;
      this.notify();
    }
  }

  async updateStateSimulation(targetState) {
    this.state.isLoading = true;
    this.notify();
    try {
      this.state.executionData = await this.dataProvider.triggerStateChange(this.state.executionId, targetState);
      this.state.error = null;
    } catch (err) {
      this.state.error = err.message || "Failed to change state";
    } finally {
      this.state.isLoading = false;
      this.notify();
    }
  }

  async savePolicy(updatedPolicy) {
    this.state.isLoading = true;
    this.notify();
    try {
      this.state.policyData = await this.dataProvider.saveGovernancePolicy(updatedPolicy);
      this.state.error = null;
    } catch (err) {
      this.state.error = err.message || "Failed to save policy";
    } finally {
      this.state.isLoading = false;
      this.notify();
    }
  }
}
