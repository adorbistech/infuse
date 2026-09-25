# INFUSE — Model Context Protocol (MCP) Server (Block 30)

## 1. Purpose
The INFUSE MCP Server exposes the full suite of INFUSE execution intelligence, telemetry, state inspection, policy governance, and control capabilities to MCP-compliant AI agents and environments (e.g. Claude Desktop, Cursor, Windsurf, custom MCP hosts).

The MCP Server is a **thin protocol adapter** that operates strictly on top of the frozen **Block 28 SDK**.

---

## 2. Architecture

```text
  MCP Host / Agent (e.g., Claude Desktop, Cursor)
                     │  (Model Context Protocol over stdio/HTTP)
                     ▼
           INFUSE MCP Server (Block 30)
                     │
                     ▼
             Block 28 SDK (InfuseClient)
                     │
                     ▼
       Universal HTTP API / INFUSE Core
```

### Architectural Invariants:
- **One Core, Many Interfaces**: The MCP server does not duplicate routing, governor evaluation, economics, state transitions, or lifecycle management.
- **SDK Delegation**: All operations map 1:1 into typed `InfuseClient` SDK calls.
- **Authoritative Control Boundary**: Control dispatches route strictly through `client.control.dispatch(...)` into the `ExecutionControlBoundary`.
- **Zero Agent/Provider Execution in MCP**: The server never spawns agent subprocesses or calls provider APIs directly.

---

## 3. MCP Compatibility
- **Protocol Version**: Model Context Protocol (MCP) v1.0.0+ specification compliant.
- **Standard SDK**: Implemented using official `mcp.server.fastmcp.FastMCP`.
- **Capabilities**:
  - `tools`: Full execution, telemetry, policy, governor, and control tool surface.
  - `resources`: Read-only contextual URIs for executions, state snapshots, policies, and governor postures.

---

## 4. Installation
Install the INFUSE package with MCP capabilities:
```bash
pip install -e .
```
This registers the `infuse-mcp` console command.

---

## 5. Server Startup
Launch the MCP server directly in `stdio` mode (default):
```bash
infuse-mcp
```

Or pass explicit flags:
```bash
infuse-mcp --endpoint http://localhost:8000 --transport stdio --log-level INFO
```

---

## 6. Transport
The INFUSE MCP Server supports:
1. **`stdio`** (Default): High-performance standard input/output JSON-RPC stream for local host integrations.
2. **`streamable_http` / `sse`**: Server-Sent Events / HTTP transport for remote microservice setups.

---

## 7. Configuration
Configuration can be supplied via environment variables or CLI arguments:

| Configuration | Environment Variable | CLI Flag | Default |
|---|---|---|---|
| Server Name | `INFUSE_MCP_SERVER_NAME` | N/A | `infuse` |
| Core API URL | `INFUSE_BASE_URL` | `--endpoint` / `--base-url` | `http://localhost:8000` |
| API Key | `INFUSE_API_KEY` | `--api-key` | `None` |
| Timeout (s) | `INFUSE_TIMEOUT_SECONDS` | `--timeout` | `30.0` |
| Transport | `INFUSE_MCP_TRANSPORT` | `--transport` | `stdio` |
| Log Level | `INFUSE_LOG_LEVEL` | `--log-level` | `INFO` |

---

## 8. Authentication
Provide credentials via `INFUSE_API_KEY` or `--api-key`. All authorization headers and tokens are securely forwarded to the INFUSE Core via the SDK. Secrets are strictly redacted in error outputs and tool responses.

---

## 9. Available Tools

| Tool Name | Purpose | Key Arguments |
|---|---|---|
| `infuse_execute` | Submit governed execution task | `task_description`, `prompt`, `provider`, `model`, `agent_name`, `request_json` |
| `infuse_get_execution` | Retrieve execution telemetry summary | `execution_id` |
| `infuse_get_execution_state` | Retrieve evaluated execution state & reason codes | `execution_id` |
| `infuse_get_execution_result` | Retrieve full canonical ExecutionResult | `execution_id` |
| `infuse_list_executions` | Search & list execution history | `query`, `state`, `agent`, `limit`, `offset` |
| `infuse_list_events` | List timeline events for execution | `execution_id` |
| `infuse_publish_event` | Ingest Block 14 telemetry event | `execution_id`, `event_type`, `source`, `payload`, `sequence` |
| `infuse_get_policy` | Get active or specific governance policy | `policy_id` (optional) |
| `infuse_list_policies` | List all configured policies | None |
| `infuse_update_policy` | Create or update governance policy | `policy_id`, `policy_data` |
| `infuse_get_governor_decision` | Inspect Governor regulation decision | `execution_id` |
| `infuse_control` | Dispatch operational control command | `execution_id`, `action` (`STOP`, `THROTTLE`, `SWITCH`, `CONTINUE`), `params` |

---

## 10. Available Resources

| Resource URI | Description | MIME Type |
|---|---|---|
| `infuse://executions/{execution_id}` | Real-time execution summary snapshot | `application/json` |
| `infuse://executions/{execution_id}/state` | Real-time execution state evaluation | `application/json` |
| `infuse://executions/{execution_id}/result` | Full canonical execution result | `application/json` |
| `infuse://policies/active` | Active governance policy rules | `application/json` |
| `infuse://governor/{execution_id}` | Evaluated Governor posture | `application/json` |

---

## 11. Execution Examples

### MCP Tool Call: `infuse_execute`
```json
{
  "task_description": "Analyze repository security dependencies",
  "prompt": "Scan pyproject.toml and report vulnerabilities",
  "provider": "mock",
  "model": "gpt-4o",
  "agent_name": "SecurityAgent"
}
```

### Result:
```json
{
  "execution_id": "exec_987654",
  "status": "COMPLETED",
  "response": {
    "content": "Analysis complete: 0 vulnerabilities found.",
    "role": "assistant"
  },
  "execution": {
    "provider": "mock",
    "model": "gpt-4o",
    "tokens_total": 450,
    "cost_usd": 0.0045,
    "latency_ms": 320.0
  },
  "decision": {
    "action": "CONTINUE",
    "reason_codes": []
  }
}
```

---

## 12. State Examples

### MCP Tool Call: `infuse_get_execution_state`
```json
{
  "execution_id": "exec_987654"
}
```

### Result:
```json
{
  "execution_id": "exec_987654",
  "state": "NORMAL",
  "boundary_threshold_percent": 100.0,
  "reason_codes": ["HEALTHY"],
  "evaluated_at": "2026-09-25T16:20:00Z"
}
```

---

## 13. Event Examples

### MCP Tool Call: `infuse_publish_event`
```json
{
  "execution_id": "exec_987654",
  "event_type": "TOKEN_OBSERVED",
  "source": "AGENT",
  "payload": {
    "tokens": 120,
    "step": 3
  },
  "sequence": 3
}
```

---

## 14. Policy Examples

### MCP Tool Call: `infuse_get_policy`
```json
{
  "policy_id": "pol_default"
}
```

### Result:
```json
{
  "policy_id": "pol_default",
  "name": "Standard Production Policy",
  "version": "1.0.0",
  "is_active": true,
  "budget": {
    "max_cost_per_task": 5.0,
    "currency": "USD"
  }
}
```

---

## 15. Governor Inspection

### MCP Tool Call: `infuse_get_governor_decision`
```json
{
  "execution_id": "exec_987654"
}
```

### Result:
```json
{
  "execution_id": "exec_987654",
  "action": "CONTINUE",
  "action_banner_title": "Execution Nominal",
  "action_banner_description": "All constraints within established boundaries.",
  "reason_codes": []
}
```

---

## 16. Control Operations

### MCP Tool Call: `infuse_control`
```json
{
  "execution_id": "exec_987654",
  "action": "STOP",
  "params": {
    "hard": false,
    "reason": "Operator requested pause"
  }
}
```

### Result:
```json
{
  "operation_id": "ctrl_op_exec_987654_1",
  "execution_id": "exec_987654",
  "action": "STOP",
  "status": "COMPLETED",
  "message": "Control applied successfully"
}
```

---

## 17. Error Handling
Errors returned to MCP clients are normalized into machine-readable structures:
```json
{
  "error": true,
  "code": "NOT_FOUND",
  "message": "Execution 'exec_missing' not found.",
  "exception_type": "NotFoundError",
  "status_code": 404
}
```

Standard Error Codes:
- `VALIDATION_ERROR`
- `AUTHENTICATION_ERROR`
- `NOT_FOUND`
- `UNSUPPORTED_OPERATION`
- `CONTROL_FAILURE`
- `TRANSPORT_ERROR`
- `TIMEOUT_ERROR`
- `SERVER_ERROR`
- `CONFLICT_ERROR`
- `MALFORMED_RESPONSE`
- `INVALID_ARGUMENT`

---

## 18. Security
- **No Hard-Coded Credentials**: All tokens and keys must be passed dynamically via config or environment.
- **Redaction Engine**: Secrets and bearer tokens are automatically sanitized from all error messages and responses.

---

## 19. Logging
- **Stream Isolation**: All diagnostic log messages are written strictly to `sys.stderr`.
- `sys.stdout` is exclusively reserved for valid JSON-RPC MCP protocol packets in stdio mode.

---

## 20. Client Integration
To configure Claude Desktop or another MCP host to use INFUSE MCP:

```json
{
  "mcpServers": {
    "infuse": {
      "command": "infuse-mcp",
      "args": [
        "--endpoint", "http://localhost:8000"
      ],
      "env": {
        "INFUSE_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

---

## 21. Versioning
- **MCP Server Version**: Aligned with INFUSE package version (`0.1.0`).
- **Contract Schema Version**: `1.0.0`.

---

## 22. Limitations & Reference Transport
The MCP server communicates with INFUSE Core via HTTP or in-memory `ReferenceTransport` during automated testing. Live provider or agent execution is governed by the core service.
