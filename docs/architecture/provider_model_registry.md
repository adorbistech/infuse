# INFUSE Provider & Model Registry Specification

**Milestone:** Block 09 (Provider & Model Registry)  
**Status:** Frozen  
**Schema Version:** `1.0.0`  

---

## 1. Overview & Architectural Role

The **Provider & Model Registry** is the neutral catalog and metadata authority for execution targets available to INFUSE.

It answers:
> *"What execution targets exist, and what do they declare?"*

It does **not** answer:
> *"Which execution target should we use?"*  
> *"Is the provider healthy?"*  
> *"What does the request cost?"*  
> *"Should execution be throttled or halted?"*

```text
┌────────────────────────────────────────────────────────┐
│               EXECUTION CONTEXT (Block 07)             │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│             WORKLOAD CLASSIFIER (Block 08)             │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│          PROVIDER & MODEL REGISTRY (Block 09)          │
│                                                        │
│  • Provider Records & Declared Infrastructure          │
│  • Model Records & Declared Context/Token Limits       │
│  • Capability Metadata (Tools, Vision, Reasoning)      │
│  • Lifecycle Status (ACTIVE, DEPRECATED, DISABLED)     │
│  • Deterministic Validation & Normalization            │
│  • Zero Credentials / API Keys Stored                  │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
        Future Capability Resolver (Block 10)
                            │
                            ▼
                Future Router (Block 11)
                            │
                            ▼
              Future Governor Engine (Block 21)
```

> [!IMPORTANT]
> **Core Architectural Principle:**  
> **"Provider & Model Registry describes available execution targets. It does not resolve capabilities, select targets, route execution, calculate cost, measure health, or issue Governor actions."**

---

## 2. Registry Entities & Data Models

### 1. Provider Record ([`ProviderRecord`](file:///Users/ssd/infuse/infuse/registry/models.py#L93-L135))
Represents an AI execution provider (e.g. Anthropic, OpenAI, Google, DeepSeek, Local Gateway):
* `provider_id`: Unique stable provider string.
* `name`: Human-readable display name.
* `description`: Optional descriptive overview.
* `provider_type`: Category (`cloud`, `local`, `gateway`, `custom`).
* `endpoint_reference`: Reference URL metadata (no auth secrets).
* `version`: API / interface version string.
* `capabilities`: [`ProviderCapabilityDeclaration`](file:///Users/ssd/infuse/infuse/registry/models.py#L58-L90) (`supports_streaming`, `supports_tool_calling`, `supports_caching`, `supports_vision`, `supports_structured_output`, `supported_protocols`, `rate_limits`).
* `status`: [`RegistryLifecycleStatus`](file:///Users/ssd/infuse/infuse/registry/models.py#L18-L23) (`ACTIVE`, `DEPRECATED`, `DISABLED`).
* `created_at` / `updated_at`: UTC ISO timestamps.

### 2. Model Record ([`ModelRecord`](file:///Users/ssd/infuse/infuse/registry/models.py#L138-L187))
Represents a specific model belonging to a provider:
* `model_id`: Unique model identifier within the provider.
* `provider_id`: Parent provider identifier referencing a valid `ProviderRecord`.
* `name`: Display name.
* `family`: Model family tag (e.g. `claude-3`, `gpt-4`, `gemini-2`).
* `context_window`: Maximum input context window size in tokens ($> 0$).
* `max_output_tokens`: Maximum generation token limit ($> 0$).
* `capabilities`: [`ModelCapabilityDeclaration`](file:///Users/ssd/infuse/infuse/registry/models.py#L32-L55) (`supports_tools`, `supports_vision`, `supports_structured_output`, `supports_streaming`, `supports_caching`, `supports_reasoning`, `modalities`, `declared_capabilities`).
* `status`: [`RegistryLifecycleStatus`](file:///Users/ssd/infuse/infuse/registry/models.py#L18-L23).

---

## 3. Registry Lifecycle

```text
REGISTER ──▶ VALIDATE ──▶ NORMALIZE ──▶ STORE ──▶ RETRIEVE
```

1. **Register / Update:** Client provides `ProviderRecord` or `ModelRecord`.
2. **Validate:** Enforces non-empty IDs, positive token limits, schema versions, and checks recursively for forbidden secret keys (`api_key`, `secret`, `token`, `password`, `Bearer ...`).
3. **Normalize:** Trims whitespace, deduplicates capability strings and protocols with canonical casing.
4. **Store:** Persists records safely behind an `RLock` in thread-safe memory with deep-copy isolation.
5. **Retrieve:** Returns immutable deep-copies to prevent accidental cross-thread or cross-service state pollution.

---

## 4. Query Interface ([`IProviderModelRegistry`](file:///Users/ssd/infuse/infuse/registry/interfaces.py#L13-L84))

Neutral catalog query methods:
* `get_provider(provider_id)`
* `list_providers(status=None)`
* `get_model(model_id, provider_id=None)`
* `list_models(status=None)`
* `list_models_for_provider(provider_id, status=None)`
* `get_summary()`

> [!CAUTION]
> **Prohibited Operations:** Methods such as `best_model()`, `select_model()`, `route()`, `rank()`, or `choose()` do not exist in Block 09.

---

## 5. Architectural Boundaries

* **Block 10 Boundary (Capability Resolver):** The registry stores *declared facts*; Block 10 matches workload requirements against those declarations.
* **Block 11 Boundary (Router):** The registry does not rank, select, or route execution targets.
* **Health Boundary (Block 17):** Registry status (`ACTIVE`, `DEPRECATED`, `DISABLED`) is administrative metadata only; it does not measure live latency, uptime, or error rates.
* **Economics Boundary (Block 16):** The registry contains zero cost/token formulas, margins, or billing calculations.
* **Governor Boundary (Block 21):** The registry does not enforce policies or make control decisions.
* **Security Invariant:** Zero credentials, passwords, or API keys are stored in the registry.
