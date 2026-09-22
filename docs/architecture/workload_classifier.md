# INFUSE Workload Classifier Specification

**Milestone:** Block 08 (Workload Classifier)  
**Status:** Frozen  
**Schema Version:** `1.0.0`  
**Input Contract:** Block 07 Execution Context ([`infuse/context/models.py`](file:///Users/ssd/infuse/infuse/context/models.py))  

---

## 1. Overview & Architectural Role

The **Workload Classifier** interprets the descriptive [`ExecutionContextRecord`](file:///Users/ssd/infuse/infuse/context/models.py#L173-L224) and derives a normalized, multi-dimensional characterization of execution demands.

It answers:
> *"What kind of workload is this, and what execution characteristics does it exhibit?"*

It does **not** answer:
> *"Which provider/model should execute it?"*  
> *"Should execution be stopped or throttled?"*  
> *"Which routing action should be taken?"*

```text
┌────────────────────────────────────────────────────────┐
│               EXECUTION CONTEXT (Block 07)             │
│                                                        │
│  • Stable Identity (execution_id, request_id)          │
│  • Task Context & Workload Hints                       │
│  • Runtime & Agent Environment Metadata                │
│  • Constraints & Capability Requests                   │
│  • Operation Payload Summary                           │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│             WORKLOAD CLASSIFIER (Block 08)             │
│                                                        │
│  • Canonical Category & Secondary Categories           │
│  • Multi-Dimensional Resource Intensities              │
│  • Deterministic Complexity Scoring [0.0, 1.0]         │
│  • Capability Demands (Tools, Web, Vision, JSON)       │
│  • Explainability Rationale & Evidence Ledger          │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
      Future Provider & Model Registry (Block 09)
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
> **"Workload Classification describes execution characteristics. It does not select a provider, select a model, route execution, enforce policy, or issue Governor actions."**

---

## 2. Classification Contracts & Vocabulary

### 1. Canonical Workload Categories ([`WorkloadCategory`](file:///Users/ssd/infuse/infuse/classifier/models.py#L11-L24))
* `CONVERSATIONAL`: General dialog, chat, or back-and-forth communication.
* `REASONING`: Multi-step reasoning, mathematical proof, logic analysis.
* `CODING`: Code generation, debugging, refactoring, or software architecture.
* `STRUCTURED_GENERATION`: Strict JSON/YAML schema emission, function payload formulation.
* `TOOL_USE`: Multi-tool coordination, tool-loop execution.
* `WEB_ENABLED`: Live web access, browsing, real-time search.
* `MULTIMODAL`: Image/vision processing, visual document inspection.
* `EXTRACTION`: Data harvesting, web scraping, unstructured text parsing.
* `TRANSFORMATION`: Data translation, format transformation, normalization.
* `WORKFLOW_EXECUTION`: Complex multi-step agent trajectory or workflow pipeline.
* `UNKNOWN`: Unclassified due to absence of signals or empty context.

### 2. Multi-Dimensional Characteristics ([`WorkloadDimensions`](file:///Users/ssd/infuse/infuse/classifier/models.py#L38-L76))
* `requires_tools`: Boolean tool execution requirement.
* `requires_web`: Boolean web access requirement.
* `requires_vision`: Boolean multimodal vision requirement.
* `requires_structured_output`: Boolean structured output requirement.
* `context_intensity`: Discrete magnitude (`NONE`, `LOW`, `MEDIUM`, `HIGH`).
* `tool_intensity`: Discrete magnitude (`NONE`, `LOW`, `MEDIUM`, `HIGH`).
* `latency_sensitivity`: Urgency (`LOW`, `MEDIUM`, `HIGH`).
* `estimated_context_tokens`, `message_count`, `tool_count`: Extracted numeric counts.

### 3. Complexity Scoring ([`ComplexityLevel`](file:///Users/ssd/infuse/infuse/classifier/models.py#L27-L32))
* `complexity_score`: Deterministic float bounded in $[0.0, 1.0]$.
* `complexity_level`:
  * `LOW`: score $< 0.30$
  * `MODERATE`: $0.30 \le \text{score} < 0.60$
  * `HIGH`: $0.60 \le \text{score} < 0.85$
  * `VERY_HIGH`: $\text{score} \ge 0.85$

---

## 3. Determinism & Explainability Evidence

* **Determinism:** Given identical `ExecutionContextRecord` inputs, the classifier produces 100% byte-for-byte identical classifications.
* **Explainability Evidence:** Every classification includes an ordered list of human-readable rationale strings in `evidence` explaining each categorical mapping, dimensional calculation, and complexity contribution.

---

## 4. Service Boundaries

* **Block 09 Boundary (Provider & Model Registry):** The classifier has zero awareness of registered providers, model lists, or pricing.
* **Block 10 Boundary (Capability Resolver):** The classifier identifies descriptive capability *demands*; Block 10 resolves those demands against actual model capabilities.
* **Block 11 Boundary (Router):** The classifier produces descriptive characteristics; the Router selects execution routes.
* **Block 21 Boundary (Governor):** The classifier evaluates workload attributes; the Governor evaluates policy rules against live execution state.
