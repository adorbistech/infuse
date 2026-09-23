# INFUSE Tool Activity Observer Specification

**Milestone:** Block 18 (Tool Activity Observer)  
**Status:** Complete / Ready for Freeze  
**Schema Version:** `1.0.0`  

---

## 1. Overview & Purpose

The **INFUSE Tool Activity Observer** is an in-memory, passive observation and deterministic aggregation layer downstream of the Event Bus (Block 14). It consumes canonical `ToolCalled` and `ToolCompleted` events to produce normalized tool activity facts associated with an execution.

```text
┌────────────────────────────────────────────────────────┐
│               EVENT CONTRACT & EVENT BUS               │
│                        (Block 14)                      │
│  • ToolCalled                                          │
│  • ToolCompleted                                       │
└───────────────────────────┬────────────────────────────┘
                            │
                      ExecutionEvent
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│         TOOL ACTIVITY OBSERVER (Block 18)              │
│  • Passive Event Consumption & Deduplication           │
│  • Invocations & Completion Correlation (call_id)      │
│  • Duration Calculation (ms) & Fallback Timestamp Diff │
│  • Outcome Classification (COMPLETED, FAILED, CALLED)  │
│  • Execution-Level Tool Activity Aggregates            │
└───────────────────────────┬────────────────────────────┘
                            │
                   ExecutionToolSummary
                   ToolInvocationRecord
                            │
                            ▼
          Execution State Engine (Block 20) / Governor (Block 21)
```

> [!IMPORTANT]
> **Core Separation of Responsibilities:**
> - **Tool Activity Observer:** *"What tool activity occurred during this execution?"*
> - **Policy Manager / Governor:** *"Was the tool allowed? Should it be retried or denied?"*
>
> The Tool Activity Observer observes and aggregates execution facts. It does **NOT** execute tools, invoke MCP servers, authorize/deny tools, enforce policies, retry failures, or mutate lifecycle state machines.

---

## 2. Tool Activity Observation Semantics

### Invocations & Call/Completion Correlation
* **Identity & Correlation:** Correlates `ToolCalled` and `ToolCompleted` events via canonical `call_id` in the event payload.
* **Concurrent & Interleaved Invocations:** Supports multiple overlapping tool calls (e.g. Call A, Call B, Comp B, Comp A) without arrival-order coupling.
* **Out-of-Order Delivery:** If `ToolCompleted` arrives prior to a delayed `ToolCalled`, completion facts are preserved and merged cleanly upon arrival of the call event.
* **Uncorrelated / Missing Completions:** Tool calls without completions remain in `CALLED` status (marked as incomplete, never assumed failed).

### Duration & Outcomes
* **Duration (`duration_ms`):** Preferred from explicit `duration_ms` in `ToolCompleted` payload; falls back to exact timestamp delta `(completed_at - started_at)` in milliseconds if $\ge 0$. Preserved as `None` if unobserved (never fabricated as `0.0`).
* **Success & Failure:**
  - `COMPLETED`: ToolCompleted with `success == True` and no error.
  - `FAILED`: ToolCompleted with `success == False` or an error payload.
  - `CALLED`: In-progress tool invocation awaiting completion.
* **Completeness (`ToolObservationCompleteness`):**
  - `COMPLETE`: At least one tool called and all calls have terminal completions.
  - `PARTIAL`: Open tool calls awaiting completion.
  - `UNKNOWN`: No tool activity observed.

### Deduplication & Idempotency
* Tracks processed `event_id` per execution run to ensure repeated event delivery does not duplicate invocations or double-count metrics.

---

## 3. Explicit Non-Responsibilities

| Non-Responsibility | Assigned Boundary |
| :--- | :--- |
| Tool execution, subprocesses, API calls | Tool Runtime / MCP Client |
| MCP server hosting or protocol transport | MCP Adapter Layer |
| Tool allowlists, denylists, permissions | Block 06 (Policy Manager) |
| Tool budget enforcement & throttling | Block 21 (Governor) |
| Web request / Web response observations | Block 19 (Web Activity Observer) |
| Lifecycle state machine transitions | Block 13 (Execution Lifecycle) |
| Token counting & token observations | Block 15 (Token Observer) |
| Economic pricing calculations | Block 16 (Economics Engine) |
| Provider health & error tracking | Block 17 (Health Engine) |
| Database persistence / External brokers | Infrastructure Layer |
