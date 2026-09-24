# INFUSE Universal Agent Adapter Specification

**Milestone:** Block 23 (Universal Agent Adapter)  
**Status:** Complete / Ready for Freeze  
**Schema Version:** `1.0.0`  

---

## 1. Overview & Purpose

The **Universal Agent Adapter** establishes the vendor-neutral execution boundary between the INFUSE control and observation systems and autonomous AI agents.

```text
Governor (Block 21)
   │
   ▼
Execution Control Boundary (Block 22)
   │
   ▼
Universal Agent Adapter (Block 23)
   │
   ├───────────────────────────────┐
   ▼                               ▼
Claude Code (Block 24)       OpenCode (Block 25) ... Codex (Block 26) ...
```

> [!IMPORTANT]
> **Block 23 establishes the universal contract and reference implementation only.**
> Concrete integrations (Claude Code, OpenCode, Codex, Hermes, OpenClaw, Lovable) belong strictly to Blocks 24–27.

---

## 2. Strict Separation of Concerns

| Domain | Responsible Entity | Scope |
| :--- | :--- | :--- |
| **Agent** | Autonomous Runtime | Reasoning, prompt engineering, task decomposition, memory, internal planning loop. |
| **INFUSE** | Execution Core | Observation, context, governance, state engine, control decisions, normalized execution boundary. |

The Universal Agent Adapter does **not** implement agent reasoning, planning, memory, or LLM loops.

---

## 3. Normalized Interface & Identity

### Adapter Identity
Autonomous agents are uniquely registered via [`AgentIdentity`](file:///Users/ssd/infuse/infuse/agents/models.py#L21-L28):
- `agent_id`: Unique runtime instance identifier.
- `agent_name`: Normalized canonical agent name (e.g. `opencode`, `claudecode`, `codex`).
- `version`: Adapter semantic version.
- `runtime_type`: Runtime execution substrate category.

### Universal Interface
[`IUniversalAgentAdapter`](file:///Users/ssd/infuse/infuse/agents/interfaces.py#L24-L95) exposes:
- **Capability Discovery:** `get_agent_capability()`, `supports_cancel()`, `supports_throttle()`, `supports_next_step_switch()`, `supports_terminate()`, `supports_action()`.
- **Execution Attachment:** `attach_execution()`, `detach_execution()`, `get_session()`.
- **Normalized Step Execution:** `execute_step(request) -> AgentStepResponse`.
- **Physical Control Execution:** `execute_control(operation) -> ControlResult` (implementing [`IControlExecutor`](file:///Users/ssd/infuse/infuse/control/interfaces.py#L16-L30)).
- **Error Normalization:** `normalize_error(raw_error) -> AgentErrorRecord`.
- **Event Bus Integration:** `attach_to_bus(bus)`.

---

## 4. Capability Bridge & Block 22 Integration

The Universal Agent Adapter implements [`IControlExecutor`](file:///Users/ssd/infuse/infuse/control/interfaces.py#L16-L30) to integrate directly with Block 22's [`ExecutionControlBoundary`](file:///Users/ssd/infuse/infuse/control/boundary.py#L19-L230).

- The adapter declares what physical control commands the underlying agent runtime can execute.
- When Block 22 dispatches a Governor decision, the adapter executes the physical operation or returns `ControlStatus.UNSUPPORTED` / `ControlStatus.FAILED`.
- **Zero False Success:** Unsupported operations are never reported as `COMPLETED` or `ACCEPTED`.

---

## 5. Event Normalization

When step or execution transitions occur, the adapter emits canonical [`ExecutionEvent`](file:///Users/ssd/infuse/infuse/contracts/events.py) objects directly onto the [`IEventBus`](file:///Users/ssd/infuse/infuse/events/interfaces.py#L12-L35) without directly invoking observers, preserving strict architectural fan-out.
