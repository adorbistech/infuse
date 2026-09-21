# INFUSE — Technical Architecture Baseline

**Project:** INFUSE — Execution Intelligence  
**Repository:** `https://github.com/adorbistech/infuse`  
**License:** Apache-2.0  
**Current Milestone:** Block 00 (Architecture & Contracts Freeze)  

---

## 1. System Vision

INFUSE is an independent execution intelligence, optimization, and governance layer that sits between autonomous AI agents and AI infrastructure.

```text
AUTONOMOUS AGENTS (Claude Code, OpenCode, Codex, Hermes, OpenClaw, Lovable)
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 INFUSE EXECUTION REGULATOR                  │
│                                                             │
│  Observe ──► State Engine ──► Governor ──► Control Boundary │
│  (Tokens, Cost, Health, Tools, Web, Anomalies)              │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
AI INFRASTRUCTURE (OpenAI, Anthropic, Gemini, DeepSeek, LiteLLM)
```

---

## 2. Frozen Block 00 Architecture Baseline

### 2.1 Five Core Layers
1. **User / Governance Layer:** 2-page Stitch frontend control surface (Information & Governance) and REST API client.
2. **Control Layer:** API Gateway, Policy Manager (effective policy derivation), and Governor (single control authority).
3. **Intelligence Layer:** Workload Classifier, Capability Resolver, Router, Execution State Engine, Token Observer, Economics Engine, Health Engine, Anomaly Detector.
4. **Execution Layer:** Execution Control Boundary, Universal Agent Adapters, Provider Adapters (LiteLLM substrate), Execution Lifecycle Engine.
5. **Observation Layer:** Event Bus ingesting immutable `ExecutionEvent` streams, fan-out to observers, deriving signals for the State Engine.

### 2.2 Permanent Architectural Rules
1. **No Hard-Coding:** All governance limits, pricing, and provider rules are data-driven (`GovernancePolicy`).
2. **One Core, Many Adapters:** Generic execution core with modular adapters for agents, providers, SDKs, CLI, and MCP.
3. **Governor Authority:** Observers produce signals; Governor produces decisions (`CONTINUE`, `OPTIMIZE`, `ESCALATE`, `DOWNGRADE`, `SWITCH`, `THROTTLE`, `STOP`).
4. **Execution Control Boundary:** Control actions are dispatched only after discovering agent capabilities (`supports_cancel`, `supports_throttle`, `supports_next_step_switch`, `supports_terminate`).
5. **Independent & Future-Ready:** Independently deployable (self-hosted server, Docker, portable CLI) without Antigravity dependency.

---

## 3. LEGO Block Build Order

```text
[Block 00: Architecture & Contracts Freeze]  <── (COMPLETED & FROZEN)
   ↓
[Blocks 01–04: Frontend Control Surface & ViewModel Integration]
   ↓
[Block 05: Universal HTTP API]
   ↓
[Blocks 06–07: Policy Manager & Execution Context]
   ↓
[Blocks 08–13: Execution Core, Registry, Router & Lifecycle]
   ↓
[Blocks 14–19: Event Bus & Observation Engines]
   ↓
[Blocks 20–22: State Engine, Governor & Execution Control Boundary]
   ↓
[Blocks 23–27: Agent Universal & Branded Adapters]
   ↓
[Blocks 28–30: SDKs, CLI & MCP Server]
   ↓
[Blocks 31–36: E2E Integration, Hardening & Self-Hosted Packaging]
```

---

## 4. Contract Package Structure

```text
infuse/contracts/
├── common.py          # InfuseBaseModel, schema versioning & extensions
├── governor.py        # GovernorAction & GovernorDecisionRecord
├── state.py           # ExecutionState, ActionState & ExecutionStateSnapshot
├── policy.py          # GovernancePolicy (Budget, Tokens, Requests, Actions)
├── control.py         # ControlCapability, ControlOperation, ControlResult
├── events.py          # ExecutionEvent envelope & canonical event taxonomy
├── execution.py       # ExecutionRequest & ExecutionResult envelopes
├── capabilities.py    # AdapterRegistration (Agent & Provider capabilities)
└── frontend.py        # ViewModels for Stitch Information & Governance UI
```
