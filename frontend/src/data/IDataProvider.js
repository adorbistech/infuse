/**
 * Interface defining the stable data & state provider contract for the INFUSE frontend.
 * 
 * Formalizes the boundary between UI components/store and data sources:
 * - MockDataProvider (Development & Unit/Integration testing)
 * - ApiDataProvider (Future Block 05: Universal HTTP API integration)
 * 
 * UI components must NEVER communicate with network endpoints or databases directly.
 */

export class IDataProvider {
  /**
   * Retrieve normalized execution telemetry bundle by execution ID.
   * 
   * @param {string} [executionId] 
   * @returns {Promise<import("../contracts/viewmodels.js").ExecutionBundleViewModel>}
   */
  async getExecutionData(executionId) {
    throw new Error("IDataProvider.getExecutionData() must be implemented by provider subclass.");
  }

  /**
   * Retrieve filterable execution history list.
   * 
   * @param {Object} [filter] 
   * @param {string} [filter.query]
   * @param {string} [filter.state]
   * @param {string} [filter.agent]
   * @returns {Promise<import("../contracts/viewmodels.js").ExecutionHistoryItemViewModel[]>}
   */
  async getExecutionHistory(filter = {}) {
    throw new Error("IDataProvider.getExecutionHistory() must be implemented by provider subclass.");
  }

  /**
   * Retrieve the active Governance Policy ViewModel.
   * 
   * @returns {Promise<import("../contracts/viewmodels.js").GovernancePolicyViewModel>}
   */
  async getGovernancePolicy() {
    throw new Error("IDataProvider.getGovernancePolicy() must be implemented by provider subclass.");
  }

  /**
   * Persist / update a Governance Policy through the provider.
   * 
   * @param {Object} updatedPolicy 
   * @returns {Promise<import("../contracts/viewmodels.js").GovernancePolicyViewModel>}
   */
  async saveGovernancePolicy(updatedPolicy) {
    throw new Error("IDataProvider.saveGovernancePolicy() must be implemented by provider subclass.");
  }

  /**
   * Simulate or trigger a state transition (for development, testing, and interactive simulation).
   * 
   * @param {string} executionId 
   * @param {string} targetState (NORMAL | COST_PRESSURE | RUNAWAY | QUALITY_DEGRADED | PROVIDER_CONSTRAINED)
   * @returns {Promise<import("../contracts/viewmodels.js").ExecutionBundleViewModel>}
   */
  async triggerStateChange(executionId, targetState) {
    throw new Error("IDataProvider.triggerStateChange() must be implemented by provider subclass.");
  }
}
