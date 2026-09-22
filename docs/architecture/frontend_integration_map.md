# INFUSE Frontend Architecture & Backend Integration Map

**Milestones:** 
- Block 01: Frontend Foundation & Contract Integration (Frozen)
- Block 02: Frontend Execution / Information Surface Hardening (Frozen)
- Block 03: Frontend Governance / Policy Surface Hardening (Frozen)
- Block 04: Frontend Data & State Contract (Frozen)

**Visual Baseline:** Stitch Console (`Autonomous Governance Obsidian` Theme)  
**Contract Baseline:** Block 00 Universal Contracts (`infuse.contracts.frontend`, `infuse.contracts.policy`)  

---

## 1. Overview & Data Boundary

The INFUSE Frontend architecture establishes a strict, formal boundary separating user-facing presentation components from data sources and future backend infrastructure:

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        INFUSE FRONTEND CONSOLE                         │
│                                                                        │
│  [Execution / Information Surface]       [Governance / Policy Surface] │
│  ├── Execution Context & Switcher        ├── Active Policy Overview    │
│  ├── Dedicated Execution State (5 States)├── 10 Policy Control Sections│
│  ├── 8-Card Metrics Grid (Tabular-nums)  │   (Budget, Tokens, Requests,│
│  ├── SVG Token Growth & Cost Time-Series │    Runtime, Providers, Web, │
│  ├── Web, Tool, File & Retry Activity    │    Tools, Retry, Anomaly,   │
│  ├── Central Governor Action Banner      │    Action Matrix)           │
│  ├── Provider & Model Health             ├── Draft & Dirty State Track │
│  ├── Traceable Event Timeline            ├── Client-side UX Validation │
│  ├── Runtime Engine Signal Inspector     └── Policy Revision Duplicate │
│  └── Filterable Execution History                                      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
                         Pages / UI Components
                                    │
                                    ▼
                       Application Store (State)
          ┌─────────────────────────┴─────────────────────────┐
          │ • Server-Derived Data State (executionData, etc.) │
          │ • UI State (route, theme, activeEngineTab, etc.)  │
          │ • Draft State (policyDraft, hasUnsavedChanges)   │
          │ • Transient State (status, filter, feedback)      │
          └─────────────────────────┬─────────────────────────┘
                                    │
                                    ▼
                        IDataProvider Interface
                                    │
                   ┌────────────────┴────────────────┐
                   ▼                                 ▼
            MockDataProvider                 ApiDataProvider
         (Active in Blocks 01-04)            (FUTURE Block 05)
                                                     │
                                                     ▼
                                            Universal HTTP API
                                       (/v1/executions, /v1/policies)
```

> [!IMPORTANT]
> **Boundary Decoupling Guarantee:**
> UI components, pages, and store modules NEVER import or communicate directly with backend runtimes, database drivers, HTTP clients, or provider SDKs. All data flows exclusively through normalized ViewModels mediated by the `IDataProvider` interface.

---

## 2. Store State Compartmentalization

The central store explicitly isolates four categories of application state:

1. **Server-Derived Data State:**
   - `executionData`: Normalized `ExecutionBundleViewModel` (summary, metrics, state, governor, health, timeline, history).
   - `policyData`: Normalized `GovernancePolicyViewModel`.
2. **UI State:**
   - `route`: Active navigation view (`"execution"` | `"governance"`).
   - `theme`: Theme setting (`"dark"` | `"light"`).
   - `activeEngineTab`: Selected runtime engine tab (`"token"` | `"economics"` | `"health"` | `"governor"`).
   - `executionId`: ID of the currently selected execution run.
3. **Draft State (Isolated from Server-Derived Baseline):**
   - `originalPolicyData`: Snapshot of active policy received from provider.
   - `has_unsaved_changes`: Boolean dirty flag.
   - Draft revisions generated via `duplicatePolicy()` or form edits before explicit save.
4. **Transient / Interaction State:**
   - `status`: Normalized `DataStatus` (`IDLE`, `LOADING`, `LOADED`, `EMPTY`, `ERROR`).
   - `isLoading`: Boolean loading indicator.
   - `historyFilter`: Multi-dimensional filters `{ query, state, agent }`.
   - `policyFeedback`: Toast feedback `{ type, message }`.
   - `error`: Normalized `AppError` instance `{ message, code, details, timestamp }`.

---

## 3. Normalized ViewModels Contract Map

| ViewModel Class | Target Component | Corresponding Block 00 Python Contract | Future Backend Origin |
|---|---|---|---|
| [`ExecutionBundleViewModel`](file:///Users/ssd/infuse/frontend/src/contracts/viewmodels.js) | [`ExecutionPage.js`](file:///Users/ssd/infuse/frontend/src/pages/ExecutionPage.js) | Aggregate Container | `GET /v1/executions/{id}` |
| [`ExecutionSummaryViewModel`](file:///Users/ssd/infuse/frontend/src/contracts/viewmodels.js) | [`ExecutionHeader.js`](file:///Users/ssd/infuse/frontend/src/components/ExecutionHeader.js) | `ExecutionSummaryContract` | Execution Lifecycle Engine |
| [`ExecutionStateViewModel`](file:///Users/ssd/infuse/frontend/src/contracts/viewmodels.js) | [`StateSelector.js`](file:///Users/ssd/infuse/frontend/src/components/StateSelector.js) | `ExecutionStateContract` | Execution State Engine |
| [`ExecutionMetricsViewModel`](file:///Users/ssd/infuse/frontend/src/contracts/viewmodels.js) | [`MetricsGrid.js`](file:///Users/ssd/infuse/frontend/src/components/MetricsGrid.js), [`Charts.js`](file:///Users/ssd/infuse/frontend/src/components/Charts.js), [`ActivityPanel.js`](file:///Users/ssd/infuse/frontend/src/components/ActivityPanel.js) | `ExecutionMetricsContract` | Token & Economics Observers |
| [`GovernorDecisionViewModel`](file:///Users/ssd/infuse/frontend/src/contracts/viewmodels.js) | [`GovernorPanel.js`](file:///Users/ssd/infuse/frontend/src/components/GovernorPanel.js) | `GovernorDecisionContract` | Central Governor |
| [`ProviderModelHealthViewModel`](file:///Users/ssd/infuse/frontend/src/contracts/viewmodels.js) | [`HealthPanel.js`](file:///Users/ssd/infuse/frontend/src/components/HealthPanel.js) | `ProviderModelHealthContract` | Health Engine |
| [`ExecutionTimelineEventViewModel`](file:///Users/ssd/infuse/frontend/src/contracts/viewmodels.js) | [`Timeline.js`](file:///Users/ssd/infuse/frontend/src/components/Timeline.js) | `ExecutionTimelineEventContract` | Event Bus & Ledger |
| [`ExecutionHistoryItemViewModel`](file:///Users/ssd/infuse/frontend/src/contracts/viewmodels.js) | [`HistoryTable.js`](file:///Users/ssd/infuse/frontend/src/components/HistoryTable.js) | `ExecutionHistoryContract` | Execution History Store |
| [`GovernancePolicyViewModel`](file:///Users/ssd/infuse/frontend/src/contracts/viewmodels.js) | [`PolicyForm.js`](file:///Users/ssd/infuse/frontend/src/components/PolicyForm.js) | `GovernancePolicyContract` | Policy Manager / Engine |

---

## 4. Normalized Page Presentation States

Both `ExecutionPage` and `GovernancePage` handle four standard states:

* **Loading (`DataStatus.LOADING`):** Animated Stitch skeleton pulse placeholders and loading indicator.
* **Error (`DataStatus.ERROR`):** Glass-panel alert with normalized `AppError` code/message and contextual Retry button (`#retry-exec-btn`, `#retry-gov-btn`).
* **Empty (`DataStatus.EMPTY`):** Helpful empty telemetry banner with recovery actions (`#load-default-exec-btn`).
* **Loaded (`DataStatus.LOADED`):** Complete glass-box telemetry and interactive surfaces.

---

## 5. Canonical Enums & Action Vocabularies

### 5.1 Execution States (5 Canonical States)
`NORMAL`, `COST_PRESSURE`, `RUNAWAY`, `QUALITY_DEGRADED`, `PROVIDER_CONSTRAINED`.

### 5.2 Governor Actions (7 Canonical Actions)
`CONTINUE`, `OPTIMIZE`, `ESCALATE`, `DOWNGRADE`, `SWITCH`, `THROTTLE`, `STOP`.

---

## 6. Future HTTP API Integration (Block 05 Reference)

The `ApiDataProvider` will be introduced in **Block 05** implementing the exact same `IDataProvider` interface:
```javascript
// Future Block 05 Implementation Outline (Do NOT implement in Block 04)
export class ApiDataProvider extends IDataProvider {
  constructor(baseUrl = "/v1") {
    super();
    this.baseUrl = baseUrl;
  }
  async getExecutionData(executionId) { /* fetch GET /v1/executions/{id} -> ExecutionBundleViewModel */ }
  async getExecutionHistory(filter) { /* fetch GET /v1/executions -> ExecutionHistoryItemViewModel[] */ }
  async getGovernancePolicy() { /* fetch GET /v1/policies/active -> GovernancePolicyViewModel */ }
  async saveGovernancePolicy(policy) { /* fetch PUT /v1/policies/active -> GovernancePolicyViewModel */ }
}
```
Replacing `MockDataProvider` with `ApiDataProvider` in `InfuseApp` requires zero modifications to UI components or pages.
