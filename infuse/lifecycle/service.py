"""Authoritative Execution Lifecycle Service implementation."""

import time
from typing import List, Optional

from infuse.classifier.interfaces import IWorkloadClassifier
from infuse.classifier.service import WorkloadClassificationService
from infuse.context.interfaces import IExecutionContextService
from infuse.context.models import ExecutionContextRecord
from infuse.context.service import ExecutionContextService
from infuse.contracts.execution import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    ExecutionTelemetry,
)
from infuse.contracts.state import ExecutionState
from infuse.lifecycle.errors import (
    ExecutionAlreadyExistsError,
    ExecutionCancellationError,
    ExecutionNotFoundError,
)
from infuse.lifecycle.interfaces import (
    IExecutionLifecycleRepository,
    IExecutionLifecycleService,
)
from infuse.lifecycle.models import (
    ExecutionLifecycleRecord,
    LifecycleState,
)
from infuse.lifecycle.repository import InMemoryExecutionLifecycleRepository
from infuse.providers.adapters.mock import MockProviderAdapter
from infuse.providers.errors import ProviderAdapterError
from infuse.providers.models import ProviderErrorRecord, ProviderExecutionResponse
from infuse.providers.registry import InMemoryProviderAdapterRegistry
from infuse.providers.service import ProviderAdapterService
from infuse.registry.defaults import get_default_catalog_records
from infuse.registry.interfaces import IProviderModelRegistry
from infuse.registry.repository import InMemoryProviderModelRegistry
from infuse.resolver.interfaces import ICapabilityResolver
from infuse.resolver.resolver import CapabilityResolver
from infuse.resolver.service import CapabilityResolverService
from infuse.router.interfaces import IRouter
from infuse.router.router import DeterministicRouter
from infuse.router.service import RouterService


from infuse.contracts.events import EventSource, EventType, ExecutionEvent
from infuse.events.interfaces import IEventBus
from infuse.events.models import (
    ExecutionCompletedPayload,
    ExecutionFailedPayload,
    ExecutionStartedPayload,
)
import uuid


class ExecutionLifecycleService(IExecutionLifecycleService):
    """Authoritative service coordinating the full execution lifecycle pipeline."""

    def __init__(
        self,
        repository: Optional[IExecutionLifecycleRepository] = None,
        context_service: Optional[IExecutionContextService] = None,
        classifier_service: Optional[WorkloadClassificationService] = None,
        registry: Optional[IProviderModelRegistry] = None,
        resolver_service: Optional[CapabilityResolverService] = None,
        router_service: Optional[RouterService] = None,
        adapter_service: Optional[ProviderAdapterService] = None,
        event_bus: Optional[IEventBus] = None
    ) -> None:
        self.repository = repository or InMemoryExecutionLifecycleRepository()
        self.context_service = context_service or ExecutionContextService()
        self.classifier_service = classifier_service or WorkloadClassificationService()
        self.event_bus = event_bus
        
        # Registry & catalog setup
        self.registry = registry or InMemoryProviderModelRegistry()
        if not self.registry.list_providers():
            providers, models = get_default_catalog_records()
            for p in providers:
                self.registry.register_provider(p)
            for m in models:
                self.registry.register_model(m)

        self.resolver_service = resolver_service or CapabilityResolverService(
            registry=self.registry
        )
        self.router_service = router_service or RouterService()

        # Adapter service setup
        if adapter_service:
            self.adapter_service = adapter_service
        else:
            adapter_reg = InMemoryProviderAdapterRegistry()
            # Register reference mock adapter by default for seamless deterministic execution
            adapter_reg.register(MockProviderAdapter(
                provider_id="mock",
                supported_models=["mock-fast", "mock-pro", "mock-code", "mock-reasoning"]
            ))
            # Also register mock adapter for standard providers if needed in testing
            for p_id in ("openai", "anthropic", "google", "deepseek"):
                adapter_reg.register(MockProviderAdapter(
                    provider_id=p_id,
                    supported_models=[
                        m.model_id for m in self.registry.list_models() if m.provider_id == p_id
                    ] if hasattr(self.registry, "list_models") else None
                ), overwrite=True)
            self.adapter_service = ProviderAdapterService(registry=adapter_reg)

    def _publish_event(
        self,
        event_type: EventType,
        execution_id: str,
        sequence: int,
        payload: dict
    ) -> None:
        """Safely publish an event to the Event Bus if configured."""
        if not self.event_bus:
            return
        try:
            event = ExecutionEvent(
                event_id=f"evt_{uuid.uuid4().hex[:12]}",
                execution_id=execution_id,
                type=event_type,
                source=EventSource.SYSTEM,
                sequence=sequence,
                payload=payload
            )
            self.event_bus.publish(event)
        except Exception:
            # Event delivery issues must never corrupt primary lifecycle execution
            pass

    def create_execution(
        self,
        request: ExecutionRequest,
        execution_id: Optional[str] = None
    ) -> ExecutionLifecycleRecord:
        """Create and persist an execution lifecycle record in CREATED state."""
        ctx_record = self.context_service.create_context(
            request=request,
            execution_id=execution_id
        )
        eid = ctx_record.execution_id

        if self.repository.exists(eid):
            raise ExecutionAlreadyExistsError(eid)

        record = ExecutionLifecycleRecord(
            execution_id=eid,
            request_id=request.request_id,
            task_id=request.task.task_id,
            state=LifecycleState.CREATED,
            context=ctx_record,
            metadata={"session_id": request.execution_context.session_id} if request.execution_context else {}
        )
        return self.repository.save(record)

    def execute(
        self,
        request: ExecutionRequest,
        execution_id: Optional[str] = None
    ) -> ExecutionResult:
        """Orchestrate canonical execution pipeline from request to final result."""
        # 1. Create lifecycle record
        record = self.create_execution(request, execution_id=execution_id)
        eid = record.execution_id
        ctx_record = record.context

        # 2. Transition -> INITIALIZING
        record = self.repository.update_state(
            eid,
            LifecycleState.INITIALIZING,
            reason="Starting workload classification and capability resolution"
        )

        # 3. Workload Classification (Block 08)
        classification = self.classifier_service.classify(ctx_record)
        record.classification = classification

        # 4. Capability Resolution (Block 10) against Registry (Block 09)
        resolution = self.resolver_service.resolve(
            context=ctx_record,
            classification=classification,
            registry=self.registry
        )
        record.resolution = resolution
        self.repository.save(record)

        if not resolution.compatible_targets:
            # Deterministic resolution failure
            error_msg = f"No compatible execution targets found for execution '{eid}'."
            norm_err = ProviderErrorRecord(
                provider_id="none",
                error_type="RESOLUTION_ERROR",
                message=error_msg,
                is_retryable=False
            )
            result = ExecutionResult(
                execution_id=eid,
                request_id=request.request_id,
                status=ExecutionStatus.FAILED,
                error_message=error_msg,
                execution=ExecutionTelemetry(
                    state=ExecutionState.PROVIDER_CONSTRAINED,
                    errors_count=1
                )
            )
            record = self.repository.update_state(eid, LifecycleState.FAILED, reason=error_msg)
            record.error = norm_err
            record.error_message = error_msg
            record.result = result
            self.repository.save(record)
            self._publish_event(
                event_type=EventType.EXECUTION_FAILED,
                execution_id=eid,
                sequence=0,
                payload=ExecutionFailedPayload(
                    request_id=request.request_id,
                    task_id=request.task.task_id,
                    error_type="RESOLUTION_ERROR",
                    error_message=error_msg,
                    is_retryable=False,
                    duration_ms=0.0,
                    status="FAILED"
                ).model_dump()
            )
            return result

        # 5. Routing Decision (Block 11)
        route_decision = self.router_service.route(
            context=ctx_record,
            resolution=resolution,
            classification=classification
        )
        selected_target = route_decision.selected_target
        record.route_decision = route_decision
        record.target = selected_target
        self.repository.save(record)

        record = self.repository.update_state(
            eid,
            LifecycleState.ROUTED,
            reason=f"Selected target '{selected_target.provider_id}:{selected_target.model_id}'"
        )

        # 6. Transition -> RUNNING
        start_perf = time.perf_counter()
        record = self.repository.update_state(
            eid,
            LifecycleState.RUNNING,
            reason=f"Invoking Provider Adapter for '{selected_target.provider_id}'"
        )
        self._publish_event(
            event_type=EventType.EXECUTION_STARTED,
            execution_id=eid,
            sequence=0,
            payload=ExecutionStartedPayload(
                request_id=request.request_id,
                task_id=request.task.task_id,
                provider_id=selected_target.provider_id,
                model_id=selected_target.model_id,
                session_id=request.execution_context.session_id if request.execution_context else None,
                workflow_id=request.execution_context.workflow_id if request.execution_context else None
            ).model_dump()
        )

        # 7. Execute via Provider Adapter (Block 12)
        try:
            prov_response = self.adapter_service.execute_target(
                execution_id=eid,
                request=request,
                target=selected_target,
                stream=False
            )
            duration_ms = (time.perf_counter() - start_perf) * 1000.0

            # 8. Success: Normalize to ExecutionResult
            exec_result = self.adapter_service.normalize_response_to_result(
                response=prov_response,
                request=request
            )
            if exec_result.execution.latency_ms <= 0.0:
                exec_result.execution.latency_ms = duration_ms

            completed_rec = self.repository.update_state(
                eid,
                LifecycleState.COMPLETED,
                reason="Provider execution finished successfully"
            )
            completed_rec.result = exec_result
            completed_rec.duration_ms = duration_ms
            self.repository.save(completed_rec)

            self._publish_event(
                event_type=EventType.EXECUTION_COMPLETED,
                execution_id=eid,
                sequence=1,
                payload=ExecutionCompletedPayload(
                    request_id=request.request_id,
                    task_id=request.task.task_id,
                    provider_id=selected_target.provider_id,
                    model_id=selected_target.model_id,
                    duration_ms=duration_ms,
                    input_tokens=exec_result.execution.input_tokens,
                    output_tokens=exec_result.execution.output_tokens,
                    total_tokens=exec_result.execution.total_tokens,
                    status="COMPLETED"
                ).model_dump()
            )
            return exec_result

        except Exception as exc:
            duration_ms = (time.perf_counter() - start_perf) * 1000.0
            norm_err = self.adapter_service.normalize_error(
                provider_id=selected_target.provider_id,
                error=exc,
                model_id=selected_target.model_id
            )

            exec_result = ExecutionResult(
                execution_id=eid,
                request_id=request.request_id,
                status=ExecutionStatus.FAILED,
                error_message=norm_err.message,
                execution=ExecutionTelemetry(
                    provider=selected_target.provider_id,
                    model=selected_target.model_id,
                    latency_ms=duration_ms,
                    errors_count=1,
                    state=ExecutionState.PROVIDER_CONSTRAINED,
                    metadata={
                        "error_record": norm_err.model_dump(),
                        "is_retryable": norm_err.is_retryable,
                        "http_status": norm_err.http_status,
                        "error_code": norm_err.error_code
                    }
                )
            )

            failed_rec = self.repository.update_state(
                eid,
                LifecycleState.FAILED,
                reason=norm_err.message
            )
            failed_rec.error = norm_err
            failed_rec.error_message = norm_err.message
            failed_rec.duration_ms = duration_ms
            failed_rec.result = exec_result
            self.repository.save(failed_rec)

            self._publish_event(
                event_type=EventType.EXECUTION_FAILED,
                execution_id=eid,
                sequence=1,
                payload=ExecutionFailedPayload(
                    request_id=request.request_id,
                    task_id=request.task.task_id,
                    provider_id=selected_target.provider_id,
                    model_id=selected_target.model_id,
                    error_type=norm_err.error_type if hasattr(norm_err, "error_type") else "PROVIDER_ERROR",
                    error_message=norm_err.message if hasattr(norm_err, "message") else str(norm_err),
                    is_retryable=norm_err.is_retryable if hasattr(norm_err, "is_retryable") else False,
                    http_status=norm_err.http_status if hasattr(norm_err, "http_status") else None,
                    duration_ms=duration_ms,
                    status="FAILED"
                ).model_dump()
            )
            return exec_result

    def get_execution(self, execution_id: str) -> Optional[ExecutionLifecycleRecord]:
        """Retrieve execution record by execution_id."""
        return self.repository.get(execution_id)

    def list_executions(
        self,
        state: Optional[LifecycleState] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ExecutionLifecycleRecord]:
        """List execution records with optional filtering."""
        return self.repository.list_executions(state=state, limit=limit, offset=offset)

    def cancel_execution(
        self,
        execution_id: str,
        reason: Optional[str] = None
    ) -> ExecutionLifecycleRecord:
        """Cancel an execution if not in a terminal state."""
        record = self.repository.get(execution_id)
        if not record:
            raise ExecutionNotFoundError(execution_id)

        state_str = record.state.value if hasattr(record.state, "value") else str(record.state)
        if record.state in (LifecycleState.COMPLETED, LifecycleState.FAILED, LifecycleState.CANCELLED, LifecycleState.TERMINATED):
            raise ExecutionCancellationError(
                execution_id=execution_id,
                reason=f"Execution is already in terminal state '{state_str}'."
            )

        cancel_msg = reason or "Execution cancelled by caller."

        # Update lifecycle state
        updated = self.repository.update_state(
            execution_id=execution_id,
            new_state=LifecycleState.CANCELLED,
            reason=cancel_msg
        )
        updated.cancellation_reason = cancel_msg

        if not updated.result:
            updated.result = ExecutionResult(
                execution_id=execution_id,
                request_id=record.request_id,
                status=ExecutionStatus.STOPPED,
                error_message=cancel_msg,
                execution=ExecutionTelemetry(
                    provider=record.target.provider_id if record.target else None,
                    model=record.target.model_id if record.target else None,
                    state=ExecutionState.NORMAL
                )
            )

        return self.repository.save(updated)
