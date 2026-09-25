# INFUSE ChatGPT App Integration

Official OpenAI Custom GPT & ChatGPT App integration for **INFUSE — Execution Intelligence**.

---

## Overview

The **INFUSE ChatGPT App** connects OpenAI ChatGPT directly to the INFUSE runtime, allowing users and autonomous workflows in ChatGPT to monitor, inspect, and execute governed AI operations.

### Architectural Principle: *One Core, Many Adapters*

```
┌─────────────────────────────────────────────────────────────┐
│                    INTERACTION SURFACES                     │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌─────────────┐  │
│  │ HTTP REST │ │ PythonSDK │ │  MCP Svr  │ │ ChatGPT App │  │
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

The ChatGPT App integration is implemented strictly as a thin, secure adapter layer (`infuse.chatgpt`). It introduces **zero duplicate business logic**:
- **Zero re-implementation** of state evaluation or transitions
- **Zero re-implementation** of pricing or cost modeling
- **Zero re-implementation** of policy enforcement or Governor decisions
- **All requests delegate** to the certified INFUSE universal core

---

## Features

- **OpenAPI 3.1.0 Compatible Actions Schema**: Served automatically from `/chatgpt/openapi.json`.
- **10 Curated Governed Tools**:
  - `get_system_info`: Inspect INFUSE runtime metadata and supported providers.
  - `list_executions`: Query and filter execution histories.
  - `get_execution_state`: Read current canonical state (`NORMAL`, `COST_PRESSURE`, `RUNAWAY`, `QUALITY_DEGRADED`, `PROVIDER_CONSTRAINED`).
  - `get_execution_result`: Retrieve detailed telemetry, tokens, costs, and responses.
  - `inspect_execution`: In-depth telemetry breakdown and anomaly diagnostics.
  - `inspect_governor_decision`: Read Governor decisions, taxonomy reason codes, and actions.
  - `get_provider_health`: Real-time status of Anthropic, OpenAI, Gemini, DeepSeek, and LiteLLM.
  - `list_policies`: List active and configured policies.
  - `get_policy`: Retrieve detailed limits and budget configurations.
  - `execute_task`: Submit governed tasks to the multi-provider routing matrix.
  - `control_execution`: Regulate live executions via canonical Governor actions (`CONTINUE`, `OPTIMIZE`, `ESCALATE`, `DOWNGRADE`, `SWITCH`, `THROTTLE`, `STOP`).
- **Flexible Authentication**: Supports API Key / Bearer tokens, OAuth2 Bearer, and configurable Multi-Tenant isolation.
- **Structured ChatGPT UI Cards**: Clean visual responses for execution summaries, cost metrics, and Governor verdicts.

---

## Quick Start

### 1. Launch INFUSE Server with ChatGPT Endpoints

```bash
# Start INFUSE server with ChatGPT App endpoints enabled
export INFUSE_CHATGPT_AUTH_MODE="bearer"
export INFUSE_CHATGPT_API_KEY="infuse_live_secret_key"
export INFUSE_PUBLIC_URL="https://infuse.yourdomain.com"

python3 -m infuse.deployment.server
```

### 2. Configure Custom GPT in OpenAI

1. Navigate to [ChatGPT](https://chatgpt.com) > **Explore GPTs** > **Create a GPT**.
2. Under **Configure**, set:
   - **Name**: `INFUSE Execution Intelligence`
   - **Description**: `Real-time AI execution intelligence, cost optimization, and Governor safety controls.`
3. Scroll down to **Actions** and click **Create new action**.
4. In **Import from URL**, provide:
   ```
   https://infuse.yourdomain.com/chatgpt/openapi.json
   ```
5. Set **Authentication**:
   - **Authentication Type**: `API Key`
   - **Auth Type**: `Bearer`
   - **API Key**: `infuse_live_secret_key`

---

## Documentation Index

- [OpenAI Integration Reference](OPENAI_INTEGRATION_REFERENCE.md): Technical spec for Custom GPT Actions.
- [Architecture](ARCHITECTURE.md): Structural boundary and "One Core, Many Adapters" invariant.
- [Tool Catalog](TOOL_CATALOG.md): Full documentation of all 10 curated tools and inputs.
- [Authentication & Multi-Tenancy](AUTHENTICATION.md): Token schemes, scopes, and tenant isolation.
- [Security & Prompt Neutralization](SECURITY.md): Adversarial defense, prompt injection mitigation, and SSRF protection.
- [App Listing Metadata](APP_LISTING.md): OpenAI Store submission metadata, descriptions, and categories.
- [Starter Prompts & Few-Shot Prompts](STARTER_PROMPTS.md): Conversation starters and prompt templates.
- [Testing & Quality Assurance](TESTING.md): Verification suite details and regression guarantees.
- [Deployment & Operational Runbook](DEPLOYMENT.md): Production hosting, Docker deployment, and environment variables.
- [OpenAI Submission Checklist](SUBMISSION_CHECKLIST.md): Step-by-step submission verification.
- [Implementation Report](CHATGPT_APP_IMPLEMENTATION_REPORT.md): Complete engineering certification.
