# INFUSE Universal Contracts Specification

**Version:** 1.0.0  
**Status:** Frozen (Block 00 Baseline)  
**Canonical Repository:** `https://github.com/adorbistech/infuse`  
**License:** Apache-2.0  

---

## 1. Executive Summary

This document specifies the formal, language-neutral data contracts governing INFUSE (Execution Intelligence).

INFUSE operates as an independent voltage regulator for autonomous AI agents. To ensure that future subsystems, agent adapters, provider substrates, SDKs, CLIs, and frontends can be developed by independent engineering agents without architectural drift, all communication is mediated by these contracts.

---

## 2. Core Architectural Principles

1. **No Hard-Coding:** No business pricing, provider margins, customer governance thresholds, or execution limits are hard-coded into contract definitions. All limits are configured through data (`GovernancePolicy`).
2. **One Core, Many Adapters:** Adapters translate agent-specific and provider-specific protocols into the universal contract; the core operates exclusively on normalized models.
3. **Governor is the Sole Control Authority:** Observers emit measurement signals; the Governor evaluates policy and state to emit control decisions.
4. **Execution Control Boundary Separation:** The system discovers physical agent capabilities (`supports_cancel`, `supports_throttle`, `supports_next_step_switch`, `supports_terminate`) before dispatching control actions.
5. **Additive Evolution:** All schemas inherit from `InfuseBaseModel` which preserves unrecognized extra fields, enabling backward and forward compatibility across version upgrades.

---

## 3. Contract Taxonomy & Responsibility Matrix

| Contract | Module | Primary Owner | Receives | Emits / Represents |
|---|---|---|---|---|
| **Universal Execution** | `infuse.contracts.execution` | API Gateway & Router | Raw caller request | `ExecutionRequest`, `ExecutionResult` |
| **Execution Events** | `infuse.contracts.events` | Event Bus | Execution telemetry | `ExecutionEvent` (Immutable stream) |
| **Governance Policy** | `infuse.contracts.policy` | Policy Manager | UI / API settings | `GovernancePolicy` (Active constraints) |
| **Execution Control Boundary** | `infuse.contracts.control` | Control Boundary | Governor decision | `ControlOperation`, `ControlResult` |
| **Governor Action** | `infuse.contracts.governor` | Governor | Policy + State | `GovernorAction`, `GovernorDecision` |
| **Execution State** | `infuse.contracts.state` | State Engine | Aggregated signals | `ExecutionStateSnapshot` |
| **Frontend ViewModel** | `infuse.contracts.frontend` | API to Frontend | State & Metrics | ViewModels for Stitch Console |
| **Adapter Capability** | `infuse.contracts.capabilities` | Adapter Registry | Adapter manifests | `AdapterRegistration` |

---

## 4. Contract Specifications

### 4.1 Universal Execution Contract (`infuse.contracts.execution`)
* **Purpose:** Normalizes incoming execution requests and outgoing execution results across all callers (CLI, SDK, Web UI, MCP).
* **Key Types:**
  * `ExecutionRequest`: Envelope containing `task` (`TaskContext`), `request` (`OperationRequest`), `requirements` (`ExecutionRequirements`), optional `policy` (`GovernancePolicy`), and `execution_context` (`ExecutionContext`).
  * `ExecutionResult`: Envelope returning `execution_id`, `status` (`ExecutionStatus`), normalized `response` (`NormalizedResponse`), comprehensive `execution` telemetry (`ExecutionTelemetry`), and final `decision` (`GovernorDecision`).
* **Extension Rules:** Provider-specific metadata must be placed inside `metadata` or `extensions` bags, never as top-level required fields.

### 4.2 Execution Event Contract (`infuse.contracts.events`)
* **Purpose:** Immutable observation backbone capturing discrete execution occurrences.
* **Envelope:**
  ```json
  {
    "event_id": "evt_01J8K7...",
    "execution_id": "exec_01J8K7...",
    "timestamp": "2026-09-21T16:50:00Z",
    "type": "TokenObserved",
    "source": "PROVIDER",
    "sequence": 1,
    "payload": {},
    "schema_version": "1.0.0"
  }
  ```
* **Canonical Event Types:**
  * `ExecutionStarted`, `ExecutionCompleted`, `ExecutionFailed`
  * `TokenObserved` (Streaming vs. Authoritative usage)
  * `UsageUpdated` (Reconciled billing usage)
  * `ToolCalled`, `ToolCompleted`
  * `WebRequest`, `WebResponse`
  * `RetryStarted`, `ProviderError`
  * `StateChanged` (State transitions)
  * `GovernorDecision`, `ControlActionIssued`

### 4.3 Policy / Governance Contract (`infuse.contracts.policy`)
* **Purpose:** Defines the user-configured execution boundary and limit action bindings.
* **Sections:**
  * `budget`: `max_cost_per_task`, `max_cost_per_day`, `max_cost_per_month`.
  * `tokens`: `max_input_tokens`, `max_output_tokens`, `max_total_tokens`.
  * `requests`: `max_rpm`, `max_requests_per_task`.
  * `runtime`: `max_execution_time_seconds`.
  * `providers`: `allowed_providers`, `allowed_models`, `blocked_providers`, `blocked_models`.
  * `web` & `tools`: Allow/block rules and frequency limits.
  * `retries` & `anomaly`: Retry backoffs, runaway surge limits, circuit breaker toggle.
  * `actions`: `budget_action`, `token_action`, `request_action`, `runtime_action`, `provider_failure_action`, `anomaly_action`.

### 4.4 Execution Control Boundary Contract (`infuse.contracts.control`)
* **Purpose:** Safely negotiates and dispatches physical control operations to agent runtimes.
* **Capability Discovery:**
  * `supports_cancel`: Graceful cancellation.
  * `supports_throttle`: Rate delay insertion.
  * `supports_next_step_switch`: Step-boundary provider/model rerouting.
  * `supports_terminate`: Fallback process termination.
* **Outcomes:** `ACCEPTED`, `COMPLETED`, `SUPPORTED`, `UNSUPPORTED`, `FAILED`. Unsupported actions fail safely with clear audit logs.

### 4.5 Governor Action Contract (`infuse.contracts.governor`)
* **Canonical Action Vocabulary:**
  * `CONTINUE`: Execution proceeds normally.
  * `OPTIMIZE`: Engage context compression, prompt compaction, or semantic caching.
  * `ESCALATE`: Elevate capability/model tier for complex workloads.
  * `DOWNGRADE`: Switch to lower-cost model at next workflow boundary.
  * `SWITCH`: Route to fallback or alternative provider due to error or policy.
  * `THROTTLE`: Inject delay to manage RPM/TPM pressure.
  * `STOP`: Trigger circuit-breaker halt and cancel execution.

### 4.6 Execution State Contract (`infuse.contracts.state`)
* **Canonical Internal States:**
  * `NORMAL`: Within standard policy and health parameters.
  * `COST_PRESSURE`: Cost approaching configured policy boundaries.
  * `RUNAWAY`: Anomalous token velocity, repetitive tool loops, or infinite retries.
  * `QUALITY_DEGRADED`: Provider responses failing validation or semantic quality checks.
  * `PROVIDER_CONSTRAINED`: Provider rate-limited, high latency, or returning transient 5xx errors.
* **Action UI States:** `OPTIMIZED`, `THROTTLED`, `SWITCHED`, `STOPPED`.

### 4.7 Frontend ViewModel Contract (`infuse.contracts.frontend`)
* **Purpose:** Decouples the Stitch UI console from backend databases and runtime objects.
* **Key ViewModels:**
  * `ExecutionSummaryViewModel` (Header card & live runtime)
  * `ExecutionMetricsViewModel` (8-metric grid & time-series chart arrays)
  * `ExecutionStateViewModel` (State badge & pill selector)
  * `GovernorDecisionViewModel` (Regulation banner & callout)
  * `ProviderModelHealthViewModel` (Health metrics)
  * `ExecutionTimelineEventViewModel` (Timeline items)
  * `ExecutionHistoryItemViewModel` (History table rows)
  * `GovernancePolicyViewModel` (Policy settings form)

### 4.8 Adapter Capability Contract (`infuse.contracts.capabilities`)
* **Purpose:** Adapter registration interface for agents (e.g. Claude Code, OpenCode, Codex), providers (e.g. OpenAI, Anthropic, Gemini, DeepSeek), SDKs, and MCP.
* **Rule:** The INFUSE core remains completely generic; adapters declare their supported protocols, models, and control hooks.

---

## 5. Versioning & Evolution Rules

1. **Semantic Versioning:** All contracts declare `schema_version` (starting at `1.0.0`).
2. **Additive Changes Only:** New fields added to contracts must be optional or have default values.
3. **Extra Field Preservation:** Models do not discard unrecognized fields during JSON serialization / deserialization.
4. **Breaking Changes:** Any breaking modification (renaming a required field or deleting an enum) requires incrementing the major schema version and maintaining adapter translation bridges.

---

## 6. Prohibited Content in Contracts

The following MUST NEVER be added to contracts:
* Hard-coded customer pricing or profit margins.
* Hard-coded vendor API keys, URLs, or authorization tokens.
* Agent reasoning algorithms or execution loops.
* Database ORM objects or SQL queries.
* Framework-specific UI presentation code.
