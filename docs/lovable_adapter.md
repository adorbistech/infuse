# INFUSE Lovable Agent Adapter Specification

**Milestone:** Block 27 (Additional Agent Adapters)  
**Status:** Complete / Ready for Freeze  
**Schema Version:** `1.0.0`  

---

## 1. Overview & Purpose

The **Lovable Agent Adapter** provides the concrete execution boundary between INFUSE's universal agent abstraction ([`IUniversalAgentAdapter`](file:///Users/ssd/infuse/infuse/agents/interfaces.py#L24-L95)) and the **Lovable Cloud Platform/API** (`https://api.lovable.dev`).

```text
Governor (Block 21)
   │
   ▼
Execution Control Boundary (Block 22)
   │
   ▼
Universal Agent Adapter (Block 23)
   │
   ▼
Lovable Adapter (Block 27)
   │
   ▼
Lovable Cloud API (REST/HTTP)
```

---

## 2. Agent vs Provider Separation

| Layer | Component | Responsibility |
| :--- | :--- | :--- |
| **Agent Adapter (Block 27)** | [`LovableAdapter`](file:///Users/ssd/infuse/infuse/agents/lovable/adapter.py#L48-L389) | Autonomous agent execution loop, session/project management, JSON response parsing, tool/web event mapping, and API execution control. |
| **Provider Adapter Layer (Block 12)** | `OpenAIProviderAdapter`, `AnthropicProviderAdapter`, etc. | Raw model API completion requests, token counts, and provider error status. |

The Lovable adapter does **not** perform provider/model routing, calculate token pricing, or duplicate Block 12 provider mechanics.

---

## 3. Universal Contract Implementation & Identity

### Identity
- `agent_id`: `lovable_adapter`
- `agent_name`: `lovable`
- `version`: `1.0.0`
- `runtime_type`: `cloud_api`

### Verified Capabilities
- `supports_cancel`: `True` (cancels in-flight API execution)
- `supports_terminate`: `True` (terminates active project build)
- `supports_throttle`: `False` (unsupported; returns `ControlStatus.UNSUPPORTED`)
- `supports_next_step_switch`: `False` (unsupported; returns `ControlStatus.UNSUPPORTED`)
- `supported_actions`: `[GovernorAction.CONTINUE, GovernorAction.STOP]`
- `supports_tool_interception`: `True` (normalizes tool execution payloads from response into canonical `ToolCalled` / `ToolCompleted` events)

---

## 4. Execution Model & Transport Architecture

```text
LovableAdapter
     │
     ▼
ILovableTransport (Interface)
     ├── LovableHttpTransport     (Live REST HTTP API transport)
     └── LovableReferenceTransport (Deterministic hermetic testing)
```

### Safety & Security
1. **Protected API Keys:** Sensitive tokens are never leaked into logs, payloads, or stdout.
2. **Secret Redaction:** Redacts API keys (`sk-...`, `lovable-...`), bearer tokens, and passwords from error messages and logs using [`redact_lovable_secrets()`](file:///Users/ssd/infuse/infuse/agents/lovable/models.py#L10-L29).
3. **Project ID Isolation:** Lovable `project_id` parameter is preserved as adapter metadata and never conflated with authoritative INFUSE `execution_id`.

---

## 5. Event and Tool/Web Normalization

- **Step Completion:** Emits standard [`ExecutionEvent`](file:///Users/ssd/infuse/infuse/contracts/events.py) envelopes (`EventType.EXECUTION_COMPLETED`, `EventSource.AGENT`) onto [`IEventBus`](file:///Users/ssd/infuse/infuse/events/interfaces.py#L12-L35).
- **Tool Normalization:** When tool activity is present in the response, publishes [`EventType.TOOL_CALLED`](file:///Users/ssd/infuse/infuse/contracts/events.py#L24) and [`EventType.TOOL_COMPLETED`](file:///Users/ssd/infuse/infuse/contracts/events.py#L25).
- **Web Normalization:** When web requests are present in the response, publishes [`EventType.WEB_REQUEST`](file:///Users/ssd/infuse/infuse/contracts/events.py#L26) and [`EventType.WEB_RESPONSE`](file:///Users/ssd/infuse/infuse/contracts/events.py#L27).
- **Error Normalization:** Converts network errors, authentication failures, and timeouts into [`AgentErrorRecord`](file:///Users/ssd/infuse/infuse/agents/models.py#L52-L58) with redacted error messages.
