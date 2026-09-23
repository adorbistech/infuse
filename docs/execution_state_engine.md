# INFUSE Execution State Engine Specification

**Milestone:** Block 20 (Execution State Engine)  
**Status:** Complete / Ready for Freeze  
**Schema Version:** `1.0.0`  

---

## 1. Overview & Purpose

The **INFUSE Execution State Engine** is the central state derivation and normalization authority sitting directly between the independent observation layer (Blocks 15–19) and the Governor (Block 21).

```text
┌──────────────────────────────┐
│  TOKEN OBSERVER (Block 15)   │ ExecutionTokenSummary
├──────────────────────────────┤
│  ECONOMICS ENGINE (Block 16) │ ExecutionEconomicSummary
├──────────────────────────────┤
│  HEALTH ENGINE (Block 17)    │ ExecutionHealthSummary
├──────────────────────────────┤
│  TOOL OBSERVER (Block 18)    │ ExecutionToolSummary
├──────────────────────────────┤
│  WEB OBSERVER (Block 19)     │ ExecutionWebSummary
└──────────────┬───────────────┘
               │ Normalized Observations
               ▼
┌────────────────────────────────────────────────────────┐
│         EXECUTION STATE ENGINE (Block 20)              │
│  • Evidence Aggregation & Partial Observation Handling │
│  • Policy Threshold Evaluation (Budget, Tokens, etc.)  │
│  • Deterministic Precedence Resolution                 │
│  • Execution State Transition Tracking                 │
│  • Thread-safe In-memory Cache & Snapshots             │
└──────────────────────────┬────────────────────────────┘
                           │
                 ExecutionStateSnapshot
                           │
                           ▼
                  GOVERNOR (Block 21)
```

> [!IMPORTANT]
> **Core Architectural Separation:**
> - **Execution State Engine:** *"What is the current health and behavioral state of this execution given observed facts and policy bounds?"*
> - **Governor:** *"What control action (OPTIMIZE, THROTTLE, SWITCH, STOP) should be taken in response to this state?"*
>
> The Execution State Engine derives state deterministically from evidence. It does **NOT** issue control actions, perform provider routing, trigger retries, mutate execution lifecycle state, or make external network calls.

---

## 2. Canonical Execution States & Precedence

The Execution State Engine derives the 5 canonical states defined by Block 00 architecture:

| State | Deterministic Evidence Required | Reason Codes |
| :--- | :--- | :--- |
| **`RUNAWAY`** | Tool calls exceed `max_tool_calls_per_task`, consecutive tool failures exceed `max_consecutive_tool_failures`, web requests exceed `max_web_requests_per_task`, execution duration exceeds `max_execution_time_seconds`, or repetitive loops detected. | `MAX_TOOL_CALLS_EXCEEDED`, `CONSECUTIVE_TOOL_FAILURES_EXCEEDED`, `MAX_WEB_REQUESTS_EXCEEDED`, `EXECUTION_TIME_EXCEEDED`, `REPETITIVE_LOOP_DETECTED` |
| **`PROVIDER_CONSTRAINED`** | Health summary contains provider error categories: `RATE_LIMIT` (429), `UNAVAILABLE` (503), `AUTHENTICATION` (401/403), `TIMEOUT` (504), or `PROVIDER_ERROR`. | `PROVIDER_RATE_LIMIT`, `PROVIDER_UNAVAILABLE`, `PROVIDER_AUTH_FAILURE`, `PROVIDER_TIMEOUT`, `PROVIDER_ERROR` |
| **`QUALITY_DEGRADED`** | Execution failed (`is_success is False` / `status == "FAILED"` without provider outage), all tool calls failed, or all web requests failed. | `EXECUTION_FAILURE`, `ALL_TOOL_CALLS_FAILED`, `ALL_WEB_REQUESTS_FAILED` |
| **`COST_PRESSURE`** | Economic cost exceeds `max_cost_per_task` (or $\ge 80\%$ budget), or token usage exceeds `max_total_tokens` (or $\ge 80\%$ ceiling). | `BUDGET_EXCEEDED`, `COST_PRESSURE_HIGH`, `TOKEN_CEILING_EXCEEDED`, `TOKEN_PRESSURE_HIGH` |
| **`NORMAL`** | Available evidence satisfies normal execution conditions without triggering anomalous/constrained/pressure signals. | `NORMAL_EXECUTION` |

### Deterministic Precedence Ranking
When multiple signals trigger concurrently, the canonical `current_state` is resolved using the exact deterministic severity hierarchy:
$$\text{RUNAWAY} > \text{PROVIDER\_CONSTRAINED} > \text{QUALITY\_DEGRADED} > \text{COST\_PRESSURE} > \text{NORMAL}$$

All triggered signal flags and reason codes are retained in `signals` and `reason_codes` within the `ExecutionStateSnapshot` to ensure complete observability for the Governor.

---

## 3. Partial Observability & Unknown Semantics

The Execution State Engine strictly distinguishes between:
* **`None` / Unobserved** $\neq$ Zero / False / Healthy
* **Missing Token Data** $\neq$ 0 tokens (does not trigger false token pressure)
* **Missing Cost Data** $\neq$ \$0.00 cost (does not trigger false budget pressure)
* **In-Flight Tools / Web Requests** $\neq$ Failed operations (does not trigger false degradation)
* **Absent Policy Limit** $\implies$ Unbounded dimension (remains NORMAL without arbitrary constants)

---

## 4. Explicit Non-Responsibilities

| Non-Responsibility | Assigned Boundary |
| :--- | :--- |
| Control actions (OPTIMIZE, THROTTLE, SWITCH, STOP) | Block 21 (Governor) |
| Provider routing and capability selection | Block 10 & 11 (Resolver / Router) |
| Retry execution and provider fallback | Block 12 & 13 (Adapter / Lifecycle) |
| Execution lifecycle mutation (CREATED, RUNNING, etc.) | Block 13 (Lifecycle) |
| Raw token estimation & counting | Block 15 (Token Observer) |
| Pricing calculations & currency conversions | Block 16 (Economics Engine) |
| Error taxonomy classification & error tracking | Block 17 (Health Engine) |
| Tool invocation execution & correlation | Block 18 (Tool Activity Observer) |
| Web request execution & correlation | Block 19 (Web Activity Observer) |
| Database persistence / external brokers | Infrastructure Layer |
