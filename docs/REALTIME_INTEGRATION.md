# Real-Time Agent Workflow Integration Guide

This guide explains how to embed **INFUSE (Execution Intelligence)** into real-time, multi-step autonomous agent execution loops.

---

## 1. Architectural Model

Placing INFUSE around an agent does not require replacing the agent's reasoning or tools. Instead, INFUSE operates as a **closed-loop voltage regulator**:

```text
┌──────────────────────────────────────────────────────────────┐
│                      YOUR APPLICATION                        │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                      INFUSE CLIENT / SDK                     │
└──────────────────────────────┬───────────────────────────────┘
                               │
               ┌───────────────┴───────────────┐
               │ (Execution Session Initiated) │
               ▼                               ▼
┌──────────────────────────────┐ ┌──────────────────────────────┐
│       AGENT EXECUTION        │ │       INFUSE GOVERNOR        │
│ 1. Agent plans step          │ │ 1. Ingests events            │
│ 2. Agent calls tools / LLMs  │ │ 2. Updates execution state   │
│ 3. Emits ExecutionEvent ─────┼─┼─► (NORMAL / RUNAWAY / etc.)  │
│ 4. Polls / receives decision │ │ 3. Evaluates policy          │
│    ◄─────────────────────────┼─┼── (CONTINUE / THROTTLE / STOP)
│ 5. Executes next step safely │ │                              │
└──────────────────────────────┘ └──────────────────────────────┘
```

---

## 2. Step-by-Step Implementation

### Step 1: Initialize the Session

Before running an agent loop, register the execution with INFUSE:

```python
from infuse.sdk import InfuseClient, ExecutionRequest, TaskContext, OperationRequest

client = InfuseClient(base_url="http://localhost:8000")

# Register the autonomous task session
session_request = ExecutionRequest(
    request_id="req_agent_session_400",
    task=TaskContext(
        task_id="task_repo_refactor",
        description="Autonomous multi-step codebase refactor",
        workload_hint="coding",
    ),
    request=OperationRequest(
        messages=[{"role": "user", "content": "Refactor database migrations"}],
    ),
)

init_result = client.execute(session_request)
exec_id = init_result.execution_id
print(f"Session started: {exec_id}")
```

### Step 2: Stream In-Flight Events from the Agent Loop

Inside your agent's execution loop, publish `ExecutionEvent` instances whenever tokens are spent, tools are invoked, or external web requests are made:

```python
from infuse.contracts.events import ExecutionEvent, EventType, EventSource

def on_agent_step_completed(exec_id: str, step_num: int, input_toks: int, output_toks: int):
    # Stream token telemetry
    client.events.publish(
        execution_id=exec_id,
        event=ExecutionEvent(
            event_id=f"evt_{exec_id}_step_{step_num}_tokens",
            execution_id=exec_id,
            type=EventType.TOKEN_OBSERVED,
            source=EventSource.AGENT,
            sequence=step_num * 2,
            payload={
                "input_tokens": input_toks,
                "output_tokens": output_toks,
                "cached_tokens": 0,
            },
        ),
    )

def on_tool_executed(exec_id: str, step_num: int, tool_name: str, duration_ms: float, success: bool):
    # Stream tool telemetry
    client.events.publish(
        execution_id=exec_id,
        event=ExecutionEvent(
            event_id=f"evt_{exec_id}_step_{step_num}_tool",
            execution_id=exec_id,
            type=EventType.TOOL_COMPLETED,
            source=EventSource.AGENT,
            sequence=step_num * 2 + 1,
            payload={
                "tool_name": tool_name,
                "duration_ms": duration_ms,
                "success": success,
            },
        ),
    )
```

### Step 3: Check Governor Decision Before Next Step

Before starting the next autonomous step, check the live Governor decision:

```python
def check_governance_posture(exec_id: str) -> bool:
    """Returns True if execution is permitted to continue, False if halted."""
    decision = client.governor.get_decision(exec_id)
    action = decision.action

    if action == "CONTINUE":
        return True
    elif action == "OPTIMIZE":
        print(f"[GOVERNOR] Optimization requested: {decision.reason}")
        # E.g. compress prompt context or reduce max_tokens
        return True
    elif action == "THROTTLE":
        delay_ms = decision.params.get("delay_ms", 1000)
        print(f"[GOVERNOR] Pacing execution, sleeping {delay_ms}ms: {decision.reason}")
        time.sleep(delay_ms / 1000.0)
        return True
    elif action == "SWITCH":
        new_model = decision.params.get("target_model", "gpt-4o-mini")
        print(f"[GOVERNOR] Switching provider to {new_model}: {decision.reason}")
        # Adjust agent's target model for subsequent steps
        return True
    elif action in ("STOP", "ESCALATE"):
        print(f"[GOVERNOR] HALT execution triggered ({action}): {decision.reason}")
        return False

    return True
```

---

## 3. Handling Control Actions

If an execution enters `RUNAWAY` or `PROVIDER_CONSTRAINED` state, the Governor or human operators can also dispatch physical control commands via the `ExecutionControlBoundary`:

```python
# Terminate a runaway session immediately
client.control.terminate(execution_id=exec_id, reason="Hard budget ceiling exceeded")

# Or pause for human review
client.control.throttle(execution_id=exec_id, delay_ms=5000)
```
