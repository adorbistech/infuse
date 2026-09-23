# INFUSE Governor Engine Specification

**Milestone:** Block 21 (Governor Engine)  
**Status:** Complete / Ready for Freeze  
**Schema Version:** `1.0.0`  

---

## 1. Overview & Architectural Role

The **INFUSE Governor Engine** is the sole control decision authority in the INFUSE architecture.

```text
User Policy
     ↓
Policy Manager (Block 06)
     ↓
Effective Policy ──────────────┐
                               ▼
Execution State (Block 20) ──► GOVERNOR (Block 21) ──► GovernorDecisionRecord
                               │                          │
                               │ [DECISION ONLY]          │ (EventType.GOVERNOR_DECISION)
                               ▼                          ▼
                     [NO EXECUTION HERE]     Execution Control Boundary (Block 22)
                                                          │
                                                          ▼
                                             Capability Enforcement / Action
```

> [!IMPORTANT]
> **Strict Separation of Decision vs Action:**
> - **Governor (Block 21):** *"What control action SHOULD happen given the effective policy and canonical execution state?"*  
> - **Execution Control Boundary (Block 22):** *"HOW is that action physically validated against runtime capabilities and safely executed?"*
>
> The Governor decides; it does **NOT** execute tools, perform network requests, invoke provider adapters, route traffic, schedule retries, or mutate lifecycle states.

---

## 2. Canonical Governor Action Vocabulary

The Governor emits one of the 7 frozen canonical control actions defined in Block 00 ([`infuse/contracts/governor.py`](file:///Users/ssd/infuse/infuse/contracts/governor.py)):

| Action | Meaning | Policy Binding Field |
| :--- | :--- | :--- |
| **`CONTINUE`** | Normal execution permitted to proceed without intervention. | *Default for `NORMAL` state* |
| **`OPTIMIZE`** | Suggest model/cost optimization or context compression. | `actions.budget_action`, `actions.token_action` |
| **`ESCALATE`** | Flag execution for human-in-the-loop oversight or higher-tier approval. | Configured on any policy trigger |
| **`DOWNGRADE`** | Suggest stepping down model tier for cost/rate containment. | Configured on any policy trigger |
| **`SWITCH`** | Suggest failing over or switching provider/model route. | `actions.provider_failure_action` |
| **`THROTTLE`** | Suggest introducing artificial rate limits or execution delays. | `actions.request_action` |
| **`STOP`** | Halt execution immediately due to policy breach or anomaly. | `actions.runtime_action`, `actions.anomaly_action` |

---

## 3. Decision Traceability & Reason Taxonomy

Every evaluation produces an immutable [`GovernorDecisionRecord`](file:///Users/ssd/infuse/infuse/contracts/governor.py#L50-L92) containing:
- `decision_id`: Unique identifier formatted as `gov_dec_<execution_id>_<sequence>_<timestamp_ms>`.
- `execution_id`: Target execution identifier.
- `action`: The canonical [`GovernorAction`](file:///Users/ssd/infuse/infuse/contracts/governor.py#L15-L24).
- `reason_codes`: Structured taxonomy codes passed from the state snapshot or policy trigger.
- `message`: Human-readable explanation of why the action was selected.
- `evaluated_state`: Canonical execution state at time of evaluation.
- `signals`: Full dictionary of active signals and observation metadata.
- `effective_policy_id`: Identifier of the evaluated policy.
- `metadata`: Audit dictionary including `triggering_policy_field`, `policy_version`, `evaluation_sequence`, and `has_explicit_policy`.

---

## 4. Precedence & Multiple Condition Handling

Action precedence is rooted in the **frozen contracts**:
1. The **Execution State Engine (Block 20)** resolves multiple simultaneous signals into a single canonical `current_state` using the frozen severity ranking:
   $$\text{RUNAWAY} > \text{PROVIDER\_CONSTRAINED} > \text{QUALITY\_DEGRADED} > \text{COST\_PRESSURE} > \text{NORMAL}$$
2. The **Governor (Block 21)** applies the user-configured [`PolicyActionBindings`](file:///Users/ssd/infuse/infuse/contracts/policy.py#L170-L196) bound to that canonical state and specific trigger reason.
3. All underlying signals and reason codes are retained within `signals` and `reason_codes` for complete auditability.

---

## 5. Explicit Non-Responsibilities

| Non-Responsibility | Assigned Boundary |
| :--- | :--- |
| Physical throttling / delays / sleeping | Block 22 (Execution Control Boundary) |
| Physical execution cancellation / stopping | Block 22 & Block 13 (Lifecycle) |
| Provider / model replacement routing | Block 10 & 11 (Resolver / Router) |
| Retry scheduling and retry execution | Block 12 & 13 (Adapter / Lifecycle) |
| Raw observation ingestion & normalization | Blocks 15–19 (Observers) |
| State classification & evidence synthesis | Block 20 (Execution State Engine) |
| Policy editing, validation, and storage | Block 06 (Policy Manager) |
| External network / database / broker calls | Infrastructure Layer |
