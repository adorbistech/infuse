# INFUSE Public ChatGPT Plugin Architecture

## 1. Architectural Overview

The **INFUSE Public Plugin Integration** connects OpenAI applications (ChatGPT, Codex, and OpenAI Custom Workflows) to the INFUSE Execution Intelligence platform. 

The public directory submission model is centered on **Remote MCP (Model Context Protocol)** operating over **Streamable HTTP** (`/mcp`), with **Custom GPT Actions (OpenAPI 3.1)** supported as a secondary compatibility layer.

```
┌─────────────────────────────────────────────────────────────┐
│                      OpenAI Ecosystem                       │
│  ┌───────────────────────┐       ┌───────────────────────┐  │
│  │   ChatGPT / Codex     │       │   Custom GPTs / UI    │  │
│  │ (Remote MCP Client)   │       │   (OpenAPI Actions)   │  │
│  └──────────┬────────────┘       └──────────┬────────────┘  │
└─────────────┼───────────────────────────────┼───────────────┘
              │ JSON-RPC 2.0 (Streamable HTTP)│ HTTPS REST
              ▼                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 INFUSE Production Gateway                   │
│                                                             │
│   /.well-known/openai-apps-challenge (Domain Verification)  │
│   /mcp                               (Streamable HTTP MCP)  │
│   /chatgpt/v1/*                      (OpenAPI REST Actions) │
│   /v1/*                              (Core API)             │
│   /health & /ready                   (Deployment Probes)    │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│               INFUSE Core Invariant Boundary                │
│                                                             │
│   ┌─────────────────────────────────────────────────────┐   │
│   │               Execution Control Boundary            │   │
│   └──────────────────────────┬──────────────────────────┘   │
│                              ▼                              │
│   ┌─────────────────────────────────────────────────────┐   │
│   │                 The Governor Core                   │   │
│   │      (Observe → Understand → Regulate Loop)         │   │
│   └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Remote MCP as Primary Integration Model

OpenAI's public plugin directory is architected around remote MCP servers. Under this architecture:
1. **Public MCP Endpoint**: Served at `https://<infuse-host>/mcp`.
2. **Streamable HTTP Transport**: Implements the `2024-11-05` MCP specification with bi-directional streaming over standard HTTPS POST/SSE channels.
3. **Tool Annotations**: Every exposed tool includes formal annotations:
   - `readOnlyHint`: Boolean flag identifying pure inspection operations.
   - `destructiveHint`: Boolean flag identifying state-mutating or disruptive control actions (e.g. `infuse_control`).
   - `openWorldHint`: Boolean flag set to `false` for all INFUSE deterministic governance tools.
4. **Session Management**: Session tokens are transmitted via the `mcp-session-id` header to enable stateful task tracking across multi-turn ChatGPT interactions.

---

## 3. Coexistence of MCP and OpenAPI Adapters

INFUSE strictly adheres to the architectural invariant: **One Core, Many Adapters**.

| Dimension | Remote MCP (`/mcp`) | OpenAPI Actions (`/chatgpt/v1`) |
| :--- | :--- | :--- |
| **Primary Target** | OpenAI Public Directory / ChatGPT / Codex | Custom GPTs & Enterprise REST Workflows |
| **Protocol** | JSON-RPC 2.0 over Streamable HTTP | REST / JSON (OpenAPI 3.1) |
| **Streaming** | Native SSE & chunked event responses | Server-Sent Events / Standard HTTP |
| **Discovery** | `tools/list` protocol handshake | `GET /chatgpt/openapi.json` |
| **Tool Annotations** | Typed `ToolAnnotations` object | OpenAPI `x-openai-isConsequential` |
| **Core Target** | INFUSE Python SDK / Execution Boundary | INFUSE Core Services via SDK |

Neither adapter bypasses the core Governor or the Execution Control Boundary.

---

## 4. Multi-Tenant Isolation Model

INFUSE enforces strict multi-tenant isolation across all MCP sessions:
- **Tenant Context**: Every MCP session is bound to an authenticated tenant execution context.
- **Trajectory Isolation**: Execution IDs, event streams, and policy configurations belonging to Tenant A cannot be observed or modified by Tenant B.
- **Sandboxed Execution Control**: Dispatching control actions via `infuse_control` verifies executor registration strictly against the requesting tenant's execution scope.
