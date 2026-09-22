# INFUSE Policy Manager Specification

**Milestone:** Block 06 (Policy Manager)  
**Status:** Frozen  
**Schema Version:** `1.0.0`  
**Contract Baseline:** Block 00 Governance Policy Contract ([`GovernancePolicy`](file:///Users/ssd/infuse/infuse/contracts/policy.py#L198-L256))  
**API Baseline:** Block 05 Universal HTTP API ([`IPolicyService`](file:///Users/ssd/infuse/infuse/api/services/interfaces.py#L47-L64))  

---

## 1. Overview & Architectural Role

The **Policy Manager** is the lifecycle, validation, normalization, versioning, revision history, and active-state authority for INFUSE governance policies.

It establishes a clean, decoupled boundary between the Universal HTTP API transport layer and the future core execution engines (such as the Governor).

```text
┌────────────────────────────────────────────────────────┐
│               UNIVERSAL HTTP API LAYER                 │
│                                                        │
│   GET /v1/policies              PUT /v1/policies/{id}  │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
                     IPolicyService
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│                     POLICY MANAGER                     │
│                                                        │
│  • Validation (Structural, Range, Combinatorial)       │
│  • Normalization (Defaults, Strings, Allow/Denylists)  │
│  • Versioning & Monotonic Revision History             │
│  • Deep-Copy Snapshot Immutability                     │
│  • Deterministic Active Policy Resolution              │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
                    IPolicyRepository
                            │
                            ▼
            Future Governor Engine (Block 21)
```

> [!IMPORTANT]
> **Core Architectural Principle:**
> **"Policy Manager manages governance policy. Policy Manager does not enforce governance."**
> 
> * **Policy Manager OWNS:** Policy validation, normalization, versioning, revision history, immutability, active-revision resolution, and storage abstraction.
> * **Policy Manager DOES NOT OWN:** Runtime enforcement, Governor decisions, throttling, halts, model switching, provider selection, ranking, token observation, or economics.

---

## 2. Policy Lifecycle

Every governance policy envelope traverses a strict 6-stage lifecycle:

```text
CREATE ──► VALIDATE ──► NORMALIZE ──► VERSION ──► STORE ──► ACTIVATE / RETRIEVE
```

1. **CREATE:** New policy envelopes are ingested via [`create_policy()`](file:///Users/ssd/infuse/infuse/policy/manager.py#L46-L71) with unique `policy_id` identity.
2. **VALIDATE:** Evaluated against canonical structural and logical constraints via [`validate_policy()`](file:///Users/ssd/infuse/infuse/policy/validation.py#L14-L149).
3. **NORMALIZE:** Strings are trimmed, currency uppercased, and access lists deduplicated deterministically via [`normalize_policy()`](file:///Users/ssd/infuse/infuse/policy/normalization.py#L31-L147).
4. **VERSION:** Monotonic revision numbers are computed; duplicate versions trigger automatic patch increments (`1.0.0` $\to$ `1.0.1`).
5. **STORE:** Snapshots are cloned into the repository ledger. Historical revisions remain strictly immutable.
6. **ACTIVATE / RETRIEVE:** The designated active revision is retrievable by the runtime; queries return deep copies to prevent state corruption.

---

## 3. Validation Rules Across 10 Sections

[`validate_policy()`](file:///Users/ssd/infuse/infuse/policy/validation.py#L14-L149) strictly validates:

| Section | Rule / Constraint | Error Trigger |
|---|---|---|
| **Identity** | `policy_id` and `version` non-empty strings | Blank or whitespace-only |
| **Budget** | `max_cost_per_task`, `max_cost_per_day`, `max_cost_per_month` $\ge 0.0$ | Negative values |
| **Budget Hierarchy** | $\text{max\_cost\_per\_month} \ge \text{max\_cost\_per\_day} \ge \text{max\_cost\_per\_task}$ | Inverted budget limits |
| **Tokens** | `max_input_tokens`, `max_output_tokens`, `max_total_tokens` $\ge 0$ | Negative integers |
| **Token Hierarchy** | $\text{max\_total\_tokens} \ge \text{max\_input\_tokens}$, $\text{max\_total\_tokens} \ge \text{max\_output\_tokens}$ | Total less than parts |
| **Requests** | `max_rpm` and `max_requests_per_task` $> 0$ | Non-positive integers |
| **Runtime** | `max_execution_time_seconds` $> 0$ | Non-positive integers |
| **Providers** | Allowlist and blocklist must be disjoint sets | Overlapping provider/model |
| **Web** | `max_web_requests_per_task` $\ge 0$; disjoint domain allow/block lists | Overlapping domains |
| **Tools** | `max_tool_calls_per_task`, `max_consecutive_tool_failures` $\ge 0$; disjoint tool lists | Overlapping tool names |
| **Retries** | `max_retries` $\ge 0$; `backoff_factor` $\ge 1.0$ | Sub-unity backoff factor |
| **Anomaly** | `token_velocity_surge_threshold` $> 0.0$; `repetitive_loop_threshold` $\ge 1$ | Non-positive thresholds |
| **Actions** | All action matrix bindings must map to valid [`GovernorAction`](file:///Users/ssd/infuse/infuse/contracts/governor.py#L10-L19) enum values | Unknown action strings |

---

## 4. Normalization Behavior

[`normalize_policy()`](file:///Users/ssd/infuse/infuse/policy/normalization.py#L31-L147) guarantees deterministic representations:
* String trimming for names, IDs, currency, and list elements.
* Currency ISO normalization (`"usd"` $\to$ `"USD"`).
* Deduplication of provider, model, domain, tool, and error list entries while preserving insertion order.
* Instantiation of default sub-model envelopes for omitted sections.
* Schema version normalization to `"1.0.0"`.

---

## 5. Versioning & Snapshot Immutability

* **Stable Identity:** `policy_id` identifies the policy entity (e.g. `pol_default`, `pol_prod`).
* **Monotonic Revisions:** Every update generates a new immutable snapshot (`1.0.0`, `1.0.1`, `1.0.2`, etc.).
* **Zero In-Place Mutation:** Historical revisions are preserved indefinitely in repository history.
* **Deep-Copy Isolation:** All read operations (`get_policy()`, `get_active_policy()`, `get_policy_history()`) return independent deep copies. Caller tampering with returned objects has zero effect on persisted state.

---

## 6. Active Policy Semantics

* Exactly one policy revision is designated active at any point in time.
* When a policy is created or updated with `is_active=True`, or activated via `activate_policy(policy_id, version)`:
  1. The target revision's `is_active` flag is set to `True`.
  2. All other policies and previous revisions are automatically set to `is_active = False`.
* `get_active_policy()` returns the active policy snapshot.

---

## 7. Service & Transport Layer Integration

The Policy Manager seamlessly integrates with the Block 05 Universal HTTP API via [`DefaultPolicyService`](file:///Users/ssd/infuse/infuse/api/services/default.py#L121-L157):

* `GET /v1/policies` $\longrightarrow$ calls `PolicyManager.list_policies()` and `PolicyManager.get_active_policy()`.
* `PUT /v1/policies/{id}` $\longrightarrow$ calls `PolicyManager.update_policy(policy_id, policy)`, mapping:
  * `PolicyValidationError` $\longrightarrow$ `422 Unprocessable Entity` (`VALIDATION_ERROR`)
  * `PolicyNotFoundError` $\longrightarrow$ `404 Not Found` (`NOT_FOUND`)
  * `PolicyConflictError` $\longrightarrow$ `409 Conflict` (`CONFLICT`)
