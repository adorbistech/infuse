# INFUSE Health Engine Specification

**Milestone:** Block 17 (Health Engine)  
**Status:** Complete / Ready for Freeze  
**Schema Version:** `1.0.0`  

---

## 1. Overview & Purpose

The **INFUSE Health Engine** is a passive observation and deterministic aggregation layer that sits downstream of the Event Bus (Block 14). It consumes canonical lifecycle, provider error, and retry events to produce normalized health facts at the execution, provider, and model levels.

```text
┌────────────────────────────────────────────────────────┐
│               EVENT CONTRACT & EVENT BUS               │
│                        (Block 14)                      │
│  • ExecutionStarted, ExecutionCompleted                │
│  • ExecutionFailed, ProviderError, RetryStarted        │
└───────────────────────────┬────────────────────────────┘
                            │
                      ExecutionEvent
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│               HEALTH ENGINE (Block 17)                 │
│  • Passive Event Consumption & Deduplication           │
│  • Latency Capture (ms) & Outcome Categorization       │
│  • Normalized Error Classification (ErrorCategory)     │
│  • Retry Occurrence Observation (No Execution)         │
│  • Provider & Model Aggregates (Latency, Outcomes)     │
└───────────────────────────┬────────────────────────────┘
                            │
                 ExecutionHealthSummary
                ProviderHealthAggregate
                  ModelHealthAggregate
                            │
                            ▼
          Execution State Engine (Block 20) / Governor (Block 21)
```

> [!IMPORTANT]
> **Core Separation of Responsibilities:**
> - **Health Engine:** *"What health facts are observable about this execution, provider, model, and execution path?"*
> - **Governor:** *"What should INFUSE do about those facts?"*
>
> The Health Engine calculates and aggregates observed facts. It does **NOT** ping or probe providers, route requests, execute retries, switch providers, throttle executions, apply markups, or mutate lifecycle state machines.

---

## 2. Health Observation Semantics

### Execution Outcomes & Latency Capture
* **Execution Outcomes:** Observed directly from canonical lifecycle events:
  - `EXECUTION_COMPLETED` $\to$ `is_success = True`, `is_finalized = True`, `status = "COMPLETED"`.
  - `EXECUTION_FAILED` $\to$ `is_success = False`, `is_finalized = True`, `status = "FAILED"`.
* **Latency:** Captures `duration_ms` from lifecycle completion/failure events. If unobserved, `latency_ms` is preserved as `None` (never silently defaulted to `0.0`).
* **Health Completeness (`HealthCompleteness`):**
  - `COMPLETE`: Both execution outcome, latency, and provider are known.
  - `PARTIAL`: Provider known or execution started, but latency or final outcome incomplete.
  - `UNKNOWN`: Insufficient signals observed.

### Error Classification (`ErrorCategory`)
Normalized into neutral categories:
- `TIMEOUT`: HTTP 408/504 or timeout/deadline keywords.
- `RATE_LIMIT`: HTTP 429 or quota/rate limit keywords.
- `AUTHENTICATION`: HTTP 401/403 or auth/forbidden/credential keywords.
- `UNAVAILABLE`: HTTP 502/503/529 or service overloaded/unavailable keywords.
- `INVALID_REQUEST`: HTTP 400/422 or bad request/validation keywords.
- `PROVIDER_ERROR`: HTTP 500 or upstream provider internal errors.
- `EXECUTION_ERROR`: Internal pipeline or resolution errors.
- `UNKNOWN`: Unclassified errors.

### Retry Observation
* Records retry occurrence, attempt number, and reason from `EventType.RETRY_STARTED`.
* Does **NOT** initiate or execute retries.

### Idempotency & Aggregation Scope
* Deduplicates events per execution using `event_id`.
* Aggregates metrics deterministically across:
  - **Execution level:** [`ExecutionHealthSummary`](file:///Users/ssd/infuse/infuse/health/models.py#L65-L95)
  - **Provider level:** [`ProviderHealthAggregate`](file:///Users/ssd/infuse/infuse/health/models.py#L98-L115) (total, success, failed, error counts, min/max/avg latency)
  - **Model level:** [`ModelHealthAggregate`](file:///Users/ssd/infuse/infuse/health/models.py#L118-L135)

---

## 3. Explicit Non-Responsibilities

| Non-Responsibility | Assigned Boundary |
| :--- | :--- |
| Active health probes, HTTP pings | Probing Adapters (Out of Scope) |
| Provider selection, fallback, routing | Block 11 (Router) |
| Retry orchestration / execution | Execution / Governor Layer |
| Budget enforcement, throttling, stopping | Block 21 (Governor) |
| Lifecycle state machine transitions | Block 13 (Execution Lifecycle) |
| Token counting & token observations | Block 15 (Token Observer) |
| Exact monetary cost calculations | Block 16 (Economics Engine) |
| Database persistence / External brokers | Infrastructure Layer |
