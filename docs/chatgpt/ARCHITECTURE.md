# INFUSE ChatGPT App Integration Architecture

## Architectural Principles & Invariants

The INFUSE system is architected around a strict principle:

> **ONE CORE, ONE GOVERNOR, ONE CONTROL BOUNDARY, MANY INTERFACES, MANY ADAPTERS**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SURFACE ADAPTER LAYER                             │
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │ HTTP REST    │  │ Python SDK   │  │ MCP Server   │  │ ChatGPT App     │  │
│  │ (Starlette)  │  │ (Typed Sync) │  │ (ModelContext│  │ (OpenAPI / GPT) │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └────────┬────────┘  │
└─────────┼─────────────────┼─────────────────┼───────────────────┼───────────┘
          │                 │                 │                   │
          ▼                 ▼                 ▼                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         INFUSE UNIVERSAL CORE (SDK)                         │
│                                                                             │
│  ┌───────────────────────┐   dispatches    ┌─────────────────────────────┐  │
│  │ Execution Client      │ ──────────────> │ Telemetry & Event Ingestion │  │
│  └───────────────────────┘                 └──────────────┬──────────────┘  │
│                                                           │                 │
│                                                           ▼ signals         │
│  ┌───────────────────────┐   evaluates     ┌─────────────────────────────┐  │
│  │ Policy Engine         │ <────────────── │ Execution State Observer    │  │
│  │ (10 Policy Sections)  │                 │ (5 Canonical States)        │  │
│  └──────────┬────────────┘                 └──────────────┬──────────────┘  │
│             │                                             │                 │
│             ▼ policies                                    ▼ state signals   │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                     THE GOVERNOR (Sole Authority)                     │  │
│  │                      (7 Canonical Action Decisions)                   │  │
│  └──────────────────────────────────┬────────────────────────────────────┘  │
│                                     │ decisions                             │
│                                     ▼                                       │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                 EXECUTION CONTROL BOUNDARY (ECB)                      │  │
│  │             (Enforces: CONTINUE, THROTTLE, SWITCH, STOP)              │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 1. Zero Logic Duplication

The ChatGPT App integration (`infuse.chatgpt`) is strictly an adapter module. It conforms to the following non-negotiable boundaries:

1. **No Shadow State Machine**: ChatGPT endpoints query the core State Engine; they do not compute or invent synthetic execution states.
2. **No Shadow Pricing Engine**: Token prices, currency conversion, and cost thresholds are read exclusively from the core contracts.
3. **No Shadow Policy Engine**: Policies are defined and parsed through `GovernancePolicy` contracts; the ChatGPT layer cannot alter policy evaluation mechanics.
4. **No Shadow Control Executor**: Governed actions (`STOP`, `THROTTLE`, `SWITCH`, etc.) are dispatched strictly through `ExecutionControlBoundary`.

---

## 2. Authentication & Tenant Isolation Pipeline

Incoming HTTP requests from OpenAI ChatGPT pass through a multi-stage gateway before hitting the SDK:

```
ChatGPT Request
       │
       ▼
[ Authorization Header Extraction ]
       │
       ├─► Missing Token ───────► 401 Unauthorized
       │
       ├─► Invalid Token ───────► 401 Unauthorized
       │
       ▼
[ Token Context Derivation ]
       ├─► tenant_id
       ├─► user_id
       └─► granted_scopes
       │
       ▼
[ RBAC / Scope Enforcement ]
       ├─► Lacks Required Scope ─► 403 Forbidden
       │
       ▼
[ Tenant-Scoped Tool Dispatch ]
       ├─► Isolates Execution Histories
       └─► Tags Outgoing Task Executions
       │
       ▼
[ Response Formatting & Card Synthesis ]
       │
       ▼
200 OK JSONResponse (Standardized ToolResponseEnvelope)
```

---

## 3. Package Structure

The ChatGPT integration is isolated within `infuse/chatgpt/`:

- `infuse/chatgpt/__init__.py`: Package entry point and public exports.
- `infuse/chatgpt/config.py`: Configuration dataclass with environment parsing (`ChatGptAppConfig`).
- `infuse/chatgpt/auth.py`: Authentication, token parsing, and tenant isolation service (`ChatGptAuthService`).
- `infuse/chatgpt/models.py`: Pydantic input models and standard response envelope (`ToolResponseEnvelope`).
- `infuse/chatgpt/ui.py`: Presentation models and UI card formatters for ChatGPT canvas.
- `infuse/chatgpt/tools.py`: Tool registry and dispatchers (`ChatGptToolRegistry`).
- `infuse/chatgpt/schema.py`: OpenAPI 3.1.0 schema generator (`generate_openapi_schema`).
- `infuse/chatgpt/router.py`: Starlette ASGI router hosting `/chatgpt/openapi.json` and Action endpoints.
