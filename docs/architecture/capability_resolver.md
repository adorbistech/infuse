# INFUSE Capability Resolver Specification

**Milestone:** Block 10 (Capability Resolver)  
**Status:** Frozen  
**Schema Version:** `1.0.0`  

---

## 1. Overview & Architectural Role

The **Capability Resolver** translates consolidated workload requirements from the Execution Context and Workload Classification into a set of compatible registered execution targets.

It answers:
> *"Which registered execution targets satisfy the declared workload requirements?"*

It does **not** answer:
> *"Which target should be used?"*  
> *"Which target is the best or highest ranked?"*  
> *"What does the execution cost?"*  
> *"Is the target healthy?"*

```text
┌────────────────────────────────────────────────────────┐
│               EXECUTION CONTEXT (Block 07)             │
│  • min_context_tokens, requested_capabilities          │
│  • supports_tools, vision, structured_output           │
│  • excluded_providers, excluded_models                 │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│             WORKLOAD CLASSIFIER (Block 08)             │
│  • requires_tools, requires_vision, requires_web       │
│  • requires_structured_output, context_intensity       │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│          PROVIDER & MODEL REGISTRY (Block 09)          │
│  • ProviderRecord (status, protocols, streaming)       │
│  • ModelRecord (context_window, output_tokens, caps)   │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│             CAPABILITY RESOLVER (Block 10)             │
│                                                        │
│  • Deterministic Requirements Consolidation            │
│  • Capability Matching (Tools, Vision, Structured)     │
│  • Context Window & Token Capacity Validation          │
│  • Exclusion Constraints Filtering                     │
│  • Explicit Mismatch Reasons Ledger                    │
│  • Zero Selection, Ranking, Scoring, or Weights        │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
                   Future Router (Block 11)
                            │
                            ▼
              Future Governor Engine (Block 21)
```

> [!IMPORTANT]
> **Core Architectural Principle:**  
> **"Capability Resolver establishes compatibility. It does not select, rank, route, price, measure health, or govern execution."**

---

## 2. Input Contracts & Requirements Consolidation

The Capability Resolver extracts and consolidates requirements from:
1. **[`ExecutionContextRecord`](file:///Users/ssd/infuse/infuse/context/models.py#L173-L224) (Block 07):** Direct constraints (`min_context_tokens`, `supports_tools`, `supports_vision`, `supports_structured_output`, `excluded_providers`, `excluded_models`, `requested_capabilities`).
2. **[`WorkloadClassification`](file:///Users/ssd/infuse/infuse/classifier/models.py#L79-L113) (Block 08):** Inferred dimensional requirements (`requires_tools`, `requires_vision`, `requires_structured_output`, `requires_web`, `estimated_context_tokens`).
3. **[`IProviderModelRegistry`](file:///Users/ssd/infuse/infuse/registry/interfaces.py#L13-L84) (Block 09):** Snapshot of active registered `ProviderRecord` and `ModelRecord` entities.

---

## 3. Output Contract ([`CapabilityResolutionResult`](file:///Users/ssd/infuse/infuse/resolver/models.py#L96-L121))

* `requirements`: [`ResolvedRequirements`](file:///Users/ssd/infuse/infuse/resolver/models.py#L26-L65) consolidated specification.
* `compatible_targets`: List of [`CandidateTarget`](file:///Users/ssd/infuse/infuse/resolver/models.py#L68-L82) (stable sorted order by `(provider_id, model_id)`).
* `incompatible_targets`: List of [`IncompatibleTarget`](file:///Users/ssd/infuse/infuse/resolver/models.py#L85-L93) with explicit `mismatch_reasons` and `details`.
* `total_evaluated`: Total models evaluated.
* `total_compatible`: Total compatible models.
* `schema_version`: `"1.0.0"`.

---

## 4. Canonical Mismatch Reasons ([`MismatchReason`](file:///Users/ssd/infuse/infuse/resolver/models.py#L14-L23))

* `missing_required_capability:<cap>`: Target lacks required capability (e.g. `tools`, `vision`, `structured_output`, `web`).
* `context_window_insufficient`: Model context capacity is smaller than `min_context_tokens`.
* `max_output_tokens_insufficient`: Model max generation output is smaller than demanded output tokens.
* `excluded_provider`: Provider is in `excluded_providers`.
* `excluded_model`: Model is in `excluded_models`.
* `unsupported_modality`: Model does not support requested modality.
* `administratively_ineligible`: Model is marked `DEPRECATED` or `DISABLED`.
* `provider_ineligible`: Provider is missing or marked `DISABLED`.

---

## 5. Architectural Boundaries

* **Block 09 Boundary (Provider & Model Registry):** Resolver reads static catalog declarations and enforces declarative constraints.
* **Block 11 Boundary (Router):** Resolver provides the candidate compatibility pool; Router decides ranking, weighting, selection, and fallbacks.
* **Health Boundary (Block 17):** Resolver does not ping providers, measure live latency, or assess outage status.
* **Economics Boundary (Block 16):** Resolver does not calculate pricing, token costs, or financial optimization.
* **Governor Boundary (Block 21):** Resolver does not issue actions, throttle executions, or enforce policy limits.
