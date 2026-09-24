# INFUSE Execution Control Boundary Specification

**Milestone:** Block 22 (Execution Control Boundary)  
**Status:** Complete / Ready for Freeze  
**Schema Version:** `1.0.0`  

---

## 1. Overview & Architectural Role

The **Execution Control Boundary** bridges Governor decisions and the physical execution runtime:

```text
User Policy
     ↓
Policy Manager (Block 06)
     ↓
Execution State (Block 20) ──► GOVERNOR (Block 21) ──► GovernorDecisionRecord
                                                           │
                                                           │ (GovernorAction)
                                                           ▼
                                            ┌──────────────────────────────┐
                                            │ BLOCK 22                     │
                                            │ EXECUTION CONTROL BOUNDARY   │
                                            └──────────────┬───────────────┘
                                                           │
                                                   capability verification
                                                           │
                                                           ▼
                                                    Agent / Runtime
                                                           │
                                                           ▼
                                                       Execution
```

> [!IMPORTANT]
> **Strict Separation of Governance vs Control Application:**
> - **Governor (Block 21):** *"WHAT SHOULD HAPPEN"* (sole control decision authority).
> - **Execution Control Boundary (Block 22):** *"WHETHER AND HOW THAT DECISION CAN SAFELY BE APPLIED"* (capability verification, dispatch, and outcome recording).
> - **Agent Adapter / Runtime (Blocks 23+):** *"PHYSICALLY PERFORMS THE OPERATION"* (e.g. process cancellation, socket throttling, provider switching).

---

## 2. Capability Model & Action Mapping

Execution targets declare control capabilities through [`ControlCapability`](file:///Users/ssd/infuse/infuse/contracts/control.py#L25-L51):

| Capability Field | Purpose | Target Actions |
| :--- | :--- | :--- |
| **`supports_cancel`** | Graceful mid-flight cancellation. | `STOP` |
| **`supports_terminate`** | Hard process termination. | `STOP` |
| **`supports_throttle`** | Artificial pacing/rate throttling. | `THROTTLE` |
| **`supports_next_step_switch`** | Step-boundary model/provider routing changes. | `SWITCH` |
| **`supported_actions`** | Explicitly declared Governor actions. | `CONTINUE`, `OPTIMIZE`, `DOWNGRADE`, `ESCALATE` |

---

## 3. Unsupported Capability = Safe Failure (No False Success)

If the Governor requests an action that the execution target does not declare capability for:
- The Control Boundary **NEVER** pretends the action succeeded.
- The Control Boundary **NEVER** converts the action into an alternative (e.g., converting `THROTTLE` into `STOP`).
- The Control Boundary **NEVER** makes a new Governor decision.
- The Control Boundary **NEVER** retries indefinitely.

Instead, an explicit [`ControlResult`](file:///Users/ssd/infuse/infuse/contracts/control.py#L77-L107) with `status=ControlStatus.UNSUPPORTED` is returned and logged in the immutable audit history.

---

## 4. Control Dispatch Interface

Dispatches follow the canonical signature:
```python
def dispatch_control(
    execution_id: str,
    action: GovernorAction,
    params: Optional[Dict[str, Any]] = None,
    operation_id: Optional[str] = None
) -> ControlResult:
```

### Dispatch Flow:
1. Validate `execution_id` and `action`.
2. Check idempotency cache against `operation_id`.
3. Emit [`ControlActionIssued`](file:///Users/ssd/infuse/infuse/contracts/events.py) event on the event bus.
4. Verify declared capability via `supports_action(execution_id, action)`.
5. If supported and a physical executor is registered, call `executor.execute_control(operation)` inside a safe error handler.
6. If executor throws or returns physical failure, preserve `ControlStatus.FAILED` without false success.
7. Record complete audit entry in [`ControlAuditRecord`](file:///Users/ssd/infuse/infuse/control/models.py).

---

## 5. Explicit Non-Responsibilities

| Non-Responsibility | Assigned Boundary |
| :--- | :--- |
| Control decision making (STOP/SWITCH/THROTTLE) | Block 21 (Governor Engine) |
| Policy evaluation and threshold checking | Block 06 (Policy Manager) |
| State classification and observation synthesis | Block 20 (Execution State Engine) |
| Provider / model routing and resolution | Block 10 & 11 (Resolver / Router) |
| Retry loops and scheduling | Block 12 & 13 (Adapter / Lifecycle) |
| Lifecycle state mutation | Block 13 (Lifecycle Engine) |
| Physical Agent CLI integration (OpenCode/Claude/Codex) | Blocks 23–27 (Agent Adapters) |
