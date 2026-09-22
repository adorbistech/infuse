"""Execution Context deterministic normalization logic."""

from datetime import datetime, timezone
from typing import List, Optional

from infuse.context.models import (
    AgentContextInfo,
    ConstraintContextInfo,
    ExecutionContextRecord,
    OperationContextInfo,
    PolicyContextInfo,
    RuntimeContextInfo,
    TaskContextInfo,
)
from infuse.version import SCHEMA_VERSION


def _clean_str(val: Optional[str]) -> Optional[str]:
    """Trim string or return None if None or empty."""
    if val is None:
        return None
    trimmed = val.strip()
    return trimmed if trimmed else None


def _clean_str_list(items: Optional[List[str]]) -> List[str]:
    """Trim strings, remove empty items, and deduplicate while preserving insertion order."""
    if not items:
        return []
    cleaned: List[str] = []
    seen = set()
    for item in items:
        if isinstance(item, str):
            s = item.strip()
            if s and s not in seen:
                seen.add(s)
                cleaned.append(s)
    return cleaned


def normalize_execution_context(ctx: ExecutionContextRecord) -> ExecutionContextRecord:
    """Deterministically normalize an ExecutionContextRecord snapshot."""
    # 1. Identity & Timestamp
    exec_id = (ctx.execution_id or "").strip()
    req_id = (ctx.request_id or "").strip()
    parent_id = _clean_str(ctx.parent_execution_id)
    
    created_at = (ctx.created_at or "").strip()
    if not created_at:
        created_at = datetime.now(timezone.utc).isoformat()

    # 2. Task normalization
    task_info = TaskContextInfo(
        task_id=(ctx.task.task_id or "").strip(),
        description=_clean_str(ctx.task.description),
        workload_hint=_clean_str(ctx.task.workload_hint),
        tags=_clean_str_list(ctx.task.tags),
        metadata=dict(ctx.task.metadata)
    )

    # 3. Agent normalization
    agent_info = AgentContextInfo(
        agent_id=_clean_str(ctx.agent.agent_id),
        agent_name=_clean_str(ctx.agent.agent_name),
        agent_type=_clean_str(ctx.agent.agent_type),
        client_version=_clean_str(ctx.agent.client_version),
        runtime_version=_clean_str(ctx.agent.runtime_version),
        execution_mode=_clean_str(ctx.agent.execution_mode),
        metadata=dict(ctx.agent.metadata)
    )

    # 4. Runtime normalization
    runtime_info = RuntimeContextInfo(
        session_id=_clean_str(ctx.runtime.session_id),
        workflow_id=_clean_str(ctx.runtime.workflow_id),
        step_index=max(0, ctx.runtime.step_index),
        isolation_pool=_clean_str(ctx.runtime.isolation_pool),
        environment=_clean_str(ctx.runtime.environment),
        region=_clean_str(ctx.runtime.region),
        metadata=dict(ctx.runtime.metadata)
    )

    # 5. Constraints normalization
    constraint_info = ConstraintContextInfo(
        requested_capabilities=_clean_str_list(ctx.constraints.requested_capabilities),
        min_context_tokens=ctx.constraints.min_context_tokens,
        max_latency_ms=ctx.constraints.max_latency_ms,
        supports_tools=bool(ctx.constraints.supports_tools),
        supports_vision=bool(ctx.constraints.supports_vision),
        supports_structured_output=bool(ctx.constraints.supports_structured_output),
        preferred_providers=_clean_str_list(ctx.constraints.preferred_providers),
        excluded_providers=_clean_str_list(ctx.constraints.excluded_providers),
        preferred_models=_clean_str_list(ctx.constraints.preferred_models),
        excluded_models=_clean_str_list(ctx.constraints.excluded_models),
        metadata=dict(ctx.constraints.metadata)
    )

    # 6. Policy reference normalization
    policy_info = PolicyContextInfo(
        policy_id=_clean_str(ctx.policy.policy_id) or "pol_default",
        policy_version=_clean_str(ctx.policy.policy_version),
        has_inline_policy=bool(ctx.policy.has_inline_policy),
        metadata=dict(ctx.policy.metadata)
    )

    # 7. Operation context normalization
    op_info = OperationContextInfo(
        message_count=max(0, ctx.operation.message_count),
        has_tools=bool(ctx.operation.has_tools),
        tool_count=max(0, ctx.operation.tool_count),
        parameter_keys=_clean_str_list(ctx.operation.parameter_keys),
        has_raw_payload=bool(ctx.operation.has_raw_payload),
        metadata=dict(ctx.operation.metadata)
    )

    return ExecutionContextRecord(
        execution_id=exec_id,
        request_id=req_id,
        parent_execution_id=parent_id,
        created_at=created_at,
        task=task_info,
        agent=agent_info,
        runtime=runtime_info,
        constraints=constraint_info,
        policy=policy_info,
        operation=op_info,
        schema_version=SCHEMA_VERSION,
        extensions=dict(ctx.extensions)
    )
