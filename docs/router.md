# INFUSE Router Specification

**Milestone:** Block 11 (Router)  
**Status:** Frozen  
**Schema Version:** `1.0.0`  

---

## 1. Overview & Purpose

The **Router** is the deterministic decision layer in INFUSE that selects an execution target from the set of compatible targets established by the Capability Resolver (Block 10).

It answers:
> *"Which compatible target should execute this workload?"*

It does **not** execute the target or invoke provider APIs.

```text
┌────────────────────────────────────────────────────────┐
│               EXECUTION CONTEXT (Block 07)             │
│  • preferred_providers, preferred_models, metadata     │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│             WORKLOAD CLASSIFIER (Block 08)             │
│  • category, complexity_level, dimensional intensity   │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│          PROVIDER & MODEL REGISTRY (Block 09)          │
│  • Catalog declarations & metadata snapshot            │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│             CAPABILITY RESOLVER (Block 10)             │
│  • Unranked compatible_targets pool                    │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│                     ROUTER (Block 11)                  │
│                                                        │
│  • Consumes compatible candidates from Block 10        │
│  • Applies deterministic routing strategy              │
│  • Honors explicit model & provider preferences        │
│  • Orders fallback targets deterministically           │
│  • Produces structured explainability evidence         │
│  • Zero provider execution or SDK invocation           │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
             Provider Adapter Layer (Block 12)
```

> [!IMPORTANT]
> **Core Architectural Guarantee:**  
> **"Router selects an execution target from compatible candidates. Router does not execute providers, perform health checks, calculate billing economics, enforce governance, or bypass capability resolution."**

---

## 2. Pipeline Position & Boundaries

* **Block 09 Boundary (Registry):** Catalog authority ("What exists?").
* **Block 10 Boundary (Capability Resolver):** Compatibility authority ("What is compatible?"). Router operates strictly on `compatible_targets` and never bypasses resolver findings or re-evaluates incompatible targets.
* **Block 11 Boundary (Router):** Target selection authority ("Which compatible target should execute this workload?").
* **Block 12 Boundary (Provider Adapter):** Invocation authority ("How do we actually invoke that target?").
* **Block 16 Boundary (Economics):** Router consumes normalized declared attributes only; zero pricing, token calculation, or billing logic in Router.
* **Block 17 Boundary (Health):** Router does not perform live health probes, pings, or latency benchmarking.
* **Block 21 Boundary (Governor):** Router does not enforce governance limits, stop tasks, or issue Governor actions.
* **Policy Boundary (Block 06):** Router does not enforce RPM/budget/token ceilings.

---

## 3. Router Inputs & Outputs

### Inputs
1. [`ExecutionContextRecord`](file:///Users/ssd/infuse/infuse/context/models.py#L173-L224) (Block 07): `preferred_providers`, `preferred_models`, constraints metadata.
2. [`CapabilityResolutionResult`](file:///Users/ssd/infuse/infuse/resolver/models.py#L96-L121) (Block 10): `compatible_targets: List[CandidateTarget]`, `requirements`.
3. [`WorkloadClassification`](file:///Users/ssd/infuse/infuse/classifier/models.py#L89-L121) (Block 08, Optional): `category`, `complexity_level`, dimensional intensities.
4. `strategy: Optional[RoutingStrategy]` (Optional): Explicit strategy override.

### Output: [`RouteDecision`](file:///Users/ssd/infuse/infuse/router/models.py#L65-L77)
* `route_id`: Unique route decision identifier (`route_<hex>`).
* `execution_id`: Target execution identifier.
* `selected_target`: Primary [`RouteTarget`](file:///Users/ssd/infuse/infuse/router/models.py#L32-L46) selected for invocation.
* `fallback_targets`: Ordered list of alternative compatible [`RouteTarget`](file:///Users/ssd/infuse/infuse/router/models.py#L32-L46) items for failover dispatch.
* `strategy_used`: Canonical [`RoutingStrategy`](file:///Users/ssd/infuse/infuse/router/models.py#L22-L29).
* `evidence`: Structured [`RoutingEvidence`](file:///Users/ssd/infuse/infuse/router/models.py#L49-L62) ledger detailing evaluation count, preference matches, tie-breaking, and explanation rationale.
* `timestamp`: UTC ISO decision timestamp.
* `schema_version`: `"1.0.0"`.

---

## 4. Routing Strategies & Candidate Selection

1. **`PREFERENCE`:**
   - Evaluates index rank in `preferred_models`, then `preferred_providers`.
   - Breaks ties by declared capability count, context window size, and lexicographical identifier.
2. **`WORKLOAD_FIT`:**
   - Prioritizes models declaring specialized capabilities (e.g. `reasoning`, `coding`) for high-complexity or reasoning/coding tasks.
3. **`LOW_LATENCY`:**
   - Prioritizes streaming/SSE declarations and lighter architectural profiles.
4. **`COST_EFFICIENT`:**
   - Prioritizes efficient model architectures and capability richness.
5. **`BALANCED` (Default):**
   - Combines preference recognition, capability richness, and context capacity with deterministic tie-breaking.

---

## 5. Deterministic Tie-Breaking Precedence

When multiple candidates evaluate equally under an objective:
1. Exact preferred model index match (lower index is higher preference)
2. Exact preferred provider index match
3. Total declared capabilities count (descending)
4. Context window size (descending)
5. Lexicographical comparison `(provider_id, model_id)`

---

## 6. Error & Empty State Behavior

* When `len(resolution.compatible_targets) == 0`, Router raises [`NoCompatibleTargetsError`](file:///Users/ssd/infuse/infuse/router/errors.py#L12-L14). Router never searches the registry independently, never bypasses the resolver, and never invents arbitrary fallbacks.
