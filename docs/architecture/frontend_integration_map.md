# INFUSE Frontend Architecture & Backend Integration Map

**Milestone:** Block 01 (Frontend Foundation & Integration)  
**Status:** Complete  
**Visual Baseline:** Stitch Console (`Autonomous Governance Obsidian` Theme)  
**Contract Baseline:** Block 00 Universal Contracts (`infuse.contracts.frontend`)  

---

## 1. Overview

The INFUSE Frontend is structured as an architectural **integration map**. Every displayed field, badge, chart, and button is bound to a normalized `ViewModel` that maps directly to a future backend engine and REST API endpoint.

```text
┌────────────────────────────────────────────────────────┐
│               INFUSE FRONTEND CONSOLE                  │
│                                                        │
│  [Execution View]                  [Governance View]   │
│         │                                  │           │
│         ▼                                  ▼           │
│  Execution ViewModels             Governance ViewModels│
│  (Summary, Metrics, State,        (Policy, Bindings,   │
│   Governor, Health, Timeline)      Strictness Index)   │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
               IDataProvider Interface
                           │
          ┌────────────────┴────────────────┐
          ▼                                 ▼
   MockDataProvider                 ApiDataProvider
   (Active in Block 01)            (Future Block 05)
                                            │
                                            ▼
                                   Universal HTTP API
                                   (/v1/executions, /v1/policies)
```

---

## 2. Component-to-Backend Integration Mapping

| UI Section / Field | Component | Frontend ViewModel | Future Backend Origin | API Endpoint |
|---|---|---|---|---|
| **Execution Context Header** | `ExecutionHeader.js` | `ExecutionSummaryViewModel` | Execution API & Lifecycle | `GET /v1/executions/{id}` |
| **Active Agent & Pool** | `ExecutionHeader.js` | `ExecutionSummaryViewModel` | Agent Adapter / Context | `GET /v1/executions/{id}` |
| **Execution State Badge & Pills** | `StateSelector.js` | `ExecutionStateViewModel` | Execution State Engine | `GET /v1/executions/{id}` |
| **Input / Cached / Output Tokens** | `MetricsGrid.js` | `ExecutionMetricsViewModel` | Token Observer | `GET /v1/executions/{id}` |
| **Cost & Budget %** | `MetricsGrid.js` | `ExecutionMetricsViewModel` | Economics Engine | `GET /v1/executions/{id}` |
| **RPM & Request Count** | `MetricsGrid.js` | `ExecutionMetricsViewModel` | API Gateway Rate Limiter | `GET /v1/executions/{id}` |
| **Token Growth Chart** | `Charts.js` | `ExecutionMetricsViewModel` | Token Observer Stream | `GET /v1/executions/{id}` |
| **Cost Over Time Chart** | `Charts.js` | `ExecutionMetricsViewModel` | Economics Engine Stream | `GET /v1/executions/{id}` |
| **Web & Tool Activity** | `ActivityPanel.js` | `ExecutionMetricsViewModel` | Tool & Web Observers | `GET /v1/executions/{id}` |
| **Governor Regulation Banner** | `GovernorPanel.js` | `GovernorDecisionViewModel` | Central Governor | `GET /v1/executions/{id}` |
| **Decision Rationale & History** | `GovernorPanel.js` | `GovernorDecisionViewModel` | Governor Audit Trail | `GET /v1/executions/{id}` |
| **Provider Latency & Availability** | `HealthPanel.js` | `ProviderModelHealthViewModel`| Health Engine | `GET /v1/executions/{id}` |
| **Chronological Event Stream** | `Timeline.js` | `ExecutionTimelineEventViewModel`| Event Bus & Ledger | `GET /v1/executions/{id}/events` |
| **Signal Inspector Tabs** | `RuntimeEngines.js`| `ExecutionMetricsViewModel` | Real-time Engine Observers | `GET /v1/executions/{id}` |
| **Historical Execution Runs** | `HistoryTable.js` | `ExecutionHistoryItemViewModel`| Execution History Store | `GET /v1/executions` |
| **10-Section Governance Policy** | `PolicyForm.js` | `GovernancePolicyViewModel` | Policy Manager | `GET /v1/policies/{id}` |
| **Policy Save / Update** | `PolicyForm.js` | `GovernancePolicyViewModel` | Policy Manager API | `PUT /v1/policies/{id}` |

---

## 3. Frontend Architecture Directory Structure

```text
frontend/
├── index.html                  # Single-Page Application HTML host
├── package.json                # Test and start configuration
├── src/
│   ├── app.js                  # Application root & event delegation
│   ├── contracts/
│   │   └── viewmodels.js       # Language-neutral JavaScript ViewModels
│   ├── data/
│   │   ├── IDataProvider.js    # Data provider interface abstraction
│   │   └── MockDataProvider.js # Synthetic data across 5 execution states
│   ├── state/
│   │   └── store.js            # Central reactive state manager
│   ├── components/
│   │   ├── Header.js
│   │   ├── ExecutionHeader.js
│   │   ├── StateSelector.js
│   │   ├── MetricsGrid.js
│   │   ├── Charts.js
│   │   ├── ActivityPanel.js
│   │   ├── GovernorPanel.js
│   │   ├── HealthPanel.js
│   │   ├── Timeline.js
│   │   ├── RuntimeEngines.js
│   │   ├── HistoryTable.js
│   │   └── PolicyForm.js
│   ├── pages/
│   │   ├── ExecutionPage.js    # Execution / Information surface
│   │   └── GovernancePage.js   # Governance / Policy surface
│   └── styles/
│       └── theme.css           # Obsidian dark theme and typography
└── tests/
    ├── viewmodels.test.js      # ViewModel contract validations
    ├── dataprovider.test.js    # Mock provider state generation tests
    ├── store.test.js           # Reactive store tests
    ├── components.test.js      # Component markup & accessibility tests
    └── integration.test.js     # Full simulated workflow lifecycle tests
```

---

## 4. Theme & Accessibility

* **Design System:** Obsidian (`#101419` surface, `#adc6ff` cobalt accent, `#1c2025` container).
* **Typography:** `Hanken Grotesk` for headers/titles; `Geist` for body, tabular telemetry numbers, and code tokens.
* **Accessibility:** All actionable buttons and inputs feature semantic ARIA labels, keyboard focus indicators, and non-color-only state badges.
* **Responsiveness:** Fluid 12-column desktop layout collapsing to 4-column priority cards on mobile viewports.
