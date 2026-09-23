"""Provider Adapter Service boundary."""

from typing import Any, Dict, List, Optional

from infuse.contracts.execution import (
    ExecutionContext,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    ExecutionTelemetry,
    NormalizedResponse,
)
from infuse.contracts.state import ExecutionState
from infuse.providers.errors import AdapterNotFoundError
from infuse.providers.interfaces import IProviderAdapter, IProviderAdapterRegistry
from infuse.providers.models import (
    ProviderErrorRecord,
    ProviderExecutionRequest,
    ProviderExecutionResponse,
    ProviderUsage,
)
from infuse.providers.registry import InMemoryProviderAdapterRegistry
from infuse.router.models import RouteTarget


class ProviderAdapterService:
    """Service boundary orchestrating provider adapter resolution, translation, and normalized execution."""

    def __init__(self, registry: Optional[IProviderAdapterRegistry] = None) -> None:
        self.registry = registry or InMemoryProviderAdapterRegistry()

    def register_adapter(self, adapter: IProviderAdapter, overwrite: bool = False) -> None:
        """Register an adapter instance."""
        self.registry.register(adapter, overwrite=overwrite)

    def get_adapter(self, provider_id: str) -> IProviderAdapter:
        """Resolve adapter by provider ID."""
        return self.registry.get(provider_id)

    def has_adapter(self, provider_id: str) -> bool:
        """Check if adapter exists for provider ID."""
        return self.registry.has(provider_id)

    def list_providers(self) -> List[str]:
        """List all registered provider IDs."""
        return self.registry.list_providers()

    def translate_request(
        self,
        execution_id: str,
        request: ExecutionRequest,
        target: RouteTarget,
        stream: bool = False
    ) -> ProviderExecutionRequest:
        """Translate universal ExecutionRequest into normalized ProviderExecutionRequest."""
        return ProviderExecutionRequest(
            execution_id=execution_id,
            request_id=request.request_id,
            task_id=request.task.task_id,
            provider_id=target.provider_id,
            model_id=target.model_id,
            messages=request.request.messages,
            tools=request.request.tools,
            parameters=request.request.parameters,
            raw_payload=request.request.raw_payload,
            stream=stream,
            metadata={
                "target_context_window": target.context_window,
                "target_max_output_tokens": target.max_output_tokens,
                **(request.execution_context.metadata if request.execution_context else {})
            }
        )

    def execute(self, request: ProviderExecutionRequest) -> ProviderExecutionResponse:
        """Execute request using registered provider adapter."""
        adapter = self.registry.get(request.provider_id)
        return adapter.execute(request)

    def execute_target(
        self,
        execution_id: str,
        request: ExecutionRequest,
        target: RouteTarget,
        stream: bool = False
    ) -> ProviderExecutionResponse:
        """Translate and execute universal execution request for a routed target."""
        prov_req = self.translate_request(
            execution_id=execution_id,
            request=request,
            target=target,
            stream=stream
        )
        return self.execute(prov_req)

    def normalize_response_to_result(
        self,
        response: ProviderExecutionResponse,
        request: ExecutionRequest
    ) -> ExecutionResult:
        """Normalize ProviderExecutionResponse into universal ExecutionResult envelope."""
        norm_resp = NormalizedResponse(
            content=response.content,
            role=response.role,
            tool_calls=response.tool_calls,
            finish_reason=response.finish_reason,
            raw_response=response.raw_response
        )

        telemetry = ExecutionTelemetry(
            provider=response.provider_id,
            model=response.model_id,
            input_tokens=response.usage.input_tokens,
            cached_tokens=response.usage.cached_tokens,
            output_tokens=response.usage.output_tokens,
            total_tokens=response.usage.total_tokens,
            latency_ms=response.latency_ms,
            requests_count=1,
            retries_count=0,
            tool_calls_count=len(response.tool_calls) if response.tool_calls else 0,
            state=ExecutionState.NORMAL,
            metadata={
                "provider_request_id": response.provider_request_id,
                "is_authoritative": response.usage.is_authoritative,
                **(response.metadata or {})
            }
        )

        return ExecutionResult(
            execution_id=response.execution_id,
            request_id=response.request_id,
            status=ExecutionStatus.COMPLETED,
            response=norm_resp,
            execution=telemetry
        )

    def normalize_error(
        self,
        provider_id: str,
        error: Any,
        model_id: Optional[str] = None
    ) -> ProviderErrorRecord:
        """Normalize provider-specific error using adapter or generic normalization."""
        if self.registry.has(provider_id):
            adapter = self.registry.get(provider_id)
            return adapter.normalize_error(error, model_id=model_id)

        # Fallback generic normalization
        msg = str(error)
        http_status = getattr(error, "status_code", None) or getattr(error, "http_status", None)
        error_code = getattr(error, "code", None) or getattr(error, "error_code", None)
        is_retryable = http_status in (429, 500, 502, 503, 504) if http_status else False

        return ProviderErrorRecord(
            provider_id=provider_id,
            model_id=model_id,
            error_type="PROVIDER_ERROR",
            error_code=str(error_code) if error_code else None,
            message=msg,
            is_retryable=is_retryable,
            http_status=http_status,
            raw_error={"error_str": str(error)} if not isinstance(error, dict) else error
        )
