# INFUSE Execution Context Specification

**Milestone:** Block 07 (Execution Context)  
**Status:** Frozen  
**Schema Version:** `1.0.0`  
**Contract Baseline:** Block 00 Execution Contract ([`infuse/contracts/execution.py`](file:///Users/ssd/infuse/infuse/contracts/execution.py))  
**API Baseline:** Block 05 Universal HTTP API ([`POST /v1/execute`](file:///Users/ssd/infuse/infuse/api/routes/execution.py))  

---

## 1. Overview & Architectural Role

The **Execution Context** establishes the canonical contextual identity and descriptive metadata surrounding an INFUSE execution.

It serves as the stable context envelope that subsequent execution pipeline stages consume.

```text
┌────────────────────────────────────────────────────────┐
│               UNIVERSAL HTTP API LAYER                 │
│                                                        │
│                    POST /v1/execute                    │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│                   EXECUTION CONTEXT                    │
│                                                        │
│  • Stable Identity (execution_id, request_id, parent)  │
│  • Task Context & Workload Hints                       │
│  • Agent & Runtime Environment Context                 │
│  • Requested Capabilities & Constraints                │
│  • Descriptive Governance Policy Reference             │
│  • Operation Payload Summary                           │
│  • Structural & Invariant Validation                   │
│  • Deterministic Normalization & Immutability          │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
         Future Workload Classifier (Block 08)
                            │
                            ▼
         Future Provider / Model Registry (Block 09)
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
> **"Execution Context describes an execution. It does not classify, route, govern, or execute it."**
> 
> * **Context DESCRIBES:** Answers *"What is this execution?"*
> * **Classifier INTERPRETS:** Block 08 derives workload complexity and classification.
> * **Registry TRACKS:** Block 09 registers providers and models.
> * **Router SELECTS:** Block 11 selects optimal provider and model.
> * **Observers MEASURE:** Blocks 15–19 record live execution metrics.
> * **Governor DECIDES:** Block 21 evaluates policy rules against live state.

---

## 2. Context Identity & Structure

[`ExecutionContextRecord`](file:///Users/ssd/infuse/infuse/context/models.py#L173-L224) formalizes 6 distinct descriptive dimensions:

### 1. Identity & Lineage
* `execution_id`: Unique execution identifier (e.g. `exec_3e4f7a1b`).
* `request_id`: Unique caller/gateway request ID.
* `parent_execution_id`: Optional parent execution ID for sub-task trees.
* `created_at`: ISO-8601 UTC creation timestamp.

### 2. Task Context
* `task_id`: Caller-provided task identifier.
* `description`: Human-readable task description.
* `workload_hint`: Descriptive hint provided by the caller (e.g. `"coding"`, `"research"`, `"chat"`). *Not an algorithmic classification.*
* `tags`: Categorical index tags.
* `metadata`: Additional task key-values.

### 3. Agent & Client Context
* `agent_id`: Identifier of the executing autonomous agent.
* `agent_name`: Human-readable agent archetype.
* `agent_type`: Category of the agent (e.g. `assistant`, `researcher`, `coder`).
* `client_version`: Client SDK/CLI/MCP version.
* `runtime_version`: Underlying runtime environment version.
* `execution_mode`: Mode (e.g. `autonomous`, `human_in_the_loop`).

### 4. Runtime & Environment Context
* `session_id`: User/workflow session grouping multiple executions.
* `workflow_id`: Pipeline identifier.
* `step_index`: Step index in multi-step trajectories ($\ge 0$).
* `isolation_pool`: Security or tenant isolation pool.
* `environment`: Environment name (`production`, `staging`, `development`).
* `region`: Geographic or datacenter region.

### 5. Capabilities & Constraints
* `requested_capabilities`: Requested capabilities (`tools`, `web`, `vision`, `structured_output`).
* `min_context_tokens`: Minimum required context window size.
* `max_latency_ms`: Requested latency ceiling.
* `preferred_providers` / `excluded_providers`: Caller preference lists (disjoint).
* `preferred_models` / `excluded_models`: Caller preference lists (disjoint).

### 6. Policy Reference & Operation Summary
* `policy_id`: Referenced governance policy ID (`"pol_default"` or custom).
* `policy_version`: Pinned policy revision string if specified.
* `has_inline_policy`: Boolean indicating if inline overrides were attached.
* `message_count`, `has_tools`, `tool_count`, `parameter_keys`: Descriptive operation summary.

---

## 3. Validation & Normalization

* **Validation ([`validate_execution_context`](file:///Users/ssd/infuse/infuse/context/validation.py#L13-L67)):**
  * Guarantees non-empty `execution_id`, `request_id`, and `task_id`.
  * Enforces non-negative `step_index` and `min_context_tokens`.
  * Verifies disjoint set condition for preferred vs excluded providers and models.
  * Ensures schema version is `"1.0.0"`.
* **Normalization ([`normalize_execution_context`](file:///Users/ssd/infuse/infuse/context/normalization.py#L38-L128)):**
  * Trims all string identifiers and text fields.
  * Deduplicates lists while preserving insertion order.
  * Generates standard ISO-8601 UTC timestamp if omitted.
  * Normalizes schema version.

---

## 4. Immutability & Deep-Copy Snapshots

* Once built, the `ExecutionContextRecord` represents an immutable snapshot of execution inputs.
* All repository queries, builder outputs, and service interactions return independent deep copies (`model_copy(deep=True)`).
* Caller modifications to retrieved context objects cannot mutate the persisted execution context ledger.

---

## 5. API & Service Integration

* [`DefaultExecutionService`](file:///Users/ssd/infuse/infuse/api/services/default.py#L36-L95) instantiates and validates the canonical execution context via [`IExecutionContextService`](file:///Users/ssd/infuse/infuse/context/interfaces.py#L42-L65).
* `POST /v1/execute` persists the execution context and uses its `execution_id` as the authoritative execution identity.
* Context validation failures map cleanly to HTTP `422 Unprocessable Entity` (`VALIDATION_ERROR`).
