# INFUSE — Execution Intelligence

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

**INFUSE** is an independent, provider-agnostic, agent-agnostic execution intelligence, optimization, and governance layer for autonomous AI agents.

It acts as a **voltage regulator** between autonomous agents (such as Claude Code, OpenCode, Codex, Hermes, OpenClaw, Lovable) and AI execution infrastructure (OpenAI, Anthropic, Google Gemini, DeepSeek, LiteLLM).

---

## Key Features

* **Glass-Box Observability:** Real-time token velocity, context growth, tool activity, web calls, and cost monitoring.
* **Deterministic Governance:** Strict user-defined policies for budgets, token ceilings, request rates, execution timeouts, and access allowlists.
* **Closed-Loop Execution Regulation:** Automated dynamic optimization, provider switching, throttling, and circuit-breaker halts managed exclusively by the central Governor.
* **Adapter-First Extensibility:** Language-neutral contracts and modular adapters for any agent runtime, model provider, SDK, CLI, or MCP interface.
* **Zero Hard-Coding:** All thresholds, budgets, and behavior rules are policy-driven.

---

## Milestone Status

* **Block 00 — Architecture & Contracts Freeze:** `COMPLETE`
  * Universal Execution Contract
  * Execution Event Contract
  * Governance Policy Contract
  * Execution Control Boundary Contract
  * Governor Action Contract
  * Execution State Contract
  * Frontend ViewModel Contract
  * Adapter Capability Contract

---

## Repository Structure

```text
infuse/
├── infuse/
│   ├── contracts/            # Versioned Universal Contracts
│   │   ├── common.py
│   │   ├── execution.py
│   │   ├── events.py
│   │   ├── policy.py
│   │   ├── control.py
│   │   ├── governor.py
│   │   ├── state.py
│   │   ├── capabilities.py
│   │   └── frontend.py
│   └── version.py
├── tests/
│   └── contracts/            # Contract test suite (33 tests)
├── docs/
│   └── architecture/
│       └── contracts.md      # Formal Contracts Specification
├── ARCHITECTURE.md           # Architecture Baseline
└── pyproject.toml
```

---

## Running Contract Tests

```bash
python3 -m unittest discover -s tests -v
```

---

## License

INFUSE is open-source software licensed under the [Apache-2.0 License](LICENSE).
