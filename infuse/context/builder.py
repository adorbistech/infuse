"""Execution Context Builder and Factory.

Constructs canonical ExecutionContextRecord snapshots from normalized execution requests
or explicit parameters, applying structural validation and deterministic normalization.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from infuse.context.models import (
    AgentContextInfo,
    ConstraintContextInfo,
    ExecutionContextRecord,
    OperationContextInfo,
    PolicyContextInfo,
    RuntimeContextInfo,
    TaskContextInfo,
)
from infuse.context.normalization import normalize_execution_context
from infuse.context.validation import validate_execution_context
from infuse.contracts.execution import ExecutionRequest
from infuse.version import SCHEMA_VERSION


class ExecutionContextBuilder:
    """Builder for constructing canonical ExecutionContextRecord envelopes."""

    def __init__(self) -> None:
        self._execution_id: Optional[str] = None
        self._request_id: Optional[str] = None
        self._parent_execution_id: Optional[str] = None
        self._created_at: Optional[str] = None
        self._task: Optional[TaskContextInfo] = None
        self._agent: Optional[AgentContextInfo] = None
        self._runtime: Optional[RuntimeContextInfo] = None
        self._constraints: Optional[ConstraintContextInfo] = None
        self._policy: Optional[PolicyContextInfo] = None
        self._operation: Optional[OperationContextInfo] = None
        self._extensions: Dict[str, Any] = {}

    def set_identity(
        self,
        execution_id: str,
        request_id: str,
        parent_execution_id: Optional[str] = None,
        created_at: Optional[str] = None
    ) -> "ExecutionContextBuilder":
        self._execution_id = execution_id
        self._request_id = request_id
        self._parent_execution_id = parent_execution_id
        self._created_at = created_at or datetime.now(timezone.utc).isoformat()
        return self

    def set_task(
        self,
        task_id: str,
        description: Optional[str] = None,
        workload_hint: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "ExecutionContextBuilder":
        self._task = TaskContextInfo(
            task_id=task_id,
            description=description,
            workload_hint=workload_hint,
            tags=tags or [],
            metadata=metadata or {}
        )
        return self

    def set_agent(
        self,
        agent_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        agent_type: Optional[str] = None,
        client_version: Optional[str] = None,
        runtime_version: Optional[str] = None,
        execution_mode: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "ExecutionContextBuilder":
        self._agent = AgentContextInfo(
            agent_id=agent_id,
            agent_name=agent_name,
            agent_type=agent_type,
            client_version=client_version,
            runtime_version=runtime_version,
            execution_mode=execution_mode,
            metadata=metadata or {}
        )
        return self

    def set_runtime(
        self,
        session_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        step_index: int = 0,
        isolation_pool: Optional[str] = None,
        environment: Optional[str] = None,
        region: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "ExecutionContextBuilder":
        self._runtime = RuntimeContextInfo(
            session_id=session_id,
            workflow_id=workflow_id,
            step_index=step_index,
            isolation_pool=isolation_pool,
            environment=environment,
            region=region,
            metadata=metadata or {}
        )
        return self

    def set_constraints(
        self,
        requested_capabilities: Optional[List[str]] = None,
        min_context_tokens: Optional[int] = None,
        max_latency_ms: Optional[float] = None,
        supports_tools: bool = False,
        supports_vision: bool = False,
        supports_structured_output: bool = False,
        preferred_providers: Optional[List[str]] = None,
        excluded_providers: Optional[List[str]] = None,
        preferred_models: Optional[List[str]] = None,
        excluded_models: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "ExecutionContextBuilder":
        self._constraints = ConstraintContextInfo(
            requested_capabilities=requested_capabilities or [],
            min_context_tokens=min_context_tokens,
            max_latency_ms=max_latency_ms,
            supports_tools=supports_tools,
            supports_vision=supports_vision,
            supports_structured_output=supports_structured_output,
            preferred_providers=preferred_providers or [],
            excluded_providers=excluded_providers or [],
            preferred_models=preferred_models or [],
            excluded_models=excluded_models or [],
            metadata=metadata or {}
        )
        return self

    def set_policy(
        self,
        policy_id: Optional[str] = "pol_default",
        policy_version: Optional[str] = None,
        has_inline_policy: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "ExecutionContextBuilder":
        self._policy = PolicyContextInfo(
            policy_id=policy_id or "pol_default",
            policy_version=policy_version,
            has_inline_policy=has_inline_policy,
            metadata=metadata or {}
        )
        return self

    def set_operation(
        self,
        message_count: int = 0,
        has_tools: bool = False,
        tool_count: int = 0,
        parameter_keys: Optional[List[str]] = None,
        has_raw_payload: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "ExecutionContextBuilder":
        self._operation = OperationContextInfo(
            message_count=message_count,
            has_tools=has_tools,
            tool_count=tool_count,
            parameter_keys=parameter_keys or [],
            has_raw_payload=has_raw_payload,
            metadata=metadata or {}
        )
        return self

    def set_extensions(self, extensions: Dict[str, Any]) -> "ExecutionContextBuilder":
        self._extensions = dict(extensions)
        return self

    @classmethod
    def from_execution_request(
        cls,
        request: ExecutionRequest,
        execution_id: Optional[str] = None,
        parent_execution_id: Optional[str] = None
    ) -> "ExecutionContextBuilder":
        """Instantiate a builder pre-populated from an ExecutionRequest."""
        builder = cls()
        exec_id = execution_id or f"exec_{uuid.uuid4().hex[:8]}"
        created_at = datetime.now(timezone.utc).isoformat()

        builder.set_identity(
            execution_id=exec_id,
            request_id=request.request_id,
            parent_execution_id=parent_execution_id,
            created_at=created_at
        )

        # Task
        builder.set_task(
            task_id=request.task.task_id,
            description=request.task.description,
            workload_hint=request.task.workload_hint,
            tags=list(request.task.tags),
            metadata=dict(request.task.metadata)
        )

        # Agent
        agent_id = request.execution_context.agent_id
        client_version = request.execution_context.client_version
        agent_meta = dict(request.execution_context.metadata)
        agent_name = agent_meta.get("agent_name") or agent_id
        agent_type = agent_meta.get("agent_type")
        execution_mode = agent_meta.get("execution_mode")
        runtime_version = agent_meta.get("runtime_version")

        builder.set_agent(
            agent_id=agent_id,
            agent_name=agent_name,
            agent_type=agent_type,
            client_version=client_version,
            runtime_version=runtime_version,
            execution_mode=execution_mode,
            metadata=agent_meta
        )

        # Runtime
        builder.set_runtime(
            session_id=request.execution_context.session_id,
            workflow_id=request.execution_context.workflow_id,
            step_index=request.execution_context.step_index,
            isolation_pool=request.execution_context.isolation_pool,
            environment=agent_meta.get("environment"),
            region=agent_meta.get("region"),
            metadata=dict(request.execution_context.metadata)
        )

        # Capabilities / Constraints
        req = request.requirements
        req_caps: List[str] = []
        if req.supports_tools:
            req_caps.append("tools")
        if req.supports_vision:
            req_caps.append("vision")
        if req.supports_structured_output:
            req_caps.append("structured_output")

        builder.set_constraints(
            requested_capabilities=req_caps,
            min_context_tokens=req.min_context_tokens,
            max_latency_ms=req.max_latency_ms,
            supports_tools=req.supports_tools,
            supports_vision=req.supports_vision,
            supports_structured_output=req.supports_structured_output,
            preferred_providers=list(req.preferred_providers),
            excluded_providers=list(req.excluded_providers),
            preferred_models=list(req.preferred_models),
            excluded_models=list(req.excluded_models)
        )

        # Policy reference
        policy_id = "pol_default"
        policy_ver = None
        has_inline = False
        if request.policy:
            policy_id = request.policy.policy_id or "pol_inline"
            policy_ver = request.policy.version
            has_inline = True

        builder.set_policy(
            policy_id=policy_id,
            policy_version=policy_ver,
            has_inline_policy=has_inline
        )

        # Operation summary
        tools = request.request.tools or []
        builder.set_operation(
            message_count=len(request.request.messages),
            has_tools=bool(tools),
            tool_count=len(tools),
            parameter_keys=list(request.request.parameters.keys()),
            has_raw_payload=request.request.raw_payload is not None
        )

        return builder

    def build(self) -> ExecutionContextRecord:
        """Validate, normalize, and construct an immutable ExecutionContextRecord."""
        raw_record = ExecutionContextRecord(
            execution_id=self._execution_id if self._execution_id is not None else f"exec_{uuid.uuid4().hex[:8]}",
            request_id=self._request_id if self._request_id is not None else f"req_{uuid.uuid4().hex[:8]}",
            parent_execution_id=self._parent_execution_id,
            created_at=self._created_at or datetime.now(timezone.utc).isoformat(),
            task=self._task if self._task is not None else TaskContextInfo(task_id=f"task_{uuid.uuid4().hex[:8]}"),
            agent=self._agent or AgentContextInfo(),
            runtime=self._runtime or RuntimeContextInfo(),
            constraints=self._constraints or ConstraintContextInfo(),
            policy=self._policy or PolicyContextInfo(),
            operation=self._operation or OperationContextInfo(),
            schema_version=SCHEMA_VERSION,
            extensions=dict(self._extensions)
        )

        # 1. Structural validation
        validate_execution_context(raw_record)

        # 2. Normalization
        norm_record = normalize_execution_context(raw_record)

        return norm_record


def create_execution_context(
    request: ExecutionRequest,
    execution_id: Optional[str] = None,
    parent_execution_id: Optional[str] = None
) -> ExecutionContextRecord:
    """Convenience factory function creating a canonical ExecutionContextRecord from an ExecutionRequest."""
    return ExecutionContextBuilder.from_execution_request(
        request=request,
        execution_id=execution_id,
        parent_execution_id=parent_execution_id
    ).build()
