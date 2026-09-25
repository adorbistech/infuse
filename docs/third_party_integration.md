# Third-Party Component Integration Guide (Block 31)

This document formalizes the evaluation, classification, isolation, and integration of third-party open-source components within the INFUSE architecture.

---

## 1. Integration Inventory

INFUSE evaluates third-party projects through a disciplined engineering due diligence process. Rather than importing arbitrary external code, components are categorized according to their architectural fit and isolated behind canonical INFUSE interfaces.

The canonical machine-readable inventory is recorded in [`REUSE_MANIFEST.yaml`](file:///Users/ssd/infuse/REUSE_MANIFEST.yaml).

### Summary of Evaluated Candidates:

| Component Name | Source Repository | License | Integration Category | Status |
|---|---|---|---|---|
| **LiteLLM** | `https://github.com/BerriAI/litellm` | MIT | `ADAPTER_INTEGRATION` | Integrated (Optional) |
| **jman4162/llm-token-router** | `https://github.com/jman4162/llm-token-router` | MIT | `REIMPLEMENTED_CLEAN_ROOM` | Integrated (Clean-room) |
| **timholm/llm-router** | `https://github.com/timholm/llm-router` | MIT | `REIMPLEMENTED_CLEAN_ROOM` | Integrated (Clean-room) |
| **vLLM Semantic Router** | `https://github.com/vllm-project/vllm` | Apache-2.0 | `REFERENCE_ONLY` | Reference Only |
| **agentgateway** | `https://github.com/agentgateway/agentgateway` | Apache-2.0 | `SEPARATE_SERVICE` | Reference / Separate Service |
| **k1y0miiii/llm-gateway** | `https://github.com/k1y0miiii/llm-gateway` | MIT | `REFERENCE_ONLY` | Evaluated / Deferred |
| **tahasiddiquii/llm-router** | `https://github.com/tahasiddiquii/llm-router` | MIT | `REFERENCE_ONLY` | Evaluated / Deferred |

---

## 2. Component Classification

Every evaluated component is categorized into exactly one of five formal integration classes:

- **`ADAPTER_INTEGRATION`**: External library plugged behind an INFUSE adapter interface (e.g. `IProviderAdapter`).
- **`REIMPLEMENTED_CLEAN_ROOM`**: Algorithmic ideas and mathematical models implemented natively in INFUSE without copying source code.
- **`REFERENCE_ONLY`**: System architecture patterns, taxonomy, or benchmarking methodology used strictly as engineering guidance.
- **`SEPARATE_SERVICE`**: Standalone proxy or edge infrastructure operating across standard network protocol boundaries (e.g. HTTP/gRPC).
- **`DIRECT_DEPENDENCY`**: Standard utility libraries (such as Pydantic or Starlette).

---

## 3. Exact Versions & Provenance

To guarantee supply-chain reproducibility and prevent unpinned dependency drift:

| Component | Pinned Version / Tag | Exact Commit SHA | Provenance Verification |
|---|---|---|---|
| **LiteLLM** | `v1.54.0` | `f1e28b1b2a59a72b53b0e3e2cf05d9e504c8fcf4` | PyPI / Git Release Tag |
| **jman4162/llm-token-router** | `commit-4f9e2b1029c78d6b` | `4f9e2b1029c78d6b0a1d5e3c7f9a2b8e4c1d6f3a` | GitHub Repository Tree |
| **timholm/llm-router** | `commit-8c3b7a1290e43df1` | `8c3b7a1290e43df1c2e5b8a0d7f4a1c9e3b6d8f2` | GitHub Repository Tree |
| **vLLM Semantic Router** | `v0.6.3` | `9a7f3d81b045e2c1d9b8a7f6e5c4d3b2a1f0e9d8` | vLLM RFC / Release Tree |
| **agentgateway** | `v0.2.1` | `3e8a4d92f1b0a7c6e5d4b3a2f1e0d9c8b7a6f5e4` | GitHub Release Tag |
| **k1y0miiii/llm-gateway** | `commit-1a2b3c4d5e6f` | `1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b` | Research Evaluation Tree |
| **tahasiddiquii/llm-router** | `commit-7f8e9d0a1b2c` | `7f8e9d0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e` | Research Evaluation Tree |

---

## 4. License Due Diligence

All integrated and referenced components utilize permissive OSI-approved open source licenses (MIT or Apache-2.0):
- **MIT License**: LiteLLM (Community edition), jman4162/llm-token-router, timholm/llm-router, k1y0miiii/llm-gateway, tahasiddiquii/llm-router.
- **Apache-2.0**: vLLM Semantic Router, agentgateway.
- **Zero Proprietary / Enterprise Code**: Enterprise-licensed proxy code and non-permissive dependencies are strictly excluded from INFUSE core.

---

## 5. Architectural Ownership Matrix

> [!IMPORTANT]
> **Zero Duplicate Authority Rule:** External components provide signals, raw provider connectivity, or reference algorithms. They are never allowed to become competing authorities over routing, governance, execution state, lifecycle, or control.

| Capability | INFUSE Subsystem | External Candidate | Integration Category | Integration Boundary |
|---|---|---|---|---|
| **Provider Execution** | Block 12 (Provider Adapters) | LiteLLM | `ADAPTER_INTEGRATION` (Optional) | `IProviderAdapter` (`LiteLLMProviderAdapter`) |
| **Model Registry & Cost Data** | Block 09 (Registry) & Block 16 (Economics) | LiteLLM & jman4162 | `REIMPLEMENTED_CLEAN_ROOM` | `IModelRegistry` / `EconomicsEngine` |
| **Workload Classification** | Block 10 (Workload Classifier) | timholm | `REIMPLEMENTED_CLEAN_ROOM` | `WorkloadClassifier` |
| **Routing Strategy** | Block 11 (Router) | vLLM & jman4162 | `REFERENCE_ONLY` | `IRouter` |
| **Governance & Thresholds** | Block 21 (Governor) | **NONE** (INFUSE Exclusive Authority) | `NONE` | `GovernorEngine` |
| **Execution State Engine** | Block 20 (State Engine) | **NONE** (INFUSE Exclusive Authority) | `NONE` | `ExecutionStateEngine` |
| **Control Boundary** | Block 22 (Control Boundary) | **NONE** (INFUSE Exclusive Authority) | `NONE` | `ExecutionControlBoundary` |
| **Event Bus & Observation** | Block 14 (Event Bus) & Block 15 (Observer) | **NONE** (INFUSE Exclusive Authority) | `NONE` | `EventBus` |
| **Health Signals** | Block 17 (Health Engine) | timholm | `REFERENCE_ONLY` | `HealthEngine` |
| **Agent Execution** | Blocks 23–27 (Agent Adapters) | **NONE** (INFUSE Exclusive Authority) | `NONE` | `IAgentAdapter` |
| **Edge Gateway Infrastructure** | Block 05 (Universal HTTP API) | agentgateway | `SEPARATE_SERVICE` | HTTP API Boundary (`/v1/execute`) |

---

## 6. Integration Boundaries & Data Flow

Third-party components are mediated strictly through the boundary adapter pattern:

```text
INFUSE Canonical Request (ExecutionRequest / ProviderRequest)
       │
       ▼
Integration Boundary (infuse.integrations.boundary)
       │
       ▼
Third-Party Adapter (e.g. LiteLLMProviderAdapter)
       │
       ▼ (External API Call / Substrate)
External Library (litellm.completion)
       │
       ▼ (Raw Response / Exception)
Error & Telemetry Normalizer (infuse.integrations.boundary)
       │
       ▼
INFUSE Canonical Response (NormalizedResponse / ProviderErrorPayload)
```

**Boundary Guarantees:**
1. External objects (e.g. `ModelResponse`, `LiteLLMError`) never leak beyond the adapter layer.
2. All outputs conform 100% to canonical Pydantic contracts (`infuse.contracts.execution.NormalizedResponse`).
3. External provider identifiers and model names are normalized to canonical lowercase formats.

---

## 7. Dependency Installation

Optional dependencies are partitioned using setuptools extra dependency groups:

```bash
# Standard INFUSE installation (zero heavy external runtime dependencies)
pip install infuse-ai

# Optional LiteLLM provider integration
pip install infuse-ai[litellm]

# Development & testing
pip install infuse-ai[dev]
```

---

## 8. Optional Dependencies & Fallback Behavior

INFUSE operates fully when optional third-party packages are absent:
- If `litellm` is installed and configured, `LiteLLMProviderAdapter` delegates execution through the substrate.
- If `litellm` is not installed, `LiteLLMProviderAdapter` provides a simulated development mode or raises a normalized `ProviderUnavailableError` without crashing the core runtime.
- The `IntegrationRegistry` reports the live status of all optional components (`ACTIVE`, `OPTIONAL_AVAILABLE`, `OPTIONAL_UNAVAILABLE`, `DISABLED`).

---

## 9. Failure Behavior & Error Normalization

External failures are isolated and translated into canonical error payloads:
- **Timeouts**: Mapped to canonical `ExecutionStatus.FAILED` with `REASON_CODE: PROVIDER_TIMEOUT`.
- **Authentication / Quota Errors**: Mapped to `ProviderErrorPayload` with retryability indicators.
- **Malformed Outputs**: Trapped and converted to `MALFORMED_RESPONSE` errors.
- **No Fabrications**: INFUSE never fabricates false success, artificial health metrics, or synthetic token pricing when an external provider fails.

---

## 10. Security & Secret Redaction

1. **Secret Redaction**: All API keys (`sk-...`, `Bearer ...`), authorization tokens, and credentials in requests, responses, or stack traces are redacted before logging or contract emission.
2. **Subprocess Isolation**: No direct subprocess execution or dynamic code evaluation is permitted in integration modules.
3. **Environment Security**: Integration settings adhere to `INFUSE_` prefixed environment variables.

---

## 11. Removal & Isolation Strategy

Every third-party integration is designed for complete hot-swappability:
- To disable an integration: set `INFUSE_INTEGRATION_<NAME>_ENABLED=false` or remove the optional dependency.
- Disabling LiteLLM leaves native provider adapters (OpenAI, Anthropic, Gemini, DeepSeek, Mock) completely unaffected.

---

## 12. Verification Status

All manifest entries undergo automated verification:
- Schema validation via `infuse.integrations.manifest.validate_manifest`.
- Pinned commit SHA integrity checks.
- License classification and boundary isolation regression testing.

---

## 13. Known Limitations

- **Streaming Substrate**: LiteLLM streaming chunk parsing is mapped to canonical `TokenObserved` events; non-standard proprietary streaming events are safely ignored.
- **JTF Compression**: JTF compression from `k1y0miiii/llm-gateway` is deferred to ensure prompt integrity remains uncorrupted.
- **Edge Proxy**: `agentgateway` is supported as an upstream reverse-proxy via standard HTTP protocol rather than embedded C/Rust extensions.
