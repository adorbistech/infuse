"""LiteLLM Provider Adapter implementation adhering to IProviderAdapter (Block 31).

Isolates LiteLLM behind the canonical Block 12 IProviderAdapter interface.
Ensures zero external object leakage and complete secret redaction.
"""

import time
from typing import Any, Dict, Iterator, List, Optional

from infuse.contracts.capabilities import ProviderCapability
from infuse.integrations.boundary import IntegrationBoundary
from infuse.providers.errors import ProviderAdapterError, ProviderInvocationError
from infuse.providers.interfaces import IProviderAdapter
from infuse.providers.models import (
    ProviderErrorRecord,
    ProviderExecutionChunk,
    ProviderExecutionRequest,
    ProviderExecutionResponse,
    ProviderUsage,
)

# Check if litellm package is available
try:
    import litellm  # type: ignore

    _LITELLM_AVAILABLE = True
except ImportError:
    litellm = None  # type: ignore
    _LITELLM_AVAILABLE = False


class LiteLLMProviderAdapter(IProviderAdapter):
    """Adapter connecting LiteLLM provider substrate to INFUSE."""

    DEFAULT_MODELS = [
        "litellm/gpt-4o",
        "litellm/gpt-4o-mini",
        "litellm/claude-3-5-sonnet",
        "litellm/claude-3-haiku",
        "litellm/gemini-1.5-pro",
        "litellm/gemini-1.5-flash",
        "litellm/deepseek-chat",
    ]

    def __init__(
        self,
        api_key: Optional[str] = None,
        custom_models: Optional[List[str]] = None,
        allow_simulation: bool = True,
        router_substrate: Optional[Any] = None,
    ):
        self._api_key = api_key
        self._custom_models = custom_models or self.DEFAULT_MODELS
        self._allow_simulation = allow_simulation
        self._router_substrate = router_substrate

    @property
    def provider_id(self) -> str:
        return "litellm"

    @property
    def is_available(self) -> bool:
        """Return True if the underlying litellm library is installed."""
        return _LITELLM_AVAILABLE

    def get_capability(self) -> ProviderCapability:
        return ProviderCapability(
            provider_name=self.provider_id,
            supports_streaming=True,
            supports_tool_calling=True,
            supports_json_mode=True,
            supports_vision=True,
            supports_prompt_caching=True,
            supports_system_messages=True,
            max_context_window=128000,
            max_output_tokens=4096,
        )

    def list_models(self) -> List[str]:
        return list(self._custom_models)

    def supports_model(self, model_id: str) -> bool:
        norm = model_id.lower().strip()
        clean = norm[len("litellm/") :] if norm.startswith("litellm/") else norm
        for m in self._custom_models:
            m_norm = m.lower().strip()
            m_clean = m_norm[len("litellm/") :] if m_norm.startswith("litellm/") else m_norm
            if norm == m_norm or clean == m_clean:
                return True
        return self.is_available

    def execute(self, request: ProviderExecutionRequest) -> ProviderExecutionResponse:
        """Execute request via litellm or safe simulation fallback."""
        start_time = time.time()
        model_name = request.model_id
        if model_name.startswith("litellm/"):
            model_name = model_name[len("litellm/") :]

        # Case 1: litellm library is available
        if self.is_available and litellm is not None:
            try:
                clean_messages = IntegrationBoundary.sanitize_secrets(request.messages)

                kwargs: Dict[str, Any] = {
                    "model": model_name,
                    "messages": clean_messages,
                    "stream": False,
                }
                if self._api_key:
                    kwargs["api_key"] = self._api_key

                # Optional hyperparameters
                if request.parameters:
                    for k, v in request.parameters.items():
                        if k in ("temperature", "max_tokens", "top_p"):
                            kwargs[k] = v

                raw_resp = litellm.completion(**kwargs)

                # Normalize response using IntegrationBoundary
                norm = IntegrationBoundary.normalize_response(
                    raw_resp, provider=self.provider_id, model=request.model_id
                )
                latency_ms = (time.time() - start_time) * 1000.0

                return ProviderExecutionResponse(
                    execution_id=request.execution_id,
                    request_id=request.request_id,
                    provider_id=self.provider_id,
                    model_id=request.model_id,
                    content=norm.content,
                    role=norm.role,
                    usage=ProviderUsage(
                        input_tokens=norm.input_tokens,
                        output_tokens=norm.output_tokens,
                        total_tokens=norm.total_tokens,
                    ),
                    latency_ms=round(latency_ms, 2),
                )
            except Exception as exc:
                err_record = self.normalize_error(exc, model_id=request.model_id)
                raise ProviderInvocationError(
                    message=f"LiteLLM execution failed: {err_record.message}",
                    provider_id=self.provider_id,
                    model_id=request.model_id,
                    error_type=err_record.error_type,
                    error_code=err_record.error_code,
                    is_retryable=err_record.is_retryable,
                    http_status=err_record.http_status,
                ) from exc

        # Case 2: Library is not installed but simulation is permitted
        if self._allow_simulation:
            prompt_text = " ".join(
                str(m.get("content", "")) for m in request.messages if isinstance(m, dict)
            )
            input_tokens = max(1, len(prompt_text.split()))
            output_tokens = 15
            latency_ms = (time.time() - start_time) * 1000.0 + 10.0

            return ProviderExecutionResponse(
                execution_id=request.execution_id,
                request_id=request.request_id,
                provider_id=self.provider_id,
                model_id=request.model_id,
                content=f"[LiteLLM Substrate Simulated Completion for {request.model_id}]",
                role="assistant",
                usage=ProviderUsage(
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=input_tokens + output_tokens,
                    is_authoritative=False,
                ),
                latency_ms=round(latency_ms, 2),
            )

        # Case 3: Library not installed and simulation disabled
        raise ProviderAdapterError(
            "LiteLLM package is not installed. Install with 'pip install litellm' or enable simulation mode.",
            details={"provider_id": self.provider_id},
        )

    def stream(self, request: ProviderExecutionRequest) -> Iterator[ProviderExecutionChunk]:
        """Stream chunks via litellm or simulated deltas."""
        if self.is_available and litellm is not None:
            try:
                model_name = request.model_id
                if model_name.startswith("litellm/"):
                    model_name = model_name[len("litellm/") :]

                clean_messages = IntegrationBoundary.sanitize_secrets(request.messages)
                kwargs = {
                    "model": model_name,
                    "messages": clean_messages,
                    "stream": True,
                }
                if self._api_key:
                    kwargs["api_key"] = self._api_key

                chunks = litellm.completion(**kwargs)
                for idx, chunk in enumerate(chunks):
                    delta_content = ""
                    finish_reason = None
                    if hasattr(chunk, "choices") and chunk.choices:
                        delta = getattr(chunk.choices[0], "delta", None)
                        if delta:
                            delta_content = getattr(delta, "content", "") or ""
                        finish_reason = getattr(chunk.choices[0], "finish_reason", None)

                    yield ProviderExecutionChunk(
                        execution_id=request.execution_id,
                        provider_id=self.provider_id,
                        model_id=request.model_id,
                        delta_content=delta_content,
                        finish_reason=finish_reason,
                        index=idx,
                    )
                return
            except Exception as exc:
                err_record = self.normalize_error(exc, model_id=request.model_id)
                raise ProviderInvocationError(
                    message=f"LiteLLM streaming failed: {err_record.message}",
                    provider_id=self.provider_id,
                    model_id=request.model_id,
                    error_type=err_record.error_type,
                    error_code=err_record.error_code,
                    is_retryable=err_record.is_retryable,
                    http_status=err_record.http_status,
                ) from exc

        # Simulated streaming fallback
        if self._allow_simulation:
            words = [f"[LiteLLM", f"Simulated", f"Stream", f"for", f"{request.model_id}]"]
            for idx, word in enumerate(words):
                is_last = idx == len(words) - 1
                yield ProviderExecutionChunk(
                    execution_id=request.execution_id,
                    provider_id=self.provider_id,
                    model_id=request.model_id,
                    delta_content=word + (" " if not is_last else ""),
                    finish_reason="stop" if is_last else None,
                    index=idx,
                )
            return

        raise ProviderAdapterError(
            "LiteLLM package is not installed.",
            details={"provider_id": self.provider_id},
        )

    def normalize_error(self, raw_error: Any, model_id: Optional[str] = None) -> ProviderErrorRecord:
        """Translate raw exceptions into normalized ProviderErrorRecord."""
        err_payload = IntegrationBoundary.normalize_error(
            raw_error if isinstance(raw_error, Exception) else Exception(str(raw_error)),
            provider=self.provider_id,
            model=model_id or "unknown",
        )
        return ProviderErrorRecord(
            provider_id=self.provider_id,
            model_id=model_id,
            error_type=err_payload.error_type,
            error_code=err_payload.error_code,
            message=err_payload.message,
            is_retryable=err_payload.is_retryable,
            http_status=err_payload.http_status,
        )


__all__ = ["LiteLLMProviderAdapter"]
