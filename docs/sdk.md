# INFUSE SDK Specification & Developer Guide

The **INFUSE SDK** (`infuse.sdk`) is a thin, typed, developer-facing client interface over the universal INFUSE API contracts, execution lifecycle, governance policies, telemetry events, and execution control boundaries.

---

## 1. Architectural Role & Boundary

The SDK provides programmatic access for applications, orchestrators, and agent runtimes to interact with INFUSE services.

```text
Developer Application / Agent Harness
                 │
                 ▼
          ┌─────────────┐
          │  InfuseSDK  │
          └──────┬──────┘
                 │ (HTTP / Transport Boundary)
                 ▼
       ┌──────────────────┐
       │   INFUSE Core    │
       │  (Blocks 00–27)  │
       └──────────────────┘
```

### Architectural Guarantees:
- **Thin Interface:** The SDK never reimplements execution, routing, pricing calculation, state machines, or Governor rule evaluation.
- **Contract Fidelity:** Re-exports and adheres 100% to canonical Block 00 data contracts and schemas.
- **Provider & Agent Agnostic:** Contains zero provider-specific or runtime-specific manipulation logic.
- **Zero Direct Agent Manipulation:** Control operations delegate strictly through the `ExecutionControlBoundary` (Block 22).
- **Redaction by Default:** Sensitive credential tokens (`api_key`, `Bearer`, `token`) are automatically redacted from all SDK error representations.

---

## 2. Installation & Quickstart

```python
from infuse.sdk import InfuseClient, ExecutionRequest, TaskContext, OperationRequest

# Initialize client (reads INFUSE_BASE_URL and INFUSE_API_KEY from environment if omitted)
client = InfuseClient(base_url="http://localhost:8000", api_key="infuse_live_token")

# Submit execution
request = ExecutionRequest(
    request_id="req_987654",
    task=TaskContext(task_id="task_build_service", description="Implement auth service"),
    request=OperationRequest(messages=[{"role": "user", "content": "Refactor tokens"}]),
)
result = client.execute(request)

print(f"Execution ID: {result.execution_id}, Status: {result.status}")
```

---

## 3. Sub-Clients & Public API

The `InfuseClient` aggregates focused domain clients:

| Sub-client | Property | Primary Operations |
| :--- | :--- | :--- |
| **ExecutionClient** | `client.executions` | `execute(req)`, `get(id)`, `list(query, state, limit, offset)`, `get_state(id)` |
| **PolicyClient** | `client.policies` | `get_active()`, `list()`, `update(id, policy)` |
| **EventClient** | `client.events` | `publish(execution_id, event)` |
| **GovernorClient** | `client.governor` | `get_decision(execution_id)` |
| **ControlClient** | `client.control` | `cancel(id)`, `terminate(id)`, `throttle(id, delay_ms)`, `switch(id, target_model)`, `get_capability(id)`, `get_history(id)`, `get_latest(id)` |

---

## 4. Code Examples

### 4.1 Submitting and Querying Executions

```python
from infuse.sdk import InfuseClient

client = InfuseClient()

# List recent executions
history = client.list_executions(query="auth", limit=10)
for item in history.items:
    print(f"[{item.status}] {item.execution_id}: {item.task_description} ({item.agent_name})")

# Retrieve single execution telemetry
summary = client.get_execution("exec_01J8K7A2")
print(f"Provider: {summary.provider}, Model: {summary.model}")
```

### 4.2 Ingesting Real-Time Telemetry Events

```python
from infuse.sdk import InfuseClient, ExecutionEvent, EventType, EventSource

client = InfuseClient()

event = ExecutionEvent(
    event_id="evt_tool_123",
    execution_id="exec_01J8K7A2",
    type=EventType.TOOL_COMPLETED,
    source=EventSource.AGENT,
    sequence=3,
    payload={
        "tool_name": "ast_parser",
        "duration_ms": 142.5,
        "success": True,
    },
)

response = client.publish_event("exec_01J8K7A2", event)
print(f"Event Ingestion Status: {response.status}")
```

### 4.3 Inspecting Policies and Updating Governance

```python
from infuse.sdk import InfuseClient, BudgetControls

client = InfuseClient()

# Get active policy
active_policy = client.get_active_policy()
print(f"Active Policy: {active_policy.name} (v{active_policy.version})")

# Update budget limits
active_policy.budget.max_cost_per_task = 3.50
updated_policy = client.update_policy(active_policy.policy_id, active_policy)
print(f"Updated Policy Revision: {updated_policy.version}")
```

### 4.4 Dispatched Control Operations

```python
from infuse.sdk import InfuseClient, ControlStatus

client = InfuseClient()

# Safely issue a cancel request through the Execution Control Boundary
ctrl_result = client.cancel("exec_01J8K7A2", reason="User stopped task via IDE")

if ctrl_result.status == ControlStatus.ACCEPTED:
    print("Execution successfully halted.")
elif ctrl_result.status == ControlStatus.UNSUPPORTED:
    print(f"Agent does not support cancellation: {ctrl_result.message}")
```

---

## 5. Transport Layer & Pluggability

The SDK communicates through the `ITransport` abstraction:
- **`HttpTransport`:** Default standard library HTTP client (`urllib.request`) requiring zero external third-party network libraries.
- **`ReferenceTransport`:** In-memory deterministic routing transport for unit and regression testing.
- **Custom Transports:** Easily pass custom transports (e.g. `httpx`, `aiohttp`, Starlette `TestClient`) conforming to `ITransport.send_request`.

```python
from infuse.sdk import InfuseClient, HttpTransport, ClientConfig

transport = HttpTransport(config=ClientConfig(timeout_seconds=60.0))
client = InfuseClient(transport=transport)
```

---

## 6. Error Taxonomy

All SDK errors inherit from `InfuseSdkError`:

```text
InfuseSdkError
├── TransportError
│   └── TimeoutError
├── AuthenticationError
├── ValidationError
├── NotFoundError
├── ConflictError
├── UnsupportedControlError
├── ControlExecutionError
├── MalformedResponseError
└── ServerError
```

Every exception automatically sanitizes any sensitive credentials from tracebacks and messages.
