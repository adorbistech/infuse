# INFUSE Claude Code Agent Adapter Specification

**Milestone:** Block 24 (Claude Code Adapter)  
**Status:** Complete / Ready for Freeze  
**Schema Version:** `1.0.0`  

---

## 1. Overview & Purpose

The **Claude Code Agent Adapter** implements the concrete execution boundary between INFUSE's universal agent abstraction ([`IUniversalAgentAdapter`](file:///Users/ssd/infuse/infuse/agents/interfaces.py#L24-L95)) and the **Claude Code CLI runtime** (`claude`).

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
Claude Code Adapter (Block 24)
   │
   ▼
Claude Code CLI Subprocess (claude)
```

---

## 2. Agent vs Provider Separation

| Layer | Component | Responsibility |
| :--- | :--- | :--- |
| **Agent Adapter (Block 24)** | [`ClaudeCodeAdapter`](file:///Users/ssd/infuse/infuse/agents/claude/adapter.py#L48-L352) | Autonomous agent execution loop, session management, and CLI process control. |
| **Provider Adapter (Block 12)** | `AnthropicProviderAdapter` | Raw Anthropic API calls, message completion requests, token counts, and provider error status. |

The Claude Code adapter does **not** call Anthropic APIs directly, calculate token pricing, or duplicate Block 12 provider mechanics.

---

## 3. Universal Contract Implementation & Identity

### Identity
- `agent_id`: `claude_code_adapter`
- `agent_name`: `claudecode`
- `version`: `1.0.0`
- `runtime_type`: `cli`

### Verified Capabilities
- `supports_cancel`: `True` (cancels running CLI process via `SIGTERM` / `proc.terminate()`)
- `supports_terminate`: `True` (hard terminates process via `SIGKILL` / `proc.kill()`)
- `supports_throttle`: `False` (CLI does not offer native step rate-limiting; returns `ControlStatus.UNSUPPORTED`)
- `supports_next_step_switch`: `False` (mid-session model switching not supported; returns `ControlStatus.UNSUPPORTED`)
- `supported_actions`: `[GovernorAction.CONTINUE, GovernorAction.STOP]`

---

## 4. Execution Model & Transport Architecture

```text
ClaudeCodeAdapter
       │
       ▼
IClaudeTransport (Interface)
       ├── ClaudeSubprocessTransport (Live claude CLI subprocess)
       └── ClaudeReferenceTransport  (Deterministic hermetic testing)
```

### Subprocess Safety & Security
1. **Zero Shell Interpolation:** Always uses direct array vectors `[cli, "-p", prompt, ...]` with `shell=False`.
2. **Secret Redaction:** Redacts API keys (`sk-ant-...`, `claude-...`), bearer tokens, and passwords from error messages and logs using [`redact_secrets()`](file:///Users/ssd/infuse/infuse/agents/claude/models.py#L10-L29).
3. **Timeout Safeguards:** Subprocesses that exceed configured timeout limits are terminated immediately.

---

## 5. Event and Error Normalization

- **Event Publication:** Emits standard [`ExecutionEvent`](file:///Users/ssd/infuse/infuse/contracts/events.py) envelopes (`EventType.EXECUTION_COMPLETED`, `EventSource.AGENT`) onto [`IEventBus`](file:///Users/ssd/infuse/infuse/events/interfaces.py#L12-L35).
- **Error Normalization:** Converts process exits, CLI not found, and timeouts into [`AgentErrorRecord`](file:///Users/ssd/infuse/infuse/agents/models.py#L52-L58) with redacted error messages.
