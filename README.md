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
* **Block 01 — Frontend Foundation & Contract Integration:** `COMPLETE`
* **Block 02 — Frontend Execution / Information Surface Hardening:** `COMPLETE`
* **Block 03 — Frontend Governance / Policy Surface Hardening:** `COMPLETE`
* **Block 04 — Frontend Data & State Contract:** `COMPLETE`
* **Block 05 — Universal HTTP API:** `COMPLETE`
* **Block 06 — Policy Manager:** `COMPLETE`
* **Block 07 — Execution Context:** `COMPLETE`
* **Block 08 — Workload Classifier:** `COMPLETE`

---

## Repository Structure

```text
infuse/
├── infuse/
│   ├── classifier/           # Workload Classifier (Block 08)
│   │   ├── models.py         # Canonical WorkloadClassification & dimensions
│   │   ├── rule_based.py     # Deterministic rule-based classifier
│   │   ├── interfaces.py     # IWorkloadClassifier interface
│   │   ├── service.py        # WorkloadClassificationService
│   │   └── errors.py         # Domain classifier exceptions
│   ├── context/              # Execution Context Boundary (Block 07)
│   │   ├── models.py         # Canonical ExecutionContextRecord & sub-models
│   │   ├── builder.py        # Context Builder & Factory
│   │   ├── validation.py     # Structural & constraint validation
│   │   ├── normalization.py  # Deterministic normalization
│   │   ├── interfaces.py     # IExecutionContextService & IExecutionContextRepository
│   │   ├── repository.py     # In-memory execution context repository
│   │   ├── service.py        # ExecutionContextService implementation
│   │   └── errors.py         # Domain context exceptions
│   ├── policy/               # Governance Policy Manager (Block 06)
│   │   ├── manager.py        # Lifecycle, versioning & active policy authority
│   │   ├── validation.py     # 10-section contract & range validation
│   │   ├── normalization.py  # Deterministic normalization
│   │   ├── interfaces.py     # IPolicyManager interface
│   │   └── errors.py         # Policy domain exceptions
│   ├── api/                  # Universal HTTP API Boundary (Block 05)
│   │   ├── app.py            # Starlette application factory & middleware
│   │   ├── errors.py         # Normalized error handling
│   │   ├── routes/           # /v1 routes (execute, executions, policies, health)
│   │   ├── services/         # Decoupled service interfaces
│   │   ├── repositories/     # In-memory repository boundary
│   │   └── schemas/          # Transport schemas
│   ├── contracts/            # Versioned Universal Contracts (Block 00)
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
├── frontend/                 # INFUSE Stitch Frontend Console (Blocks 01-04)
│   ├── src/
│   │   ├── contracts/        # Normalized ViewModels & AppError
│   │   ├── data/             # IDataProvider & MockDataProvider
│   │   ├── state/            # Compartmentalized Store
│   │   ├── components/       # Stitch Obsidian UI components
│   │   └── pages/            # Execution & Governance pages
│   └── tests/                # Frontend contract test suite (49 tests)
├── tests/
│   ├── contracts/            # Python contract test suite (33 tests)
│   ├── api/                  # Python API test suite (25 tests)
│   ├── policy/               # Python Policy Manager test suite (26 tests)
│   ├── context/              # Python Execution Context test suite (20 tests)
│   └── classifier/           # Python Workload Classifier test suite (15 tests)
├── docs/
│   └── architecture/
│       ├── contracts.md      # Formal Contracts Specification
│       ├── frontend_integration_map.md # Frontend Architecture Map
│       ├── api_contract.md   # Universal HTTP API Specification
│       └── policy_manager.md # Policy Manager Specification
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
