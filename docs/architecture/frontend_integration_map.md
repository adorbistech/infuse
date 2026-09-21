# INFUSE Frontend Architecture & Backend Integration Map

**Milestone:** Block 02 (Frontend Information / Execution Surface Hardening)  
**Status:** Frozen  
**Visual Baseline:** Stitch Console (`Autonomous Governance Obsidian` Theme)  
**Contract Baseline:** Block 00 Universal Contracts (`infuse.contracts.frontend`)  

---

## 1. Overview

The INFUSE Execution / Information surface provides a comprehensive, glass-box operational telemetry view of real-time autonomous AI agent execution.

Every displayed field, metric, status pill, chart, and timeline event is strictly mapped to normalized `ViewModels` delivered through the [`IDataProvider`](file:///Users/ssd/infuse/frontend/src/data/IDataProvider.js) interface, completely decoupled from database schemas and backend execution logic.

```text
┌────────────────────────────────────────────────────────┐
│               INFUSE FRONTEND CONSOLE                  │
│                                                        │
│  [Execution / Information Surface]                     │
│  ├── Execution Context & Switcher                      │
│  ├── Dedicated Execution State (5 States)              │
│  ├── 8-Card Metrics Grid (Tabular-nums)                │
│  ├── SVG Token Growth & Cost Time-Series               │
│  ├── Web, Tool, File & Retry Activity                  │
│  ├── Central Governor Action Banner (7 Actions)        │
│  ├── Provider & Model Health                           │
│  ├── Traceable Event Timeline                          │
│  ├── Runtime Engine Signal Inspector (4 Engines)       │
│  └── Filterable Execution History                      │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
               IDataProvider Interface
                           │
          ┌────────────────┴────────────────┐
          ▼                                 ▼
   MockDataProvider                 ApiDataProvider
   (Active in Blocks 01-02)         (Future Block 05)
                                            │
                                            ▼
                                   Universal HTTP API
                                   (/v1/executions, /v1/policies)
```

---

## 2. Execution Surface Component-to-Backend Integration Map

| # | Execution Section | Component | Frontend ViewModel | Future Backend Origin | API Route |
|---|---|---|---|---|---|
| **1** | **Execution Context Header** | [`ExecutionHeader.js`](file:///Users/ssd/infuse/frontend/src/components/ExecutionHeader.js) | `ExecutionSummaryViewModel` | Execution API & Lifecycle | `GET /v1/executions/{id}` |
| **2** | **Execution State** | [`StateSelector.js`](file:///Users/ssd/infuse/frontend/src/components/StateSelector.js) | `ExecutionStateViewModel` | Execution State Engine | `GET /v1/executions/{id}` |
| **3** | **Execution Metrics (8 Cards)** | [`MetricsGrid.js`](file:///Users/ssd/infuse/frontend/src/components/MetricsGrid.js) | `ExecutionMetricsViewModel` | Token Observer & Economics | `GET /v1/executions/{id}` |
| **4** | **Token Growth Time-Series** | [`Charts.js`](file:///Users/ssd/infuse/frontend/src/components/Charts.js) | `ExecutionMetricsViewModel` | Token Observer Stream | `GET /v1/executions/{id}` |
| **5** | **Cost Over Time Chart** | [`Charts.js`](file:///Users/ssd/infuse/frontend/src/components/Charts.js) | `ExecutionMetricsViewModel` | Economics Engine Stream | `GET /v1/executions/{id}` |
| **6** | **Execution Activity** | [`ActivityPanel.js`](file:///Users/ssd/infuse/frontend/src/components/ActivityPanel.js) | `ExecutionMetricsViewModel` | Tool & Web Observers | `GET /v1/executions/{id}` |
| **7** | **Governor Action Banner** | [`GovernorPanel.js`](file:///Users/ssd/infuse/frontend/src/components/GovernorPanel.js) | `GovernorDecisionViewModel` | Central Governor | `GET /v1/executions/{id}` |
| **8** | **Provider / Model Health** | [`HealthPanel.js`](file:///Users/ssd/infuse/frontend/src/components/HealthPanel.js) | `ProviderModelHealthViewModel`| Health Engine | `GET /v1/executions/{id}` |
| **9** | **Chronological Event Timeline**| [`Timeline.js`](file:///Users/ssd/infuse/frontend/src/components/Timeline.js) | `ExecutionTimelineEventViewModel`| Event Bus & Ledger | `GET /v1/executions/{id}/events` |
| **10**| **Runtime Engine Inspector** | [`RuntimeEngines.js`](file:///Users/ssd/infuse/frontend/src/components/RuntimeEngines.js)| `ExecutionMetricsViewModel` | Real-time Engine Observers | `GET /v1/executions/{id}` |
| **11**| **Execution History Table** | [`HistoryTable.js`](file:///Users/ssd/infuse/frontend/src/components/HistoryTable.js) | `ExecutionHistoryItemViewModel`| Execution History Store | `GET /v1/executions` |

---

## 3. Canonical States & Governor Actions Supported

### 3.1 Execution States
1. `NORMAL`: Standard operation within policy parameters.
2. `COST_PRESSURE`: Cost approaching budget pacing boundary (automated optimization engaged).
3. `RUNAWAY`: Recursive loop or anomalous token surge detected (circuit breaker halt).
4. `QUALITY_DEGRADED`: Output drift or schema validation failures (model tier escalation).
5. `PROVIDER_CONSTRAINED`: Provider rate limits (HTTP 429) or high latency (dynamic route switching).

### 3.2 Governor Actions
1. `CONTINUE`: Standard unthrottled execution.
2. `OPTIMIZE`: Context compression & semantic caching.
3. `ESCALATE`: Model tier elevation.
4. `DOWNGRADE`: Route to lower-cost tier for subsequent steps.
5. `SWITCH`: Failover to backup provider.
6. `THROTTLE`: Rate-limit request pacing.
7. `STOP`: Hard circuit-breaker termination.

---

## 4. Multi-Agent History Database in Mock Layer

The mock layer provides multi-agent historical telemetry covering:
* **Agents:** `OpenCode`, `Claude Code`, `Codex`, `Hermes`, `OpenClaw`, `Lovable`.
* **Providers:** `Anthropic`, `OpenAI`, `Google Gemini`, `DeepSeek`.
* **Multi-filter capabilities:** Client-side real-time text query, state filtering, and agent filtering with instant view switching.
