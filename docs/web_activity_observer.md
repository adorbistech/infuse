# INFUSE Web Activity Observer Specification

**Milestone:** Block 19 (Web Activity Observer)  
**Status:** Complete / Ready for Freeze  
**Schema Version:** `1.0.0`  

---

## 1. Overview & Purpose

The **INFUSE Web Activity Observer** is an in-memory, passive observation and deterministic aggregation layer downstream of the Event Bus (Block 14). It consumes canonical `WebRequest` and `WebResponse` events to produce normalized web activity facts associated with an execution.

```text
┌────────────────────────────────────────────────────────┐
│               EVENT CONTRACT & EVENT BUS               │
│                        (Block 14)                      │
│  • WebRequest                                          │
│  • WebResponse                                         │
└───────────────────────────┬────────────────────────────┘
                            │
                      ExecutionEvent
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│         WEB ACTIVITY OBSERVER (Block 19)               │
│  • Passive Event Consumption & Deduplication           │
│  • Request & Response Correlation (request_id)         │
│  • Method, URL, Status Code & Payload Size Capture     │
│  • Duration Calculation (ms) & Fallback Timestamp Diff │
│  • Outcome Classification (COMPLETED, FAILED, etc.)    │
│  • Execution-Level Web Activity Aggregates             │
└───────────────────────────┬────────────────────────────┘
                            │
                    ExecutionWebSummary
                     WebActivityRecord
                            │
                            ▼
          Execution State Engine (Block 20) / Governor (Block 21)
```

> [!IMPORTANT]
> **Core Separation of Responsibilities:**
> - **Web Activity Observer:** *"What web activity occurred during this execution?"*
> - **Policy Manager / Governor:** *"Was the web request allowed? Should it be retried, denied, or throttled?"*
>
> The Web Activity Observer observes and aggregates execution facts. It does **NOT** make HTTP/HTTPS network requests, automate browsers, crawl endpoints, authorize/deny URLs, enforce domain allowlists, retry failures, or mutate lifecycle state machines.

---

## 2. Web Activity Observation Semantics

### Request/Response Correlation & Identity
* **Identity & Correlation:** Correlates `WebRequest` and `WebResponse` events via canonical `request_id` (or `correlation_id`) in the event payload.
* **Fallback Correlation:** When explicit request identifiers are omitted, correlates open in-flight requests matching the same target URL.
* **Concurrent & Interleaved Requests:** Supports multiple overlapping web requests (e.g. Req A, Req B, Resp B, Resp A) without arrival-order coupling.
* **Out-of-Order Delivery:** If `WebResponse` arrives prior to a delayed `WebRequest`, response facts (status code, duration, bytes) are preserved and merged cleanly upon arrival of the request event.
* **Uncorrelated / Missing Responses:** Requests without responses remain in `REQUESTED` status (marked as incomplete/in-flight, never assumed failed).

### Status Codes, Duration & Outcomes
* **HTTP Methods & Target URLs:** Captures requested method (`GET`, `POST`, `PUT`, `DELETE`, etc.) and target URL.
* **Status Codes & Byte Counts:** Captures integer status codes (e.g. `200`, `404`, `500`) and payload `bytes_transferred`.
* **Duration (`duration_ms`):** Preferred from explicit `duration_ms` in `WebResponse` payload; falls back to exact timestamp delta `(responded_at - requested_at)` in milliseconds if $\ge 0$. Preserved as `None` if unobserved (never fabricated as `0.0`).
* **Success & Failure:**
  - `COMPLETED`: Response with $200 \le \text{status\_code} < 400$ or `success == True`.
  - `FAILED`: Response with $\text{status\_code} \ge 400$, `success == False`, or an explicit `error` payload.
  - `REQUESTED`: In-flight web request awaiting response.
* **Completeness (`WebObservationCompleteness`):**
  - `COMPLETE`: At least one web request observed and all requests have terminal responses.
  - `PARTIAL`: In-flight requests awaiting response.
  - `UNKNOWN`: No web activity observed.

### Deduplication & Idempotency
* Tracks processed `event_id` per execution run to ensure repeated event delivery does not duplicate requests or double-count metrics.

---

## 3. Explicit Non-Responsibilities

| Non-Responsibility | Assigned Boundary |
| :--- | :--- |
| HTTP/HTTPS requests, sockets, network calls | Web Client / Runtime |
| Browser automation, scraping, crawling | Web Crawler / Browser Layer |
| Domain allowlists, denylists, URL policies | Block 06 (Policy Manager) |
| Web rate limits, throttling, budgets | Block 21 (Governor) |
| Tool activity observations (ToolCalled/Completed) | Block 18 (Tool Activity Observer) |
| Lifecycle state machine transitions | Block 13 (Execution Lifecycle) |
| Token counting & token observations | Block 15 (Token Observer) |
| Economic pricing calculations | Block 16 (Economics Engine) |
| Provider health & error tracking | Block 17 (Health Engine) |
| Database persistence / External brokers | Infrastructure Layer |
