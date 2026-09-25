# OpenAI Custom GPT Integration Reference

Technical reference for integrating **INFUSE — Execution Intelligence** into ChatGPT Custom GPT Actions.

---

## Architecture Overview

Custom GPT Actions enable ChatGPT to interact with external APIs using standard OpenAPI specifications. When a user asks ChatGPT a question or requests an action involving INFUSE, the ChatGPT model formulates a structured HTTP REST request according to the generated OpenAPI schema, receives the structured JSON response, and renders the result.

```
┌──────────────────┐               ┌──────────────────┐               ┌──────────────────┐
│   ChatGPT User   │ <─ Natural ─> │     ChatGPT      │ <─ OpenAPI ─> │  INFUSE ChatGPT  │
│    Interface     │    Language   │    Model (LLM)   │    Actions    │  Adapter Layer   │
└──────────────────┘               └──────────────────┘               └────────┬─────────┘
                                                                               │
                                                                               ▼
                                                                      ┌──────────────────┐
                                                                      │  INFUSE Core SDK │
                                                                      │ & Governor Plane │
                                                                      └──────────────────┘
```

---

## OpenAPI Specification Endpoint

INFUSE dynamically serves an OpenAPI 3.1.0 compliant specification directly at:

```
GET /chatgpt/openapi.json
```

### Schema Features

1. **Explicit Type Definitions**: Fully typed parameters, query parameters, request bodies, and responses generated from Pydantic v2 contracts.
2. **Deterministic Enums**:
   - `Canonical States`: `NORMAL`, `COST_PRESSURE`, `RUNAWAY`, `QUALITY_DEGRADED`, `PROVIDER_CONSTRAINED`
   - `Governor Actions`: `CONTINUE`, `OPTIMIZE`, `ESCALATE`, `DOWNGRADE`, `SWITCH`, `THROTTLE`, `STOP`
3. **Conforming Operation IDs**: Unique and semantic `operationId` tags (`getSystemInfo`, `listExecutions`, `getExecutionState`, `getExecutionResult`, `inspectExecution`, `inspectGovernorDecision`, `getProviderHealth`, `listPolicies`, `getPolicy`, `executeTask`, `controlExecution`).
4. **Rich Descriptions**: Detailed semantic descriptions on every parameter to guide the ChatGPT model's function-calling planner.

---

## Action Routing Table

| Tool Name | HTTP Method | Path | Category | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| `get_system_info` | `GET` | `/chatgpt/v1/system` | READ | Version, schema, supported agents & models. |
| `list_executions` | `GET` | `/chatgpt/v1/executions` | READ | Paginated execution history with state/agent filters. |
| `get_execution_state` | `GET` | `/chatgpt/v1/executions/{execution_id}/state` | ANALYZE | Current canonical health state & anomaly reason codes. |
| `get_execution_result` | `GET` | `/chatgpt/v1/executions/{execution_id}/result` | READ | Execution status, output message, token breakdown & cost. |
| `inspect_execution` | `GET` | `/chatgpt/v1/executions/{execution_id}/inspect` | ANALYZE | Comprehensive multi-system diagnostic inspection. |
| `inspect_governor_decision` | `GET` | `/chatgpt/v1/executions/{execution_id}/governor` | ANALYZE | Governor regulatory verdict and rationale. |
| `get_provider_health` | `GET` | `/chatgpt/v1/providers/health` | READ | Multi-provider latency and error rate telemetry. |
| `list_policies` | `GET` | `/chatgpt/v1/policies` | READ | List available and active governance policies. |
| `get_policy` | `GET` | `/chatgpt/v1/policies/{policy_id}` | READ | Detailed policy configuration & thresholds. |
| `execute_task` | `POST` | `/chatgpt/v1/execute` | EXECUTE | Submit governed task to multi-provider routing matrix. |
| `control_execution` | `POST` | `/chatgpt/v1/control` | CONTROL | Dispatch Governor regulatory action to live execution. |

---

## Response Envelope Format

All ChatGPT Action endpoints return a standardized, predictable `ToolResponseEnvelope`:

```json
{
  "success": true,
  "tool_name": "inspect_execution",
  "category": "ANALYZE",
  "data": {
    "execution_id": "exec_8548d99b",
    "summary": { ... },
    "state_evaluation": { ... },
    "governor_decision": { ... }
  },
  "error": null,
  "error_code": null,
  "ui_card": {
    "type": "infuse_execution_card",
    "version": "1.0",
    "execution_id": "exec_8548d99b",
    "status": "COMPLETED",
    "tokens": 36,
    "cost_usd": 0.0002
  }
}
```

### Error Envelope Example

```json
{
  "success": false,
  "tool_name": "get_execution_result",
  "category": "READ",
  "data": null,
  "error": "Execution 'exec_nonexistent' not found.",
  "error_code": "NOT_FOUND",
  "ui_card": null
}
```

---

## Custom GPT Configuration Guide

### System Instructions Template

Paste the following into the **Instructions** section of your Custom GPT:

```text
You are the official INFUSE Execution Intelligence Assistant.
INFUSE is a universal execution intelligence platform and real-time voltage regulator for AI agents.

When interacting with the user:
1. Always use the available INFUSE Actions to inspect, analyze, or execute tasks.
2. When summarizing executions, always highlight:
   - Execution State (NORMAL, COST_PRESSURE, RUNAWAY, QUALITY_DEGRADED, PROVIDER_CONSTRAINED)
   - Governor Action & Rationale
   - Cost in USD and Token Usage
   - Provider and Model used
3. When abnormal conditions occur (COST_PRESSURE or RUNAWAY), recommend appropriate Governor interventions (e.g., THROTTLE or SWITCH).
4. For dangerous actions like STOP, explain the consequences clearly to the user before confirming.
```
