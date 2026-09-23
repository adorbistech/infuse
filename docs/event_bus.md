# INFUSE Event Contract & Event Bus Specification

**Milestone:** Block 14 (Event Contract & Event Bus)  
**Status:** Complete / Ready for Freeze  
**Schema Version:** `1.0.0`  

---

## 1. Overview & Purpose

The **INFUSE Event Bus** establishes the canonical, in-process event transport boundary between the execution lifecycle and downstream observation engines (Token Observer, Economics Engine, Health Engine, Tool/Web Observers, and Anomaly Detectors).

```text
┌────────────────────────────────────────────────────────┐
│             EXECUTION LIFECYCLE (Block 13)             │
└───────────────────────────┬────────────────────────────┘
                            │
              publishes ExecutionEvent
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│          EVENT CONTRACT & EVENT BUS (Block 14)         │
│  • Canonical Event Validation                          │
│  • Idempotency & Conflict Detection                    │
│  • In-Process Synchronous Delivery                     │
│  • Subscriber Isolation & Error Boundary               │
└─────────────┬─────────────┬─────────────┬──────────────┘
              │             │             │
              ▼             ▼             ▼
      ┌──────────────┐┌───────────┐┌──────────────┐
      │Token Observer││ Economics ││Health Engine │ ... (Blocks 15-19)
      │  (Block 15)  ││ (Block 16)││  (Block 17)  │
      └──────────────┘└───────────┘└──────────────┘
```

> [!IMPORTANT]
> **Core Architectural Guarantee:**  
> **"The Event Bus transports and distributes normalized execution facts. It does NOT persist events to databases, does NOT make routing decisions, does NOT evaluate Governor policies, does NOT calculate prices/margins, does NOT score provider health, and does NOT execute retries."**

---

## 2. Canonical Event Envelope (Frozen Block 00)

Every event traveling across the INFUSE Event Bus adheres to the frozen Block 00 [`ExecutionEvent`](file:///Users/ssd/infuse/infuse/contracts/events.py#L105-L136) envelope:

| Field | Type | Description |
| :--- | :--- | :--- |
| `event_id` | `str` | Globally unique identifier for this event. |
| `execution_id` | `str` | Associated execution identifier. |
| `timestamp` | `datetime` | UTC timestamp when the event occurred. |
| `type` | `EventType` | Canonical event type. |
| `source` | `EventSource` | Originating subsystem (`SYSTEM`, `AGENT`, `PROVIDER`, `RUNTIME`, `GOVERNOR`, `OBSERVER`). |
| `sequence` | `int` | Monotonically non-decreasing sequence number ($\ge 0$) within the execution. |
| `payload` | `Dict[str, Any]` | Typed payload data dictionary. |
| `schema_version`| `str` | Contract schema version (`"1.0.0"`). |

---

## 3. Canonical Event Taxonomy

The Event Bus supports all 14 canonical event types defined in Block 00:

1. **`ExecutionStarted`** — Lifecycle execution initialization and target selection.
2. **`ExecutionCompleted`** — Successful completion of provider execution with token usage and latency.
3. **`ExecutionFailed`** — Normalized execution failure with error record and retryability metadata.
4. **`TokenObserved`** — Real-time or step token telemetry (Block 15).
5. **`UsageUpdated`** — Aggregated usage tracking.
6. **`ToolCalled`** — Tool invocation activity (Block 18).
7. **`ToolCompleted`** — Tool execution results (Block 18).
8. **`WebRequest`** — Outbound web request activity (Block 18).
9. **`WebResponse`** — Inbound web response telemetry (Block 18).
10. **`RetryStarted`** — Provider execution retry attempts.
11. **`ProviderError`** — Raw/normalized provider fault notifications.
12. **`StateChanged`** — Operational state machine transition (Block 20).
13. **`GovernorDecision`** — Policy enforcement outcomes (Block 21).
14. **`ControlActionIssued`** — Authoritative control signals issued to agent/runtime (Block 22).

---

## 4. Bus Delivery Semantics

* **In-Process & Synchronous:** Events are published and distributed synchronously without introducing threads, background workers, or external message broker dependencies.
* **Deterministic Ordering:** Subscribers are invoked in deterministic registration order.
* **Idempotency & Duplicate Conflict Detection:**
  - Duplicate identical event ID publication is safely idempotent.
  - Conflicting duplicate event ID publication raises [`DuplicateEventConflictError`](file:///Users/ssd/infuse/infuse/events/errors.py#L17-L23).
* **Subscriber Mutation Isolation:** The bus dispatches deep copies of events to handlers, ensuring mutations inside one subscriber do not corrupt events received by others.
* **Subscriber Error Boundary:** Exceptions thrown by individual subscribers are trapped, recorded in `handler_errors`, and isolated so other subscribers continue receiving events uninterrupted.
* **Filtering:** Handlers can subscribe globally or filter by specific `EventType` and/or `execution_id`.

---

## 5. Lifecycle Integration (Block 13 ↔ Block 14)

The [`ExecutionLifecycleService`](file:///Users/ssd/infuse/infuse/lifecycle/service.py#L52-L327) publishes events at canonical phase transitions:
1. **Entering `RUNNING`:** Publishes `ExecutionStarted` (`sequence=0`) with request, task, provider, and session metadata.
2. **Entering `COMPLETED`:** Publishes `ExecutionCompleted` (`sequence=1`) with duration and token consumption metrics.
3. **Entering `FAILED`:** Publishes `ExecutionFailed` with normalized error record and retryability flag.

---

## 6. Testing & In-Memory Test Collector

Block 14 provides [`InMemoryEventCollector`](file:///Users/ssd/infuse/infuse/events/collector.py#L9-L43) to safely record and assert published events in unit tests without turning the Event Bus into a persistent database.
