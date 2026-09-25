# INFUSE ChatGPT App Integration

Official OpenAI Custom GPT & ChatGPT App integration for **INFUSE — Execution Intelligence**.

---

## Overview

The **INFUSE ChatGPT App & Remote MCP Plugin** connects OpenAI ChatGPT, Codex, and OpenAI Custom Workflows directly to the INFUSE runtime, allowing users and autonomous workflows to monitor, inspect, and execute governed AI operations.

### Two Submission & Integration Surfaces

1. **Remote MCP Server (`/mcp`) — Primary Public Directory Model**:
   - Streamable HTTP (JSON-RPC 2.0, specification `2024-11-05`) on `/mcp`.
   - 12 Authoritative Tools with OpenAI `ToolAnnotations` (`readOnlyHint`, `destructiveHint`, `openWorldHint`).
   - Domain challenge verification at `/.well-known/openai-apps-challenge`.
   - Direct integration with ChatGPT and Codex.

2. **OpenAPI 3.1 Custom Actions (`/chatgpt/v1`) — Secondary Compatibility Model**:
   - REST endpoints with OpenAPI 3.1.0 schema at `/chatgpt/openapi.json`.
   - 10 Curated Action tools for Custom GPTs and manual action builders.

### Architectural Principle: *One Core, Many Adapters*

```
┌─────────────────────────────────────────────────────────────┐
│                    INTERACTION SURFACES                     │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌─────────────┐  │
│  │ HTTP REST │ │ PythonSDK │ │ RemoteMCP │ │ ChatGPT App │  │
│  └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └──────┬──────┘  │
└────────┼─────────────┼─────────────┼──────────────┼─────────┘
         │             │             │              │
         ▼             ▼             ▼              ▼
┌─────────────────────────────────────────────────────────────┐
│                 INFUSE UNIVERSAL CORE ENGINE                │
│                                                             │
│   ┌──────────────────┐  signals  ┌───────────────────────┐  │
│   │ Telemetry Engine │ ────────> │ Governor (Authority)  │  │
│   └──────────────────┘           └──────────┬────────────┘  │
│                                             │               │
│                                             │ decisions     │
│                                             ▼               │
│   ┌──────────────────┐           ┌───────────────────────┐  │
│   │  Policy Manager  │           │   Execution Control   │  │
│   │  (10 Dimensions) │           │    Boundary (ECB)     │  │
│   └──────────────────┘           └───────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

The ChatGPT and MCP integrations are implemented strictly as thin, secure adapter layers. They introduce **zero duplicate business logic**:
- **Zero re-implementation** of state evaluation or transitions
- **Zero re-implementation** of pricing or cost modeling
- **Zero re-implementation** of policy enforcement or Governor decisions
- **All requests delegate** to the certified INFUSE universal core and Execution Control Boundary

---

## Documentation Index

### Remote MCP Public Directory Integration
- [Public Plugin Architecture](PUBLIC_PLUGIN_ARCHITECTURE.md): Architectural design of Remote MCP as primary public directory model.
- [Remote MCP Production Endpoint](MCP_PRODUCTION_ENDPOINT.md): Specification of `/mcp` Streamable HTTP transport, SSE, and reverse proxy setup.
- [OpenAI Submission Requirements](OPENAI_SUBMISSION_REQUIREMENTS.md): Breakdown of modern OpenAI directory requirements and annotations.
- [Public Directory Submission Checklist](PUBLIC_DIRECTORY_SUBMISSION_CHECKLIST.md): Automated and operator checklist for directory submission.
- [Public Plugin Certification Report](PUBLIC_PLUGIN_CERTIFICATION_REPORT.md): Complete engineering certification report.

### Custom GPT / OpenAPI Actions Layer
- [OpenAI Integration Reference](OPENAI_INTEGRATION_REFERENCE.md): Technical spec for Custom GPT Actions.
- [Architecture](ARCHITECTURE.md): Structural boundary and "One Core, Many Adapters" invariant.
- [Tool Catalog](TOOL_CATALOG.md): Full documentation of all 10 curated tools and inputs.
- [Authentication & Multi-Tenancy](AUTHENTICATION.md): Token schemes, scopes, and tenant isolation.
- [Security & Prompt Neutralization](SECURITY.md): Adversarial defense, prompt injection mitigation, and SSRF protection.
- [App Listing Metadata](APP_LISTING.md): OpenAI Store submission metadata, descriptions, and categories.
- [Starter Prompts & Few-Shot Prompts](STARTER_PROMPTS.md): Conversation starters and prompt templates.
- [Testing & Quality Assurance](TESTING.md): Verification suite details and regression guarantees.
- [Deployment & Operational Runbook](DEPLOYMENT.md): Production hosting, Docker deployment, and environment variables.
- [Implementation Report](CHATGPT_APP_IMPLEMENTATION_REPORT.md): Initial ChatGPT adapter engineering certification.
