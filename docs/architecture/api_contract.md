# INFUSE Universal HTTP API Specification

**Milestone:** Block 05 (Universal HTTP API)  
**Status:** Frozen  
**Schema Version:** `1.0.0`  
**Base Path:** `/v1`  
**Contract Baseline:** Block 00 Universal Contracts (`infuse.contracts.*`)  
**Frontend Baseline:** Block 04 Frontend Data & State Contract (`IDataProvider`, `ExecutionBundleViewModel`, `GovernancePolicyViewModel`)  

---

## 1. Overview & Architecture

The **Universal HTTP API** establishes the transport and schema boundary between external clients (autonomous AI agents, SDKs, CLI tools, MCP sidecars, and the INFUSE Stitch frontend) and the INFUSE execution intelligence core.

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        INFUSE STITCH FRONTEND                          │
│                                                                        │
│  [Execution Surface]                          [Governance Surface]     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
                         IDataProvider Interface
                                    │
                                    ▼
                          ApiDataProvider (HTTP)
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│                       UNIVERSAL HTTP API LAYER                         │
│                                                                        │
│   POST /v1/execute              POST /v1/executions/{id}/events        │
│   GET  /v1/executions           GET  /v1/policies                      │
│   GET  /v1/executions/{id}      PUT  /v1/policies/{id}                 │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
                             Transport Schema
                 (Correlation ID, Error Normalization, DTOs)
                                    │
                                    ▼
                             Service Boundary
             (IExecutionService, IEventService, IPolicyService)
                                    │
                                    ▼
                            Repository Boundary
                 (IExecutionRepository, IPolicyRepository)
                                    │
                                    ▼
                     Future Core Engines (Blocks 06+)
     (Policy Manager, Router, Observers, Governor, State Engine, Bus)
```

> [!IMPORTANT]
> **Block 05 Scope Boundary:**
> Block 05 implements the HTTP/JSON transport layer, request parsing, schema validation, response serialization, normalized error handling, correlation propagation, and clean service/repository interfaces.
> It does **NOT** implement:
> * Autonomous execution or model calling
> * Provider routing, scoring, or selection
> * Governor decisions or circuit breakers
> * Policy Manager validation rules or enforcement
> * Token, economics, or health observers
> * External database persistence (PostgreSQL, SQLite, Redis)

---

## 2. API Endpoints

### 2.1 Operational & Health

#### `GET /health` / `GET /v1/health`
Returns the operational health and version of the API service.

**Response (200 OK):**
```json
{
  "status": "OK",
  "version": "0.1.0",
  "schema_version": "1.0.0"
}
```

---

### 2.2 Execution Lifecycle

#### `POST /v1/execute`
Submits an agent operation to INFUSE for execution regulation and telemetry capture.

* **Request Body:** [`ExecutionRequest`](file:///Users/ssd/infuse/infuse/contracts/execution.py#L144-L170)
* **Response (200 OK):** [`ExecutionResult`](file:///Users/ssd/infuse/infuse/contracts/execution.py#L227-L257)

**Example Request:**
```json
{
  "request_id": "req_01J8K7A0",
  "task": {
    "task_id": "task_auth_refactor",
    "description": "Refactor authentication middleware",
    "workload_hint": "coding",
    "tags": ["backend", "security"]
  },
  "request": {
    "messages": [
      {
        "role": "user",
        "content": "Refactor JWT middleware to use decoupled token validators."
      }
    ],
    "parameters": {
      "temperature": 0.2
    }
  },
  "requirements": {
    "preferred_providers": ["Anthropic"],
    "preferred_models": ["Claude Sonnet"]
  },
  "execution_context": {
    "agent_id": "OpenCode",
    "session_id": "sess_01"
  }
}
```

**Example Response:**
```json
{
  "execution_id": "exec_01J8K7A2",
  "request_id": "req_01J8K7A0",
  "status": "COMPLETED",
  "response": {
    "content": "Authentication middleware refactored to use decoupled JWT validators.",
    "role": "assistant"
  },
  "execution": {
    "provider": "Anthropic",
    "model": "Claude Sonnet",
    "input_tokens": 42800,
    "cached_tokens": 18400,
    "output_tokens": 8280,
    "total_tokens": 69480,
    "cost_usd": 0.184,
    "latency_ms": 1240.0,
    "requests_count": 14,
    "retries_count": 0,
    "tool_calls_count": 11,
    "web_requests_count": 6,
    "errors_count": 0,
    "state": "COST_PRESSURE",
    "metadata": {
      "agent_name": "OpenCode",
      "task_description": "Refactor authentication middleware"
    }
  },
  "decision": {
    "action": "OPTIMIZE",
    "reason": "Cost velocity approaching budget pacing boundary.",
    "reason_codes": ["COST_LIMIT_WARNING"]
  },
  "schema_version": "1.0.0"
}
```

---

#### `GET /v1/executions`
Retrieves a paginated and filterable list of execution summaries for the history table and telemetry surface.

* **Query Parameters:**
  * `query` (string, optional): Substring filter for ID, task description, or agent name.
  * `state` (string, optional): Filter by execution state (`NORMAL`, `COST_PRESSURE`, `RUNAWAY`, `QUALITY_DEGRADED`, `PROVIDER_CONSTRAINED`).
  * `agent` (string, optional): Filter by agent identifier (e.g. `OpenCode`, `Claude Code`).
  * `limit` (int, default: 50, range: 1..200): Page size.
  * `offset` (int, default: 0, min: 0): Page offset.
* **Response (200 OK):**
```json
{
  "executions": [ ... ],
  "total": 7,
  "limit": 50,
  "offset": 0,
  "schema_version": "1.0.0"
}
```

---

#### `GET /v1/executions/{id}`
Retrieves normalized execution detail and telemetry for a specific execution run.

* **Path Parameters:**
  * `id` (string, required): Execution identifier.
* **Response (200 OK):** [`ExecutionResult`](file:///Users/ssd/infuse/infuse/contracts/execution.py#L227-L257)
* **Response (404 Not Found):** Normalized [`ApiErrorResponse`](file:///Users/ssd/infuse/infuse/api/schemas/errors.py#L10-L28).

---

### 2.3 Event Ingestion

#### `POST /v1/executions/{id}/events`
Ingests an observation telemetry event into the execution run's event ledger.

* **Path Parameters:**
  * `id` (string, required): Execution identifier.
* **Request Body:** [`ExecutionEvent`](file:///Users/ssd/infuse/infuse/contracts/events.py#L106-L136)
* **Response (201 Created):**
```json
{
  "status": "INGESTED",
  "event_id": "evt_01J8K7E0",
  "execution_id": "exec_01J8K7A2",
  "schema_version": "1.0.0"
}
```
* **Response (404 Not Found):** If target `execution_id` does not exist.
* **Response (422 Unprocessable Entity):** If event schema is malformed.

---

### 2.4 Governance Policies

#### `GET /v1/policies`
Retrieves the active governance policy and all stored policy revisions.

* **Response (200 OK):**
```json
{
  "policies": [ ... ],
  "active_policy": {
    "policy_id": "pol_default",
    "name": "Default Execution Policy",
    "version": "1.0.0",
    "is_active": true,
    "budget": { ... },
    "tokens": { ... },
    "requests": { ... },
    "runtime": { ... },
    "providers": { ... },
    "web": { ... },
    "tools": { ... },
    "retries": { ... },
    "anomaly": { ... },
    "actions": { ... }
  },
  "schema_version": "1.0.0"
}
```

---

#### `PUT /v1/policies/{id}`
Creates or updates a governance policy envelope.

* **Path Parameters:**
  * `id` (string, required): Policy identifier.
* **Request Body:** [`GovernancePolicy`](file:///Users/ssd/infuse/infuse/contracts/policy.py#L198-L256)
* **Response (200 OK):** Updated [`GovernancePolicy`](file:///Users/ssd/infuse/infuse/contracts/policy.py#L198-L256).
* **Response (422 Unprocessable Entity):** If policy schema fails validation.

---

## 3. Normalized API Error Contract

All non-2xx responses conform to the normalized `ApiErrorResponse` schema:

```json
{
  "code": "VALIDATION_ERROR",
  "message": "Invalid execution request schema.",
  "details": {
    "errors": [
      {
        "type": "missing",
        "loc": ["request_id"],
        "msg": "Field required"
      }
    ]
  },
  "correlation_id": "corr_9f2a08c1d5b3",
  "schema_version": "1.0.0"
}
```

### HTTP Status Code Taxonomy
| HTTP Status | Error Code (`code`) | Trigger Condition |
|---|---|---|
| **400 Bad Request** | `BAD_REQUEST` | Invalid query/path parameter format (e.g. non-numeric limit/offset). |
| **400 Bad Request** | `MALFORMED_JSON` | Request payload is not valid JSON. |
| **404 Not Found** | `NOT_FOUND` | Target `execution_id` or `policy_id` does not exist. |
| **409 Conflict** | `CONFLICT` | Resource identifier or revision version conflict. |
| **422 Unprocessable Entity** | `VALIDATION_ERROR` | Request payload fails Pydantic schema validation or type constraints. |
| **500 Internal Server Error** | `INTERNAL_ERROR` | Unexpected server fault; sanitized error message returned without stack trace leakage. |

---

## 4. Tracing & Correlation

Every HTTP request receives a correlation identifier via the `CorrelationIdMiddleware`:
1. If the caller supplies `X-Correlation-ID` or `X-Request-ID`, it is preserved.
2. If absent, a unique UUID (`corr_<12-hex>`) is automatically generated.
3. The identifier is returned in the `X-Correlation-ID` response header and embedded in all error payloads.

---

## 5. Clean Layered Boundaries

```text
HTTP Request
    │
    ▼
[Transport Layer]
    ├── Starlette Routes (infuse/api/routes/)
    ├── CorrelationIdMiddleware (infuse/api/app.py)
    └── Error Handling & Serialization (infuse/api/errors.py)
    │
    ▼
[Service Layer] (infuse/api/services/interfaces.py)
    ├── IExecutionService
    ├── IEventService
    └── IPolicyService
    │
    ▼
[Repository Layer] (infuse/api/repositories/interfaces.py)
    ├── IExecutionRepository
    └── IPolicyRepository
```

The service and repository interfaces can be replaced with production implementations (Block 06+ Policy Manager, Block 11 Router, Block 14 Event Bus, Block 21 Governor) without modifying route handlers.
