"""Deterministic Mock / Reference Provider Adapter for testing and simulation."""

from typing import Any, Callable, Dict, Iterator, List, Optional
from uuid import uuid4

from infuse.contracts.capabilities import ProviderCapability
from infuse.providers.adapters.base import BaseProviderAdapter
from infuse.providers.errors import ProviderInvocationError
from infuse.providers.models import (
    ProviderErrorRecord,
    ProviderExecutionChunk,
    ProviderExecutionRequest,
    ProviderExecutionResponse,
    ProviderUsage,
)


class MockProviderAdapter(BaseProviderAdapter):
    """Deterministic reference adapter requiring zero external credentials and zero network calls."""

    def __init__(
        self,
        provider_id: str = "mock",
        supported_models: Optional[List[str]] = None,
        capability: Optional[ProviderCapability] = None,
        default_content: str = "Deterministic mock completion.",
        default_usage: Optional[ProviderUsage] = None,
        error_generator: Optional[Callable[[ProviderExecutionRequest], Optional[Exception]]] = None,
        latency_ms: float = 12.5
    ) -> None:
        models = supported_models or ["mock-fast", "mock-pro", "mock-reasoning", "mock-code"]
        super().__init__(
            provider_id=provider_id,
            supported_models=models,
            capability=capability or ProviderCapability(
                provider_name=provider_id,
                supported_models=models,
                supports_streaming=True,
                supports_tool_calling=True,
                supports_caching=True,
                supports_vision=True,
                supports_structured_output=True,
                max_context_window=128000
            )
        )
        self.default_content = default_content
        self.default_usage = default_usage or ProviderUsage(
            input_tokens=150,
            output_tokens=45,
            total_tokens=195,
            cached_tokens=0,
            is_authoritative=True
        )
        self.error_generator = error_generator
        self.latency_ms = latency_ms
        self.execution_history: List[ProviderExecutionRequest] = []

    def execute(self, request: ProviderExecutionRequest) -> ProviderExecutionResponse:
        """Execute request deterministically in-memory."""
        self._validate_request(request)
        self.execution_history.append(request)

        # Check simulated error hook
        if self.error_generator:
            err = self.error_generator(request)
            if err:
                norm_err = self.normalize_error(err, model_id=request.model_id)
                raise ProviderInvocationError(
                    message=norm_err.message,
                    provider_id=self.provider_id,
                    model_id=request.model_id,
                    error_type=norm_err.error_type,
                    error_code=norm_err.error_code,
                    is_retryable=norm_err.is_retryable,
                    http_status=norm_err.http_status,
                    provider_request_id=norm_err.provider_request_id,
                    raw_error=norm_err.raw_error
                )

        req_id = f"mock_req_{uuid4().hex[:10]}"
        tool_calls = None
        if request.tools and request.parameters.get("mock_tool_call"):
            tool_calls = [{
                "id": f"call_{uuid4().hex[:8]}",
                "type": "function",
                "function": {
                    "name": request.tools[0].get("name", "test_tool"),
                    "arguments": "{}"
                }
            }]

        content = request.parameters.get("mock_content", self.default_content)
        usage = request.parameters.get("mock_usage", self.default_usage)

        return ProviderExecutionResponse(
            execution_id=request.execution_id,
            request_id=request.request_id,
            provider_id=self.provider_id,
            model_id=request.model_id,
            content=content,
            role="assistant",
            tool_calls=tool_calls,
            finish_reason="tool_calls" if tool_calls else "stop",
            usage=usage,
            latency_ms=self.latency_ms,
            provider_request_id=req_id,
            raw_response={"mock": True, "provider_request_id": req_id},
            metadata={"adapter": "MockProviderAdapter"}
        )

    def stream(self, request: ProviderExecutionRequest) -> Iterator[ProviderExecutionChunk]:
        """Stream chunks deterministically."""
        self._validate_request(request)
        self.execution_history.append(request)

        if self.error_generator:
            err = self.error_generator(request)
            if err:
                norm_err = self.normalize_error(err, model_id=request.model_id)
                raise ProviderInvocationError(
                    message=norm_err.message,
                    provider_id=self.provider_id,
                    model_id=request.model_id,
                    error_type=norm_err.error_type,
                    error_code=norm_err.error_code,
                    is_retryable=norm_err.is_retryable,
                    http_status=norm_err.http_status
                )

        req_id = f"mock_req_{uuid4().hex[:10]}"
        content = request.parameters.get("mock_content", self.default_content)
        words = content.split(" ")

        for idx, word in enumerate(words):
            is_last = (idx == len(words) - 1)
            delta = word + (" " if not is_last else "")
            yield ProviderExecutionChunk(
                execution_id=request.execution_id,
                provider_id=self.provider_id,
                model_id=request.model_id,
                delta_content=delta,
                finish_reason="stop" if is_last else None,
                usage=self.default_usage if is_last else None,
                index=idx,
                provider_request_id=req_id
            )


# Alias for clarity in architectural tests
DeterministicReferenceAdapter = MockProviderAdapter
