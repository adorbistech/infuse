# INFUSE ChatGPT Tool Catalog

Complete reference for the 10 curated tools exposed to OpenAI ChatGPT Custom Actions.

---

## 1. `get_system_info`

- **HTTP Route**: `GET /chatgpt/v1/system`
- **Operation ID**: `getSystemInfo`
- **Category**: `READ`
- **Required Scope**: `read:executions`
- **Description**: Inspect INFUSE runtime metadata, schema version, active policy identifier, registered providers, registered agents, and canonical state/action vocabularies.

### Input Parameters
*None*

### Sample Response Data
```json
{
  "name": "INFUSE — Execution Intelligence",
  "version": "0.1.0",
  "schema_version": "1.0.0",
  "status": "HEALTHY",
  "active_policy": "pol_default",
  "registered_providers": ["Anthropic", "OpenAI", "Gemini", "DeepSeek", "LiteLLM"],
  "registered_agents": ["Claude Code", "OpenCode", "Codex", "Hermes", "OpenClaw", "Lovable"],
  "canonical_states": ["NORMAL", "COST_PRESSURE", "RUNAWAY", "QUALITY_DEGRADED", "PROVIDER_CONSTRAINED"],
  "canonical_actions": ["CONTINUE", "OPTIMIZE", "ESCALATE", "DOWNGRADE", "SWITCH", "THROTTLE", "STOP"]
}
```

---

## 2. `list_executions`

- **HTTP Route**: `GET /chatgpt/v1/executions`
- **Operation ID**: `listExecutions`
- **Category**: `READ`
- **Required Scope**: `read:executions`
- **Description**: Query and list execution records scoped to caller's tenant with optional filters.

### Input Parameters (Query String)
| Parameter | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `query` | `string` | No | `null` | Free-text search matching task descriptions or IDs. |
| `state` | `string` | No | `null` | Filter by canonical state (`NORMAL`, `COST_PRESSURE`, `RUNAWAY`, etc.). |
| `agent` | `string` | No | `null` | Filter by agent name (e.g. `Claude Code`, `OpenCode`). |
| `limit` | `integer` | No | `20` | Max executions to return (1–100). |
| `offset` | `integer` | No | `0` | Pagination offset. |

---

## 3. `get_execution_state`

- **HTTP Route**: `GET /chatgpt/v1/executions/{execution_id}/state`
- **Operation ID**: `getExecutionState`
- **Category**: `ANALYZE`
- **Required Scope**: `read:executions`
- **Description**: Inspect the current evaluated state, anomaly indicators, and threshold consumption.

### Path Parameters
| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `execution_id` | `string` | Yes | The execution identifier (e.g. `exec_8548d99b`). |

---

## 4. `get_execution_result`

- **HTTP Route**: `GET /chatgpt/v1/executions/{execution_id}/result`
- **Operation ID**: `getExecutionResult`
- **Category**: `READ`
- **Required Scope**: `read:executions`
- **Description**: Retrieve execution completion status, response messages, token counts, and cost breakdown.

### Path Parameters
| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `execution_id` | `string` | Yes | The execution identifier. |

---

## 5. `inspect_execution`

- **HTTP Route**: `GET /chatgpt/v1/executions/{execution_id}/inspect`
- **Operation ID**: `inspectExecution`
- **Category**: `ANALYZE`
- **Required Scope**: `read:executions`
- **Description**: Comprehensive inspection combining summary, state evaluation, governor verdict, and health diagnostics.

### Path Parameters
| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `execution_id` | `string` | Yes | The execution identifier. |

---

## 6. `inspect_governor_decision`

- **HTTP Route**: `GET /chatgpt/v1/executions/{execution_id}/governor`
- **Operation ID**: `inspectGovernorDecision`
- **Category**: `ANALYZE`
- **Required Scope**: `read:executions`
- **Description**: Read the Governor's regulation decision, machine-readable reason codes, and proposed routing changes.

### Path Parameters
| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `execution_id` | `string` | Yes | The execution identifier. |

---

## 7. `get_provider_health`

- **HTTP Route**: `GET /chatgpt/v1/providers/health`
- **Operation ID**: `getProviderHealth`
- **Category**: `READ`
- **Required Scope**: `read:executions`
- **Description**: Report real-time health matrix, latencies, and error rates across AI providers.

### Input Parameters
*None*

---

## 8. `list_policies`

- **HTTP Route**: `GET /chatgpt/v1/policies`
- **Operation ID**: `listPolicies`
- **Category**: `READ`
- **Required Scope**: `read:policies`
- **Description**: List available governance policies and identify the active policy.

### Input Parameters
*None*

---

## 9. `get_policy`

- **HTTP Route**: `GET /chatgpt/v1/policies/{policy_id}`
- **Operation ID**: `getPolicy`
- **Category**: `READ`
- **Required Scope**: `read:policies`
- **Description**: Retrieve 10-dimensional configuration limits for a specific policy (or active policy if omitted).

### Path Parameters
| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `policy_id` | `string` | No | Specific policy ID (e.g. `pol_default`). |

---

## 10. `execute_task`

- **HTTP Route**: `POST /chatgpt/v1/execute`
- **Operation ID**: `executeTask`
- **Category**: `EXECUTE`
- **Required Scope**: `execute:tasks`
- **Description**: Submit a task for governed AI agent execution under active INFUSE policies.

### Request Body (JSON)
| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `task_description` | `string` | Yes | Goal or description of the task. |
| `prompt` | `string` | No | User prompt content (defaults to `task_description`). |
| `workload_hint` | `string` | No | Workload classification hint (e.g. `coding`, `analysis`). |
| `preferred_provider` | `string` | No | Provider hint (e.g. `Anthropic`, `OpenAI`, `Gemini`). |
| `preferred_model` | `string` | No | Model hint (e.g. `claude-3-7-sonnet`, `gpt-4o`). |
| `temperature` | `number` | No | Sampling temperature (0.0 to 2.0). |

---

## Governed Control: `control_execution`

- **HTTP Route**: `POST /chatgpt/v1/control`
- **Operation ID**: `controlExecution`
- **Category**: `CONTROL`
- **Required Scope**: `control:write`
- **Description**: Dispatch governed control action strictly through Execution Control Boundary.

### Request Body (JSON)
| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `execution_id` | `string` | Yes | Target execution ID to regulate. |
| `action` | `string` | Yes | Canonical action (`STOP`, `THROTTLE`, `SWITCH`, `CONTINUE`). |
| `reason` | `string` | No | Human-readable justification. |
| `delay_ms` | `integer` | No | Delay in milliseconds if action is `THROTTLE`. |
| `target_model` | `string` | No | Target model if action is `SWITCH`. |
