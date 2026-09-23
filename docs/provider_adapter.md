# INFUSE Provider Adapter Layer Specification

**Milestone:** Block 12 (Provider Adapter Layer)  
**Status:** Complete / Ready for Freeze  
**Schema Version:** `1.0.0`  

---

## 1. Overview & Purpose

The **Provider Adapter Layer** establishes the universal execution and translation boundary between INFUSE's core orchestration/governance architecture and concrete AI providers (such as OpenAI, Anthropic, Google Gemini, DeepSeek, LiteLLM substrate, or custom enterprise gateways).

```text
┌────────────────────────────────────────────────────────┐
│                   ROUTER (Block 11)                    │
│  • Selects RouteTarget (provider_id, model_id)         │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│             PROVIDER ADAPTER SERVICE (Block 12)        │
│  • Resolves adapter instance from Adapter Registry     │
│  • Translates ExecutionRequest -> ProviderExecutionReq │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│               PROVIDER ADAPTER (Block 12)              │
│  • Encapsulates provider protocol wire format          │
│  • Executes request or emits streaming deltas          │
│  • Normalizes responses, usage, and error telemetry    │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
                     Target AI Provider
```

> [!IMPORTANT]
> **Core Architectural Guarantee:**  
> **"Provider adapters are translation boundaries. They normalize requests into provider formats and normalize responses/errors into INFUSE contracts. Provider adapters do NOT route, do NOT enforce policy, do NOT make Governor decisions, do NOT calculate billing economics, and do NOT execute retry loops."**

---

## 2. Universal Adapter Contract

All provider adapters implement the [`IProviderAdapter`](file:///Users/ssd/infuse/infuse/providers/interfaces.py#L14-L45) interface:

* `provider_id -> str`: Stable identifier (e.g. `'openai'`, `'anthropic'`, `'google'`, `'mock'`).
* `get_capability() -> ProviderCapability`: Exposes declared features (streaming, tool calling, caching, vision, structured output, context window).
* `list_models() -> List[str]`: Supported model identifiers.
* `supports_model(model_id: str) -> bool`: Model compatibility predicate.
* `execute(request: ProviderExecutionRequest) -> ProviderExecutionResponse`: Synchronous execution.
* `stream(request: ProviderExecutionRequest) -> Iterator[ProviderExecutionChunk]`: Streaming execution delta generator.
* `normalize_error(raw_error: Any, model_id: Optional[str]) -> ProviderErrorRecord`: Translates provider exceptions into normalized error records.

---

## 3. Adapter Registration & Resolution

* [`IProviderAdapterRegistry`](file:///Users/ssd/infuse/infuse/providers/interfaces.py#L48-L75): Abstract catalog interface.
* [`InMemoryProviderAdapterRegistry`](file:///Users/ssd/infuse/infuse/providers/registry.py#L8-L53): Thread-safe in-memory registry implementation.
* Duplicate registrations raise [`DuplicateAdapterError`](file:///Users/ssd/infuse/infuse/providers/errors.py#L22-L29) unless `overwrite=True`.
* Unregistered provider lookups raise [`AdapterNotFoundError`](file:///Users/ssd/infuse/infuse/providers/errors.py#L13-L20).

---

## 4. Request Translation & Response Normalization

### Request Translation
Universal [`ExecutionRequest`](file:///Users/ssd/infuse/infuse/contracts/execution.py#L144-L170) and routed [`RouteTarget`](file:///Users/ssd/infuse/infuse/router/models.py#L30-L48) are translated into [`ProviderExecutionRequest`](file:///Users/ssd/infuse/infuse/providers/models.py#L42-L73):
- Preserves `execution_id`, `request_id`, and `task_id`.
- Forwards `messages`, `tools`, `parameters`, and `raw_payload`.

### Response Normalization
[`ProviderExecutionResponse`](file:///Users/ssd/infuse/infuse/providers/models.py#L76-L113) normalizes completion payloads:
- `content`, `role`, `tool_calls`, `finish_reason`.
- [`ProviderUsage`](file:///Users/ssd/infuse/infuse/providers/models.py#L14-L26): `input_tokens`, `output_tokens`, `total_tokens`, `cached_tokens`, and `is_authoritative` flag.
- `provider_request_id` and `latency_ms`.
- Normalized into standard [`ExecutionResult`](file:///Users/ssd/infuse/infuse/contracts/execution.py#L227-L257) with [`ExecutionTelemetry`](file:///Users/ssd/infuse/infuse/contracts/execution.py#L196-L225).

---

## 5. Error Normalization & Retryability

Provider errors are translated into [`ProviderErrorRecord`](file:///Users/ssd/infuse/infuse/providers/models.py#L29-L40) and raised as [`ProviderInvocationError`](file:///Users/ssd/infuse/infuse/providers/errors.py#L41-L61):
- `is_retryable`: Automatically flagged for transient errors (HTTP 429, 500, 502, 503, 504).
- `http_status` and `error_code` extracted without leaking provider SDK exceptions into core.
- The adapter *reports* retryability; higher-level lifecycle/policy layers decide whether to retry.

---

## 6. Deterministic Reference / Mock Adapter

[`MockProviderAdapter`](file:///Users/ssd/infuse/infuse/providers/adapters/mock.py#L19-L136) (aliased as [`DeterministicReferenceAdapter`](file:///Users/ssd/infuse/infuse/providers/adapters/mock.py#L139)) provides complete in-memory simulation:
- Requires **zero API keys** and makes **zero network requests**.
- Supports mock completion text, custom usage configurations, simulated error injection, tool call generation, and token streaming chunks.
- Enables hermetic test execution across all INFUSE test suites.
