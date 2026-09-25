# OpenAI Public Plugin Directory Submission Requirements

## 1. Directory Overview & Modern Standards

The OpenAI Public Plugin Directory serves as the central discovery index for ChatGPT, Codex, and enterprise AI workspaces. Under the current specification:
1. **Primary Protocol**: Remote MCP (Model Context Protocol) over Streamable HTTP (`/mcp`).
2. **Protocol Version**: JSON-RPC 2.0 complying with `2024-11-05`.
3. **Transport**: Public HTTPS endpoint supporting streaming and bi-directional session tracking.
4. **Domain Verification**: Valid domain challenge served at `/.well-known/openai-apps-challenge`.
5. **Tool Annotations**: Fully typed tool safety hints (`readOnlyHint`, `destructiveHint`, `openWorldHint`).

---

## 2. Directory Listing Metadata

| Field | Value / Implementation |
| :--- | :--- |
| **App / Plugin Name** | INFUSE — Execution Intelligence |
| **Short Description** | Real-time voltage regulator and execution governance for autonomous AI agents. |
| **Detailed Description** | INFUSE monitors and governs AI execution streams in real-time. It inspects token velocity, tracks live costs, enforces budget safety limits, detects runaway loops, and dispatches deterministic Governor control actions (STOP, THROTTLE, SWITCH, CONTINUE) via the Execution Control Boundary. |
| **Developer / Org** | Adorbis Technologies |
| **Website** | https://github.com/adorbistech/infuse |
| **Privacy Policy URL** | https://github.com/adorbistech/infuse/blob/main/PRIVACY.md |
| **Terms of Service URL** | https://github.com/adorbistech/infuse/blob/main/TERMS.md |
| **Support URL** | https://github.com/adorbistech/infuse/issues |
| **Icon URL** | https://raw.githubusercontent.com/adorbistech/infuse/main/assets/infuse-logo.svg |
| **Primary Endpoint** | `https://api.infuse.adorbis.com/mcp` |

---

## 3. Tool Annotations Breakdown

Every tool exposed to the OpenAI directory provides explicit hints to the model:

```json
{
  "name": "infuse_control",
  "description": "Dispatch an operational control command (STOP, THROTTLE, SWITCH, CONTINUE) to an active execution strictly through the Execution Control Boundary.",
  "annotations": {
    "readOnlyHint": false,
    "destructiveHint": true,
    "openWorldHint": false
  }
}
```

- **`readOnlyHint`**: Set to `true` on 8 inspection tools (`infuse_get_execution`, `infuse_get_execution_state`, `infuse_get_execution_result`, `infuse_list_executions`, `infuse_list_events`, `infuse_get_policy`, `infuse_list_policies`, `infuse_get_governor_decision`). Prevents ChatGPT from prompting for confirmation on safe read operations.
- **`destructiveHint`**: Set to `true` exclusively on `infuse_control`. Informs ChatGPT that this tool dispatches operational state changes (e.g. terminating or throttling an active agent run), prompting appropriate user confirmation when required.
- **`openWorldHint`**: Set to `false` across all 12 tools. Ensures ChatGPT understands these tools interact strictly with deterministic INFUSE internal infrastructure rather than arbitrary external web resources.

---

## 4. Required Attestations

Before public directory submission:
1. **Safety**: All control interventions are mediated by the Governor and the Execution Control Boundary. No arbitrary shell execution or direct process tampering is permitted.
2. **Secret Redaction**: All API keys and credentials in execution payloads, errors, and logs are automatically sanitized with `[REDACTED]` prior to response generation.
3. **Availability & Uptime**: The production server implements `/health` (liveness) and `/ready` (dependency readiness) probes with automatic graceful shutdown and signal handling.
