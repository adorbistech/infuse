/**
 * Interface defining the contract for data providers in the INFUSE frontend.
 * Enables switching between MockDataProvider (now) and ApiDataProvider (future Block 05).
 */

export class IDataProvider {
  /**
   * Get the complete Execution ViewModels bundle for an execution ID.
   * @param {string} executionId 
   * @returns {Promise<{summary: ExecutionSummaryViewModel, metrics: ExecutionMetricsViewModel, state: ExecutionStateViewModel, governor: GovernorDecisionViewModel, health: ProviderModelHealthViewModel, timeline: ExecutionTimelineEventViewModel[], history: ExecutionHistoryItemViewModel[]}>}
   */
  async getExecutionData(executionId) {
    throw new Error("Method getExecutionData() must be implemented.");
  }

  /**
   * Get the active Governance Policy ViewModel.
   * @returns {Promise<GovernancePolicyViewModel>}
   */
  async getGovernancePolicy() {
    throw new Error("Method getGovernancePolicy() must be implemented.");
  }

  /**
   * Save / Update a Governance Policy.
   * @param {Object} updatedPolicy 
   * @returns {Promise<GovernancePolicyViewModel>}
   */
  async saveGovernancePolicy(updatedPolicy) {
    throw new Error("Method saveGovernancePolicy() must be implemented.");
  }

  /**
   * Simulate a state transition (for demonstration and testing).
   * @param {string} executionId 
   * @param {string} targetState (NORMAL | COST_PRESSURE | RUNAWAY | QUALITY_DEGRADED | PROVIDER_CONSTRAINED)
   * @returns {Promise<Object>}
   */
  async triggerStateChange(executionId, targetState) {
    throw new Error("Method triggerStateChange() must be implemented.");
  }
}
