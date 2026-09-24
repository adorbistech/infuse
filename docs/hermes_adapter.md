# INFUSE Hermes Agent Adapter Specification

**Milestone:** Block 27 (Additional Agent Adapters)  
**Status:** Complete / Ready for Freeze  
**Schema Version:** `1.0.0`  

---

## 1. Overview & Purpose

The **Hermes Agent Adapter** provides the concrete execution boundary between INFUSE's universal agent abstraction ([`IUniversalAgentAdapter`](file:///Users/ssd/infuse/infuse/agents/interfaces.py#L24-L95)) and the **Nous Research Hermes Agent runtime** (`hermes`).

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
Hermes Adapter (Block 27)
   │
   ▼
Hermes CLI Subprocess (hermes)
```

---

## 2. Agent vs Provider Separation

| Layer | Component | Responsibility |
| :--- | :--- | :--- |
| **Agent Adapter (Block 27)** | [`HermesAdapter`](file:///Users/ssd/infuse/infuse/agents/hermes/adapter.py#L48-L389) | Autonomous agent execution loop, session management, JSON stream parsing, tool/web event mapping, and CLI process control. |
| **Provider Adapter Layer (Block 12)** | `OpenAIProviderAdapter`, `AnthropicProviderAdapter`, etc. | Raw model API completion requests, token counts, and provider error status. |

The Hermes adapter does **not** perform provider/model routing, calculate token pricing, or duplicate Block 12 provider mechanics.

---

## 3. Universal Contract Implementation & Identity

### Identity
- `agent_id`: `hermes_adapter`
- `agent_name`: `hermes`
- `version`: `1.0.0`
- `runtime_type`: `cli`

### Verified Capabilities
- `supports_cancel`: `True` (cancels running CLI process via `SIGTERM` / `proc.terminate()`)
- `supports_terminate`: `True` (hard terminates process via `SIGKILL` / `proc.kill()`)
- `supports_throttle`: `False` (CLI does not offer native step rate-limiting; returns `ControlStatus.UNSUPPORTED`)
- `supports_next_step_switch`: `False` (mid-session model switching not supported; returns `ControlStatus.UNSUPPORTED`)
- `supported_actions`: `[GovernorAction.CONTINUE, GovernorAction.STOP]`
- `supports_tool_interception`: `True` (normalizes tool execution payloads from output into canonical `ToolCalled` / `ToolCompleted` events)

---

## 4. Execution Model & Transport Architecture

```text
HermesAdapter
     │
     ▼
IHermesTransport (Interface)
     ├── HermesSubprocessTransport (Live hermes CLI subprocess at /Volumes/Adorbis/bin/hermes)
     └── HermesReferenceTransport  (Deterministic hermetic testing)
```

### Subprocess Safety & Security
1. **Zero Shell Interpolation:** Always uses direct array vectors `[cli, "-z", prompt, ...]` with `shell=False`.
2. **Secret Redaction:** Redacts API keys (`sk-...`, `hermes-...`), bearer tokens, and passwords from error messages and logs using [`redact_hermes_secrets()`](file:///Users/ssd/infuse/infuse/agents/hermes/models.py#L10-L29).
3. **Timeout Safeguards:** Subprocesses that exceed configured timeout limits are terminated immediately.

---

## 5. Event and Tool/Web Normalization

- **Step Completion:** Emits standard [`ExecutionEvent`](file:///Users/ssd/infuse/infuse/contracts/events.py) envelopes (`EventType.EXECUTION_COMPLETED`, `EventSource.AGENT`) onto [`IEventBus`](file:///Users/ssd/infuse/infuse/events/interfaces.py#L12-L35).
- **Tool Normalization:** When tool activity is present in the output, publishes [`EventType.TOOL_CALLED`](file:///Users/ssd/infuse/infuse/contracts/events.py#L24) and [`EventType.TOOL_COMPLETED`](file:///Users/ssd/infuse/infuse/contracts/events.py#L25).
- **Web Normalization:** When web requests/searches are present in the output, publishes [`EventType.WEB_REQUEST`](file:///Users/ssd/infuse/infuse/contracts/events.py#L26) and [`EventType.WEB_RESPONSE`](file:///Users/ssd/infuse/infuse/contracts/events.py#L27).
- **Error Normalization:** Converts process exits, CLI not found, and timeouts into [`AgentErrorRecord`](file:///Users/ssd/infuse/infuse/agents/models.py#L52-L58) with redacted error messages.
