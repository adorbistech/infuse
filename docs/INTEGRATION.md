# INFUSE — Agent & Provider Integration Guide

This guide describes how to connect custom autonomous agent runtimes and AI model providers to **INFUSE (Execution Intelligence)**.

---

## 1. Integration Architecture

INFUSE follows the **"One Core, Many Adapters"** architectural design:

```text
┌─────────────────────────────────────────────────────────────┐
│                    Universal Core Engine                    │
│   (Contracts, Event Bus, Observers, State, Governor, CB)    │
└──────────────┬───────────────────────────────┬──────────────┘
               │                               │
               ▼                               ▼
┌─────────────────────────────┐ ┌─────────────────────────────┐
│    Universal Agent Adapter  │ │   Universal Provider Adapter│
│  (Claude, OpenCode, Codex)  │ │   (LiteLLM, OpenAI, Google) │
└─────────────────────────────┘ └─────────────────────────────┘
```

---

## 2. Implementing a Custom Agent Adapter

All agent adapters inherit from `BaseAgentAdapter` and implement the `IAgentAdapter` interface:

```python
from typing import Dict, Any, List
from infuse.agents.base import BaseAgentAdapter
from infuse.contracts.control import ControlCapability
from infuse.contracts.events import ExecutionEvent, EventType, EventSource
from infuse.contracts.execution import ExecutionRequest, NormalizedResponse

class MyCustomAgentAdapter(BaseAgentAdapter):
    """Custom adapter for proprietary agent framework."""

    def get_capabilities(self) -> ControlCapability:
        """Declare physical control capabilities supported by your agent runtime."""
        return ControlCapability(
            supports_cancel=True,
            supports_throttle=True,
            supports_next_step_switch=False,
            supports_terminate=True,
        )

    def execute_step(self, request: ExecutionRequest) -> NormalizedResponse:
        """Execute task step and stream events into the event bus."""
        # 1. Start step
        self.emit_event(
            EventType.EXECUTION_STARTED,
            {"task_id": request.task.task_id},
        )
        
        # 2. Invoke underlying model / tools
        response_text = self._run_agent_internal(request)
        
        # 3. Stream token facts
        self.emit_event(
            EventType.TOKEN_OBSERVED,
            {"input_tokens": 100, "output_tokens": 50},
        )
        
        return NormalizedResponse(
            content=response_text,
            role="assistant",
        )
```

---

## 3. Subprocess Transport Security Rules

When invoking agent CLI tools or external processes:
1. **Always use `shell=False`:** Never invoke shell interpreters directly to avoid command injection vulnerabilities.
2. **Use discrete argument lists:** Pass parameters as `List[str]`.
3. **Set execution timeouts:** Always bind subprocess invocations to explicit deadlines.
4. **Isolate credentials:** Never log or pass API keys as CLI argument flags; pass them via managed subprocess environment dictionaries.

---

## 4. Registering Adapters

Register custom adapters in the adapter registry during application startup:

```python
from infuse.providers.registry import ProviderRegistry
from infuse.agents.registry import AgentRegistry

# Register custom agent
AgentRegistry.register("my-custom-agent", MyCustomAgentAdapter)
```
