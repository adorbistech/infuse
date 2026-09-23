# INFUSE Execution Lifecycle Specification

**Milestone:** Block 13 (Execution Lifecycle)  
**Status:** Complete / Ready for Freeze  
**Schema Version:** `1.0.0`  

---

## 1. Overview & Purpose

The **Execution Lifecycle Layer** coordinates the end-to-end execution flow of an INFUSE request. It orchestrates the lifecycle phases—from initial request ingestion and context binding, through workload classification, capability resolution, deterministic routing, and provider adapter execution, to normalized result formation and terminal state tracking.

```text
┌────────────────────────────────────────────────────────┐
│                   EXECUTION REQUEST                    │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│          EXECUTION LIFECYCLE SERVICE (Block 13)        │
│  • Context Association (Block 07)                      │
│  • Workload Classification (Block 08)                  │
│  • Capability Resolution (Block 10) vs Registry (09)   │
│  • Deterministic Routing Decision (Block 11)           │
│  • Provider Adapter Invocation (Block 12)              │
│  • Response / Failure Normalization (Block 00 & 12)    │
│  • State Audit Trail & Terminal Record Management      │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│             NORMALIZED EXECUTION RESULT                │
└────────────────────────────────────────────────────────┘
```

> [!IMPORTANT]
> **Core Architectural Guarantee:**  
> **"The Execution Lifecycle Layer coordinates the execution flow across system boundaries. It does NOT make routing decisions, does NOT enforce policies, does NOT make Governor decisions, does NOT perform billing/margin calculations, does NOT score provider health, and does NOT execute retry loops."**

---

## 2. Lifecycle States & Valid Transitions

Every execution is tracked by an [`ExecutionLifecycleRecord`](file:///Users/ssd/infuse/infuse/lifecycle/models.py#L38-L96) with authoritative [`LifecycleState`](file:///Users/ssd/infuse/infuse/lifecycle/models.py#L22-L31) phases:

```text
                     ┌───────────┐
                     │  CREATED  │
                     └─────┬─────┘
                           │
                           ▼
                    ┌──────────────┐
                    │ INITIALIZING │
                    └──────┬───────┘
                           │
                           ▼
                       ┌────────┐
                       │ ROUTED │
                       └───┬────┘
                           │
                           ▼
                       ┌─────────┐
                       │ RUNNING │
                       └───┬─────┘
            ┌──────────────┼──────────────┐
            ▼              ▼              ▼
     ┌───────────┐   ┌──────────┐   ┌───────────┐
     │ COMPLETED │   │  FAILED  │   │ CANCELLED │
     └───────────┘   └──────────┘   └───────────┘
```

### Transition Invariants
* **`CREATED`** → `INITIALIZING`, `CANCELLED`, `FAILED`
* **`INITIALIZING`** → `ROUTED`, `RUNNING`, `CANCELLED`, `FAILED`
* **`ROUTED`** → `RUNNING`, `CANCELLED`, `FAILED`
* **`RUNNING`** → `COMPLETED`, `FAILED`, `CANCELLED`, `TERMINATED`
* **Terminal States (`COMPLETED`, `FAILED`, `CANCELLED`, `TERMINATED`):** Cannot transition further. Attempting to transition from terminal states raises [`InvalidStateTransitionError`](file:///Users/ssd/infuse/infuse/lifecycle/errors.py#L32-L46) or [`ExecutionCancellationError`](file:///Users/ssd/infuse/infuse/lifecycle/errors.py#L49-L57).

---

## 3. Architecture & Service Boundary

* **Interface:** [`IExecutionLifecycleService`](file:///Users/ssd/infuse/infuse/lifecycle/interfaces.py#L42-L86)
* **Implementation:** [`ExecutionLifecycleService`](file:///Users/ssd/infuse/infuse/lifecycle/service.py#L49-L327)
* **Repository Interface:** [`IExecutionLifecycleRepository`](file:///Users/ssd/infuse/infuse/lifecycle/interfaces.py#L10-L39)
* **In-Memory Storage:** [`InMemoryExecutionLifecycleRepository`](file:///Users/ssd/infuse/infuse/lifecycle/repository.py#L44-L138)

---

## 4. Pipeline Execution Sequence

1. **Context Creation:** Calls [`ExecutionContextService.create_context()`](file:///Users/ssd/infuse/infuse/context/service.py#L18-L31) to establish canonical context identity and parameters.
2. **Lifecycle Initial Record:** Creates record in `CREATED` state with unique `execution_id`, `request_id`, `task_id`.
3. **Transition to `INITIALIZING`:** Audit trail records phase change.
4. **Workload Classification:** Invokes [`WorkloadClassificationService.classify()`](file:///Users/ssd/infuse/infuse/classifier/service.py#L27-L29).
5. **Capability Resolution:** Invokes [`CapabilityResolverService.resolve()`](file:///Users/ssd/infuse/infuse/resolver/service.py#L25-L38) against [`IProviderModelRegistry`](file:///Users/ssd/infuse/infuse/registry/interfaces.py).
   - If no compatible targets exist, transitions directly to `FAILED` with normalized `RESOLUTION_ERROR`.
6. **Deterministic Routing:** Invokes [`RouterService.route()`](file:///Users/ssd/infuse/infuse/router/service.py#L19-L32) to select [`RouteTarget`](file:///Users/ssd/infuse/infuse/router/models.py#L30-L48). Transitions to `ROUTED`.
7. **Transition to `RUNNING`:** Measures execution timestamp.
8. **Provider Invocation:** Dispatches to [`ProviderAdapterService.execute_target()`](file:///Users/ssd/infuse/infuse/providers/service.py#L82-L100).
9. **Outcome Handling:**
   - **Success:** Normalizes to [`ExecutionResult`](file:///Users/ssd/infuse/infuse/contracts/execution.py#L227-L257) with complete token usage and latency. Transitions to `COMPLETED`.
   - **Failure:** Captures provider errors, normalizes via `normalize_error()`, sets `status=ExecutionStatus.FAILED`, preserves retryability metadata, and transitions to `FAILED`. No silent fallbacks or retries are executed.

---

## 5. Cancellation & Control Boundary

* Non-terminal executions can be cancelled via [`cancel_execution(execution_id, reason)`](file:///Users/ssd/infuse/infuse/lifecycle/service.py#L286-L327).
* Transition to `CANCELLED` records reason and sets normalized `ExecutionResult` with `status=ExecutionStatus.STOPPED`.
* Terminal executions reject cancellation deterministically.

---

## 6. Preparation for Downstream Blocks

* **Block 14 (Event Contract & Bus):** Lifecycle transitions provide clean hooks for `ExecutionStarted`, `ExecutionCompleted`, and `ExecutionFailed` events.
* **Block 15 (Token Observer):** Complete token telemetry is preserved on the normalized `ExecutionResult`.
* **Block 20 & 21 (Execution State Engine & Governor):** Lifecycle state is clearly separated from operational execution health states (`NORMAL`, `COST_PRESSURE`, `RUNAWAY`, `PROVIDER_CONSTRAINED`).
