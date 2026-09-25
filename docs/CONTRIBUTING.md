# Contributing to INFUSE

Thank you for your interest in contributing to **INFUSE (Execution Intelligence)**!

---

## 1. Core Architectural Invariants

Before writing code or opening pull requests, familiarize yourself with our immutable architectural principles:

1. **One Core, Many Adapters:** Keep core intelligence (State, Governor, Observers, Event Bus) agnostic to specific LLM providers and agent runtimes. Provider-specific logic belongs in `infuse/providers/` and agent-specific mechanics in `infuse/agents/`.
2. **Governor Authority:** The `GovernorEngine` is the sole authority for execution decisions. Observers must remain purely observational and must never mutate or control execution directly.
3. **Control Boundary Separation:** Physical runtime actions (`cancel`, `throttle`, `switch`, `terminate`) must be mediated strictly by the `ExecutionControlBoundary`.
4. **No Hard-Coded Rules:** Never hard-code monetary costs, provider pricing, token budgets, or customer thresholds in code. Everything must be externalized in declarative policy.
5. **Frozen Baseline Preservation:** The v0.1.0 release (Blocks 00–36, commit `cfab1a402770ac8814471f13b8e525c490809268`) is frozen and immutable. All new features are developed on post-v0.1.0 development branches.

---

## 2. Development Setup

```bash
# Clone the repository
git clone https://github.com/adorbistech/infuse.git
cd infuse

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in editable mode with development dependencies
pip install -e ".[dev]"
```

---

## 3. Running Tests

All contributions must pass the full regression test suite with 100% pass rate:

```bash
# Run backend Python tests
python3 -m unittest discover -s tests

# Run frontend tests
npm test --prefix frontend
```

---

## 4. Submitting Pull Requests

1. Create a feature branch: `git checkout -b feature/my-new-adapter`.
2. Ensure your changes include comprehensive unit tests.
3. Verify that zero secrets, credentials, or private configuration files are tracked.
4. Open a clear Pull Request detailing your changes and linking any relevant GitHub issues.

---

## 5. Security & Responsible Disclosure

If you discover a security vulnerability in INFUSE, please do not file a public GitHub issue. Instead, email `security@adorbistech.com` for responsible disclosure.
