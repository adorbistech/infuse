# INFUSE Economics Engine Specification

**Milestone:** Block 16 (Economics Engine)  
**Status:** Complete / Ready for Freeze  
**Schema Version:** `1.0.0`  

---

## 1. Overview & Purpose

The **INFUSE Economics Engine** is an economic observation and calculation component that sits downstream of the Token Observer (Block 15). It converts normalized token usage facts into deterministic, normalized economic cost facts.

```text
┌────────────────────────────────────────────────────────┐
│               TOKEN OBSERVER (Block 15)                │
│  • Normalized Token Usage Facts (Input, Output, Cache) │
│  • Authoritative vs Estimated Status                   │
│  • Execution Finalization State                        │
└───────────────────────────┬────────────────────────────┘
                            │
               ExecutionTokenSummary
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│             ECONOMICS ENGINE (Block 16)                │
│  • Pricing Rate Lookup via IPricingRegistry            │
│  • Exact Deterministic Decimal Cost Calculation        │
│  • Unit Normalization (per Token, per 1K, per 1M)      │
│  • Currency Propagation & Completeness Evaluation      │
└───────────────────────────┬────────────────────────────┘
                            │
              ExecutionEconomicSummary
                            │
           ┌────────────────┴────────────────┐
           ▼                                 ▼
Execution State Engine                       Governor
      (Block 20)                            (Block 21)
```

> [!IMPORTANT]
> **Core Separation of Responsibilities:**
> - **Token Observer:** *"How much was used?"*
> - **Economics Engine:** *"What economic cost does that usage represent?"*
> - **Governor:** *"What should INFUSE do about the execution?"*
>
> The Economics Engine calculates economic facts. It does **NOT** enforce budgets, bill customers, add markups/margins, select providers, route requests, throttle, or mutate execution lifecycles.

---

## 2. Economic Calculation Semantics

### Exact Decimal Arithmetic & Unit Normalization
* Calculations use Python's exact `decimal.Decimal` arithmetic to avoid floating-point drift.
* Units are explicitly declared in [`ModelPricingRate`](file:///Users/ssd/infuse/infuse/economics/models.py#L25-L45):
  - `PER_TOKEN`: factor = $1$
  - `PER_1K_TOKENS`: factor = $1,000$
  - `PER_1M_TOKENS`: factor = $1,000,000$
* Formula for dimension $D$:
  $$\text{cost}_D = \frac{\text{tokens}_D \times \text{rate}_D}{\text{factor}}$$

### Currency & Completeness Invariants
* **Explicit Currency:** Currency is propagated directly from the registered pricing rate (e.g. `"USD"`, `"EUR"`). If unspecified, currency is represented as `None` (never silently defaulted to USD).
* **Economic Completeness (`EconomicCompleteness`):**
  - `COMPLETE`: All observed token dimensions for the model are priced and calculated.
  - `PARTIAL`: Some token dimensions have rates and were calculated, but others are unpriced or missing.
  - `UNKNOWN`: No pricing metadata exists for the provider/model or all dimensions are unpriced.
* **No Zero Fabrication:** Unknown or unpriced costs are preserved as `None` rather than fabricated as `0.0`.

### Idempotency & Cumulative Updates
* Calculating cost from an [`ExecutionTokenSummary`](file:///Users/ssd/infuse/infuse/observer/models.py#L44-L79) is a pure, deterministic function.
* Receiving multiple or updated cumulative usage snapshots recalculates the state cleanly without double-counting past intervals.

---

## 3. Explicit Non-Responsibilities

| Non-Responsibility | Assigned Boundary |
| :--- | :--- |
| Customer billing, invoices, markups, margins | Billing Layer (Out of Scope) |
| Budget enforcement, quotas, throttling | Block 21 (Governor) |
| Target selection, routing, fallback | Block 11 (Router) |
| Token counting, usage normalization | Block 15 (Token Observer) |
| Lifecycle transition orchestration | Block 13 (Execution Lifecycle) |
| Provider health scoring | Block 17 (Health Engine) |
| Provider SDK interaction | Block 12 (Provider Adapter Layer) |
| Database persistence | Persistence Layer (Future) |
