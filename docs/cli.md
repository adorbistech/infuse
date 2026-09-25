# INFUSE CLI Reference Guide (Block 29)

The **INFUSE Command-Line Interface (`infuse`)** provides a direct terminal and automation interface over the INFUSE Execution Intelligence platform. Built exclusively as a thin operational client over the frozen **Block 28 SDK**, the CLI maintains complete architectural boundary separation and does not duplicate core routing, governor decisions, policy evaluation, or agent lifecycle management.

---

## 1. Installation

Install INFUSE and its CLI via pip:

```bash
pip install infuse-ai
```

Or for development / editable installation:

```bash
pip install -e .
```

Verify installation:

```bash
infuse version
```

---

## 2. Invocation & Global Options

```bash
infuse [GLOBAL_OPTIONS] <command> [SUBCOMMAND] [ARGS...]
```

### Global Options

| Option | Environment Variable | Description |
|---|---|---|
| `-o, --output <text\|json>` | `INFUSE_OUTPUT_FORMAT` | Format output as plain text table or machine-readable JSON |
| `--json` | - | Shortcut for `--output json` |
| `--endpoint, --base-url <url>` | `INFUSE_BASE_URL` | INFUSE HTTP API Base URL (default: `http://localhost:8000`) |
| `--api-key <key>` | `INFUSE_API_KEY` | Authorization Bearer token or API key |
| `--timeout <seconds>` | `INFUSE_TIMEOUT_SECONDS`| Network request timeout (default: `30.0`s) |
| `--version` | - | Display version information and exit |
| `-h, --help` | - | Show help information |

---

## 3. Command Hierarchy

```text
infuse
├── version                           Display version & schema metadata
├── config (or info)                  Display active CLI/SDK configuration
├── execute                           Submit execution request
├── executions
│   ├── list                          List & filter execution history
│   ├── get <id>                      Retrieve execution summary
│   └── state <id>                    Inspect execution state
├── execution
│   ├── get <id>                      Retrieve execution summary
│   ├── state <id>                    Inspect execution state
│   └── result <id>                   Inspect execution result
├── state <id>                         Inspect execution state directly
├── governor <id>                      Inspect Governor regulation decision
├── events
│   ├── emit / publish <id>           Publish telemetry event
│   └── list <id>                     Inspect timeline events
├── policy
│   ├── list                          List all configured policies
│   ├── active                        Get currently active policy
│   ├── get [id]                      Get policy by ID (or active)
│   └── update / set <id>             Create or update policy revision
└── control
    ├── cancel <id>                   Request graceful cancellation
    ├── terminate <id>                Request hard termination
    ├── throttle <id>                 Request pacing / rate throttling
    └── switch <id>                   Request model / route switch
```

---

## 4. Configuration

Configuration resolution follows deterministic precedence:
1. **Explicit CLI Options** (`--endpoint`, `--api-key`, `--timeout`)
2. **Environment Variables** (`INFUSE_BASE_URL`, `INFUSE_API_KEY`, `INFUSE_TIMEOUT_SECONDS`)
3. **Default Values** (`http://localhost:8000`, 30s timeout)

To inspect active configuration:

```bash
infuse config
```

---

## 5. Authentication

Set the API key in your environment or pass via `--api-key`:

```bash
export INFUSE_API_KEY="infuse-prod-live-key-xyz"
infuse executions list
```

All credentials are automatically redacted in CLI output, error logs, and JSON payloads.

---

## 6. Execution Commands

Submit a single-shot or agent task execution:

```bash
# Basic task execution
infuse execute --task "Analyze git commit history" --provider mock --model mock-model

# Submit structured ExecutionRequest JSON file
infuse execute --file request.json --output json
```

---

## 7. Execution Inspection

Retrieve execution telemetry, status, and summaries:

```bash
# Get summary
infuse execution get exec_abc123

# List executions with filters & pagination
infuse executions list --state NORMAL --limit 20 --offset 0
```

---

## 8. State Inspection

Inspect the evaluated multi-dimensional state snapshot:

```bash
infuse state exec_abc123
```

Output displays the state (`NORMAL`, `COST_PRESSURE`, `RUNAWAY`, `QUALITY_DEGRADED`, `PROVIDER_CONSTRAINED`), threshold %, reason codes, and timestamp.

---

## 9. Events

Publish runtime telemetry events or inspect recorded events:

```bash
# Publish token observation event
infuse events emit exec_abc123 --type TOKEN_OBSERVED --payload '{"prompt_tokens": 120, "completion_tokens": 45}'

# Publish event from JSON envelope
infuse events publish exec_abc123 --file event_payload.json
```

---

## 10. Governance Policy Management

Inspect and update governance policies:

```bash
# List all policies
infuse policy list

# View active policy
infuse policy active

# Update policy from JSON file
infuse policy update pol_default --file policy_update.json
```

---

## 11. Governor Inspection

Inspect the active Governor posture, regulation decisions, and reason codes:

```bash
infuse governor exec_abc123
```

---

## 12. Execution Control Boundary

Dispatch operational control actions through the Execution Control Boundary:

```bash
# Graceful cancellation
infuse control cancel exec_abc123 --reason "User initiated abort" --yes

# Immediate hard termination
infuse control terminate exec_abc123 --reason "Runaway token surge detected" --yes

# Rate throttling
infuse control throttle exec_abc123 --delay-ms 2500 --yes

# Model switch
infuse control switch exec_abc123 --target-model fallback-model --yes
```

> **Safety Notice**: If an execution runtime does not support a requested control action, the CLI returns `ControlStatus.UNSUPPORTED` with exit code `5`.

---

## 13. Output Modes

### Human-Readable (Default)
Standard text tables and labeled fields designed for interactive terminal use.

### Machine-Readable JSON
Strict, machine-parsable JSON formatted on `stdout`:

```bash
infuse executions list --json | jq '.items[0].execution_id'
```

---

## 14. JSON Automation & Shell Scripting

In `--json` mode:
- Standard output contains **only** the valid JSON payload.
- Diagnostics and errors are written to `stderr`.

Example bash automation:

```bash
EXEC_ID=$(infuse execute --task "Process batch" --json | jq -r '.execution_id')
STATE=$(infuse state "$EXEC_ID" --json | jq -r '.state')

if [ "$STATE" = "RUNAWAY" ]; then
    infuse control terminate "$EXEC_ID" --yes
fi
```

---

## 15. Exit Codes Contract

Deterministic exit codes for CI/CD and pipeline monitoring:

| Exit Code | Constant | Meaning |
|---|---|---|
| `0` | `EXIT_SUCCESS` | Operation completed successfully |
| `1` | `EXIT_GENERIC_ERROR` | Unhandled or internal exception |
| `2` | `EXIT_USAGE_ERROR` / `EXIT_VALIDATION_ERROR` | Bad arguments, missing required flags, schema validation error |
| `3` | `EXIT_AUTHENTICATION_ERROR` | Missing, expired, or invalid API key / token |
| `4` | `EXIT_NOT_FOUND` | Target execution, policy, or resource not found |
| `5` | `EXIT_UNSUPPORTED` | Control operation not supported by runtime |
| `6` | `EXIT_CONTROL_ERROR` | Control operation failed or was rejected |
| `7` | `EXIT_TRANSPORT_ERROR` | Network connection refused, DNS error, transport failure |
| `8` | `EXIT_TIMEOUT` | Request timed out |
| `9` | `EXIT_SERVER_ERROR` | Internal server error (HTTP 500) |
| `10` | `EXIT_CONFLICT` | Resource conflict (HTTP 409) |
| `11` | `EXIT_MALFORMED_RESPONSE` | Non-decodable or schema-violating server response |

---

## 16. Error Handling

Errors output a clear message and code:
- Human mode: `Error [ERROR_CODE]: Error description` on `stderr`
- JSON mode: `{"error": "Error description", "code": "ERROR_CODE"}` on `stderr`

Tracebacks are suppressed by default in standard operation.

---

## 17. Security & Secret Redaction

The CLI automatically sanitizes all outputs:
- API keys matching `sk-...`, `infuse-...`, or `Bearer ...` patterns are masked as `[REDACTED]`.
- Configuration displays report `[CONFIGURED]` or `[NONE]` without revealing the secret value.

---

## 18. CI / Automation Examples

### GitHub Actions Step Example

```yaml
- name: Run Governed Agent Task
  env:
    INFUSE_BASE_URL: ${{ secrets.INFUSE_API_URL }}
    INFUSE_API_KEY: ${{ secrets.INFUSE_API_KEY }}
  run: |
    infuse execute --task "Deploy staging verification" --agent CI-Runner --json > result.json
    cat result.json
```
