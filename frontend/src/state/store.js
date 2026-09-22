/**
 * Central Reactive Store for INFUSE Frontend (Hardened).
 * 
 * Formalizes explicit state separation:
 * 1. UI State (route, theme, activeEngineTab, executionId)
 * 2. Server-Derived Data State (executionData, policyData)
 * 3. Draft State (originalPolicyData, hasUnsavedChanges, draft revisions)
 * 4. Transient / Interaction State (status, historyFilter, policyFeedback, error)
 */

import { MockDataProvider } from "../data/MockDataProvider.js";
import {
  validateGovernancePolicy,
  GovernancePolicyViewModel,
  DataStatus,
  AppError
} from "../contracts/viewmodels.js";

export class Store {
  constructor(dataProvider = new MockDataProvider()) {
    this.dataProvider = dataProvider;
    this.state = {
      // 1. UI State
      route: "execution", // "execution" | "governance"
      theme: "dark",      // "dark" | "light"
      activeEngineTab: "token", // "token" | "economics" | "health" | "governor"
      executionId: "exec_01J8K7A2",

      // 2. Server-Derived Data State
      executionData: null,
      policyData: null,

      // 3. Draft State (Isolated from Server-Derived Baseline)
      originalPolicyData: null,

      // 4. Transient / Interaction State
      status: DataStatus.IDLE, // IDLE | LOADING | LOADED | EMPTY | ERROR
      isLoading: false,
      historyFilter: {
        query: "",
        state: "ALL",
        agent: "ALL"
      },
      policyFeedback: null, // { type: "success" | "error" | "info", message: string }
      error: null           // AppError | null
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

  clearError() {
    this.state.error = null;
    this.notify();
  }

  async loadExecutionData(executionId = this.state.executionId) {
    this.state.isLoading = true;
    this.state.status = DataStatus.LOADING;
    this.state.executionId = executionId;
    this.notify();
    try {
      const result = await this.dataProvider.getExecutionData(executionId);
      if (!result) {
        this.state.executionData = null;
        this.state.status = DataStatus.EMPTY;
      } else {
        this.state.executionData = result;
        this.state.status = DataStatus.LOADED;
      }
      this.state.error = null;
    } catch (err) {
      this.state.status = DataStatus.ERROR;
      this.state.error = err instanceof AppError ? err : new AppError(err.message || "Failed to load execution data", "FETCH_FAILED");
    } finally {
      this.state.isLoading = false;
      this.notify();
    }
  }

  async loadPolicyData() {
    this.state.isLoading = true;
    this.state.status = DataStatus.LOADING;
    this.notify();
    try {
      const policyResult = await this.dataProvider.getGovernancePolicy();
      if (!policyResult) {
        this.state.policyData = null;
        this.state.status = DataStatus.EMPTY;
      } else {
        this.state.policyData = policyResult;
        this.state.originalPolicyData = JSON.parse(JSON.stringify(this.state.policyData.policy || {}));
        this.state.status = DataStatus.LOADED;
      }
      this.state.error = null;
    } catch (err) {
      this.state.status = DataStatus.ERROR;
      this.state.error = err instanceof AppError ? err : new AppError(err.message || "Failed to load governance policy", "POLICY_FETCH_FAILED");
    } finally {
      this.state.isLoading = false;
      this.notify();
    }
  }

  async updateStateSimulation(targetState) {
    this.state.isLoading = true;
    this.state.status = DataStatus.LOADING;
    this.notify();
    try {
      this.state.executionData = await this.dataProvider.triggerStateChange(this.state.executionId, targetState);
      this.state.status = DataStatus.LOADED;
      this.state.error = null;
    } catch (err) {
      this.state.status = DataStatus.ERROR;
      this.state.error = err instanceof AppError ? err : new AppError(err.message || "Failed to change state", "SIMULATION_FAILED");
    } finally {
      this.state.isLoading = false;
      this.notify();
    }
  }

  /**
   * Update draft policy in memory, validate, and mark unsaved changes.
   */
  updatePolicyDraft(draftUpdates) {
    if (!this.state.policyData) return;
    
    const current = this.state.policyData.policy || {};
    const merged = {
      ...current,
      ...draftUpdates,
      budget: { ...(current.budget || {}), ...(draftUpdates.budget || {}) },
      tokens: { ...(current.tokens || {}), ...(draftUpdates.tokens || {}) },
      requests: { ...(current.requests || {}), ...(draftUpdates.requests || {}) },
      runtime: { ...(current.runtime || {}), ...(draftUpdates.runtime || {}) },
      providers: { ...(current.providers || {}), ...(draftUpdates.providers || {}) },
      web: { ...(current.web || {}), ...(draftUpdates.web || {}) },
      tools: { ...(current.tools || {}), ...(draftUpdates.tools || {}) },
      retries: { ...(current.retries || {}), ...(draftUpdates.retries || {}) },
      anomaly: { ...(current.anomaly || {}), ...(draftUpdates.anomaly || {}) },
      actions: { ...(current.actions || {}), ...(draftUpdates.actions || {}) }
    };

    const validation = validateGovernancePolicy(merged);
    this.state.policyData.policy = merged;
    this.state.policyData.has_unsaved_changes = true;
    this.state.policyData.validation_errors = validation.errors;
    this.notify();
  }

  /**
   * Revert all in-progress draft changes back to last saved baseline.
   */
  resetPolicyChanges() {
    if (!this.state.originalPolicyData) return;
    this.state.policyData.policy = JSON.parse(JSON.stringify(this.state.originalPolicyData));
    this.state.policyData.has_unsaved_changes = false;
    this.state.policyData.validation_errors = [];
    this.state.policyFeedback = {
      type: "info",
      message: "Unsaved changes discarded. Restored to baseline policy."
    };
    this.notify();
  }

  /**
   * Duplicate active policy into a new revision draft.
   */
  duplicatePolicy() {
    if (!this.state.policyData) return;
    const base = this.state.policyData.policy || {};
    const currentVer = base.version || "1.0.4";
    const parts = currentVer.replace(/^v/, "").split(".").map(Number);
    if (parts.length >= 3 && !isNaN(parts[2])) {
      parts[2] += 1;
    }
    const newVersion = `v${parts.join(".")}`;
    const newId = `pol_${Math.random().toString(36).substring(2, 9)}`;

    const duplicated = {
      ...JSON.parse(JSON.stringify(base)),
      policy_id: newId,
      name: `${base.name || "Default Policy"} (Copy)`,
      version: newVersion,
      is_active: true
    };

    this.state.policyData.policy = duplicated;
    this.state.policyData.has_unsaved_changes = true;
    this.state.policyData.validation_errors = [];
    this.state.policyFeedback = {
      type: "info",
      message: `Duplicated policy as draft revision ${newVersion} (${newId}). Click 'Save Active Policy' to commit.`
    };
    this.notify();
  }

  clearPolicyFeedback() {
    this.state.policyFeedback = null;
    this.notify();
  }

  async savePolicy(updatedPolicy) {
    const validation = validateGovernancePolicy(updatedPolicy);
    if (!validation.isValid) {
      if (this.state.policyData) {
        this.state.policyData.validation_errors = validation.errors;
      }
      this.state.policyFeedback = {
        type: "error",
        message: "Validation failed: " + validation.errors.join("; ")
      };
      this.notify();
      return;
    }

    this.state.isLoading = true;
    this.state.status = DataStatus.LOADING;
    this.notify();
    try {
      this.state.policyData = await this.dataProvider.saveGovernancePolicy(updatedPolicy);
      this.state.originalPolicyData = JSON.parse(JSON.stringify(this.state.policyData.policy || {}));
      this.state.policyData.has_unsaved_changes = false;
      this.state.policyData.validation_errors = [];
      this.state.policyFeedback = {
        type: "success",
        message: `Policy '${this.state.policyData.policy.name}' (${this.state.policyData.policy.version}) saved successfully.`
      };
      this.state.status = DataStatus.LOADED;
      this.state.error = null;
    } catch (err) {
      this.state.status = DataStatus.ERROR;
      const appErr = err instanceof AppError ? err : new AppError(err.message || "Failed to save policy", "POLICY_SAVE_FAILED");
      this.state.error = appErr;
      this.state.policyFeedback = {
        type: "error",
        message: appErr.message
      };
    } finally {
      this.state.isLoading = false;
      this.notify();
    }
  }

  async retryLastAction() {
    if (this.state.route === "governance") {
      return this.loadPolicyData();
    }
    return this.loadExecutionData(this.state.executionId);
  }
}
