# INFUSE Token Observer Specification

**Milestone:** Block 15 (Token Observer)  
**Status:** Complete / Ready for Freeze  
**Schema Version:** `1.0.0`  

---

## 1. Overview & Purpose

The **INFUSE Token Observer** sits downstream of the Block 14 Event Bus to consume canonical execution and token events and produce a normalized, deterministic execution-level token observation view.

```text
┌────────────────────────────────────────────────────────┐
│             EXECUTION LIFECYCLE (Block 13)             │
└───────────────────────────┬────────────────────────────┘
                            │
              publishes ExecutionEvents
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│          EVENT CONTRACT & EVENT BUS (Block 14)         │
│  • TokenObserved                                       │
│  • UsageUpdated                                        │
│  • ExecutionCompleted                                  │
│  • ExecutionFailed                                     │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│               TOKEN OBSERVER (Block 15)                │
│  • Normalized Token Usage Aggregation                  │
│  • Authoritative vs Estimated Distinction              │
│  • Missing Data / Explicit Absence Invariants          │
│  • Thread-Safe & Idempotent In-Memory Store            │
└───────────────────────────┬────────────────────────────┘
                            │
             Normalized Token Observations
                            │
           ┌────────────────┴────────────────┐
           ▼                                 ▼
   Economics Engine                 Execution State Engine
      (Block 16)                          (Block 20)
```

> [!IMPORTANT]
> **Core Architectural Principle:**  
> **"OBSERVE $\to$ NORMALIZE $\to$ AGGREGATE $\to$ EXPOSE"**  
> The Token Observer observes and normalizes execution usage facts. It does NOT price, bill, route, govern, retry, throttle, mutate lifecycle states, score health, or detect anomalies.

---

## 2. Token Observation Semantics

### Authoritative vs Derived Data
* **`PROVIDER_USAGE` / `LIFECYCLE_EVENT`:** When usage numbers are supplied directly in an authoritative provider response (`is_authoritative=True`), `ExecutionCompleted`, or authoritative `UsageUpdated`, they are marked authoritative.
* **`STREAM_ESTIMATE`:** Incremental streaming chunks report estimates (`is_authoritative=False`).
* **Supersession Invariant:** Once an authoritative usage observation is recorded, subsequent or delayed stream estimates do not overwrite the authoritative summary counts.
* **Derived Total:** When `total_tokens` is absent or 0, it is derived as `input_tokens + output_tokens` only if the component dimensions are present.

### Missing Data Invariants
* The observer does **not** fabricate `0` for unobserved dimensions.
* Missing fields remain explicit `None` unless a zero count was explicitly reported.

### Aggregation & Idempotency
* **Deduplication:** Tracks seen `event_id`s per `execution_id`. Replaying identical events is safely idempotent and does not double-count usage.
* **Audit History:** Each distinct event is preserved in `ExecutionTokenSummary.history` as a [`TokenObservationRecord`](file:///Users/ssd/infuse/infuse/observer/models.py#L22-L41).
* **Finalization:**
  - `ExecutionCompleted` sets `is_finalized=True`, `final_status="COMPLETED"`, and finalizes authoritative counts.
  - `ExecutionFailed` sets `is_finalized=True`, `final_status="FAILED"`, without inventing missing usage data.

---

## 3. Event Bus Integration

The Token Observer implements [`ITokenObserver`](file:///Users/ssd/infuse/infuse/observer/interfaces.py#L10-L45) and seamlessly attaches to the Block 14 [`IEventBus`](file:///Users/ssd/infuse/infuse/events/interfaces.py#L10-L64):

```python
from infuse.events.bus import InMemoryEventBus
from infuse.observer.observer import TokenObserver

bus = InMemoryEventBus()
observer = TokenObserver()
subscription_ids = observer.attach_to_bus(bus)
```

Subscriptions include:
* `EventType.EXECUTION_STARTED`
* `EventType.TOKEN_OBSERVED`
* `EventType.USAGE_UPDATED`
* `EventType.EXECUTION_COMPLETED`
* `EventType.EXECUTION_FAILED`

---

## 4. Explicit Non-Responsibilities

| Non-Responsibility | Assigned Block / Domain |
| :--- | :--- |
| Cost calculation, provider pricing, margins | Block 16 (Economics Engine) |
| Token limits, budget enforcement, throttling | Block 21 (Governor) |
| Target selection, routing, fallback | Block 11 (Router) |
| Lifecycle transition coordination | Block 13 (Execution Lifecycle) |
| Provider health scoring | Block 17 (Health Engine) |
| Runaway loop / anomaly detection | Block 19 (Anomaly Detector) |
| Provider SDK interaction | Block 12 (Provider Adapter Layer) |
| Database persistence | Persistence Layer (Future) |
