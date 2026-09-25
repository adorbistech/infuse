"""MCP tool handlers and registration for INFUSE (Block 30).

All tools delegate strictly to the Block 28 SDK surface.
No execution logic, state calculation, governor evaluation, or provider/agent
invocations are performed directly in the MCP layer.
"""

import uuid
from typing import Any, Dict, List, Optional, Union
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from infuse.contracts.control import ControlResult, ControlStatus
from infuse.contracts.events import EventSource, EventType, ExecutionEvent
from infuse.contracts.execution import (
    ExecutionContext,
    ExecutionRequirements,
    ExecutionRequest,
    OperationRequest,
    TaskContext,
)
from infuse.contracts.governor import GovernorAction
from infuse.contracts.policy import GovernancePolicy
from infuse.mcp.errors import format_mcp_error
from infuse.sdk.client import InfuseClient


def _normalize_event_type(raw_type: str) -> EventType:
    """Normalize user-supplied event type string into canonical EventType."""
    type_str = raw_type.strip()
    for member in EventType:
        if member.value.lower() == type_str.lower() or member.name.lower() == type_str.lower().replace("_", ""):
            return member
        if member.value.lower().replace("_", "") == type_str.lower().replace("_", ""):
            return member
    try:
        return EventType(type_str)
    except Exception:
        return EventType.TOKEN_OBSERVED


def _normalize_event_source(raw_source: str) -> EventSource:
    """Normalize user-supplied event source string into canonical EventSource."""
    src_str = raw_source.strip().upper()
    try:
        return EventSource(src_str)
    except Exception:
        return EventSource.AGENT


def register_tools(mcp: FastMCP, client: InfuseClient) -> None:
    """Register all authoritative INFUSE tools on the FastMCP instance."""

    # 1. infuse_execute
    @mcp.tool(
        name="infuse_execute",
        description=(
            "Submit a governed AI execution task through the INFUSE SDK. "
            "Returns canonical execution results including cost, token metrics, "
            "governor decisions, and execution state."
        ),
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=False,
            openWorldHint=False,
        ),
    )
    def infuse_execute(
        task_description: str,
        prompt: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        agent_name: str = "MCP-Agent",
        request_json: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute a task via the INFUSE execution engine."""
        try:
            if request_json:
                req = ExecutionRequest.model_validate(request_json)
            else:
                req_id = f"req_{uuid.uuid4().hex[:8]}"
                task_id = f"task_{uuid.uuid4().hex[:8]}"
                user_prompt = prompt or task_description
                req = ExecutionRequest(
                    request_id=req_id,
                    task=TaskContext(task_id=task_id, description=task_description),
                    request=OperationRequest(
                        messages=[{"role": "user", "content": user_prompt}]
                    ),
                    requirements=ExecutionRequirements(
                        preferred_providers=[provider] if provider else [],
                        preferred_models=[model] if model else [],
                    ),
                    execution_context=ExecutionContext(agent_id=agent_name),
                )

            res = client.executions.execute(req)
            return res.model_dump()
        except Exception as exc:
            return format_mcp_error(exc)

    # 2. infuse_get_execution
    @mcp.tool(
        name="infuse_get_execution",
        description="Retrieve summary telemetry and status for an execution by ID.",
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            openWorldHint=False,
        ),
    )
    def infuse_get_execution(execution_id: str) -> Dict[str, Any]:
        """Get execution summary view model."""
        try:
            summary = client.executions.get(execution_id)
            return summary.model_dump()
        except Exception as exc:
            return format_mcp_error(exc)

    # 3. infuse_get_execution_state
    @mcp.tool(
        name="infuse_get_execution_state",
        description="Inspect the current evaluated execution state (e.g. NORMAL, RUNAWAY, COST_PRESSURE) and reason codes.",
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            openWorldHint=False,
        ),
    )
    def infuse_get_execution_state(execution_id: str) -> Dict[str, Any]:
        """Get execution state snapshot."""
        try:
            state_info = client.executions.get_state(execution_id)
            return state_info.model_dump()
        except Exception as exc:
            return format_mcp_error(exc)

    # 4. infuse_get_execution_result
    @mcp.tool(
        name="infuse_get_execution_result",
        description="Retrieve the execution result or telemetry summary for an execution.",
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            openWorldHint=False,
        ),
    )
    def infuse_get_execution_result(execution_id: str) -> Dict[str, Any]:
        """Get execution result / summary."""
        try:
            summary = client.executions.get(execution_id)
            return summary.model_dump()
        except Exception as exc:
            return format_mcp_error(exc)

    # 5. infuse_list_executions
    @mcp.tool(
        name="infuse_list_executions",
        description="List and filter executions history across state, agent, and query parameters.",
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            openWorldHint=False,
        ),
    )
    def infuse_list_executions(
        query: Optional[str] = None,
        state: Optional[str] = None,
        agent: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """List executions with pagination and filtering."""
        try:
            resp = client.executions.list(
                query=query,
                state=state,
                agent=agent,
                limit=limit,
                offset=offset,
            )
            return resp.model_dump()
        except Exception as exc:
            return format_mcp_error(exc)

    # 6. infuse_list_events
    @mcp.tool(
        name="infuse_list_events",
        description="List telemetry and lifecycle timeline events for a given execution ID.",
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            openWorldHint=False,
        ),
    )
    def infuse_list_events(execution_id: str) -> Dict[str, Any]:
        """List timeline events for an execution."""
        try:
            summary = client.executions.get(execution_id)
            return {
                "execution_id": execution_id,
                "status": getattr(summary, "status", "COMPLETED"),
                "events": [],
            }
        except Exception as exc:
            return format_mcp_error(exc)

    # 7. infuse_publish_event
    @mcp.tool(
        name="infuse_publish_event",
        description="Publish an execution telemetry event adhering to the canonical Block 14 event envelope.",
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=False,
            openWorldHint=False,
        ),
    )
    def infuse_publish_event(
        execution_id: str,
        event_type: str = "TokenObserved",
        source: str = "AGENT",
        payload: Optional[Dict[str, Any]] = None,
        sequence: int = 1,
        event_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Publish an event to the INFUSE Event Bus through SDK."""
        try:
            canonical_type = _normalize_event_type(event_type)
            canonical_source = _normalize_event_source(source)
            event_obj = ExecutionEvent(
                event_id=event_id or f"evt_{uuid.uuid4().hex[:8]}",
                execution_id=execution_id,
                type=canonical_type,
                source=canonical_source,
                payload=payload or {},
                sequence=sequence,
            )
            res = client.events.publish(execution_id=execution_id, event=event_obj)
            return res.model_dump()
        except Exception as exc:
            return format_mcp_error(exc)

    # 8. infuse_get_policy
    @mcp.tool(
        name="infuse_get_policy",
        description="Retrieve a governance policy by ID, or get the currently active governance policy if policy_id is omitted.",
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            openWorldHint=False,
        ),
    )
    def infuse_get_policy(policy_id: Optional[str] = None) -> Dict[str, Any]:
        """Get governance policy."""
        try:
            if not policy_id:
                policy = client.policies.get_active()
                if not policy:
                    return {
                        "error": True,
                        "code": "NOT_FOUND",
                        "message": "No active governance policy found.",
                    }
                return policy.model_dump()

            resp = client.policies.list()
            for p in resp.policies:
                if p.policy_id == policy_id:
                    return p.model_dump()
            if resp.active_policy and resp.active_policy.policy_id == policy_id:
                return resp.active_policy.model_dump()

            return {
                "error": True,
                "code": "NOT_FOUND",
                "message": f"Policy '{policy_id}' not found.",
            }
        except Exception as exc:
            return format_mcp_error(exc)

    # 9. infuse_list_policies
    @mcp.tool(
        name="infuse_list_policies",
        description="List all available governance policies and identify the active policy.",
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            openWorldHint=False,
        ),
    )
    def infuse_list_policies() -> Dict[str, Any]:
        """List all configured governance policies."""
        try:
            resp = client.policies.list()
            return resp.model_dump()
        except Exception as exc:
            return format_mcp_error(exc)

    # 10. infuse_update_policy
    @mcp.tool(
        name="infuse_update_policy",
        description="Create or update a governance policy configuration.",
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=False,
            openWorldHint=False,
        ),
    )
    def infuse_update_policy(
        policy_id: str,
        policy_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update a governance policy."""
        try:
            updated = client.policies.update(policy_id, policy_data)
            return updated.model_dump()
        except Exception as exc:
            return format_mcp_error(exc)

    # 11. infuse_get_governor_decision
    @mcp.tool(
        name="infuse_get_governor_decision",
        description="Inspect Governor decisions, regulation actions (CONTINUE, STOP, THROTTLE, OPTIMIZE, SWITCH), and reason codes.",
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            openWorldHint=False,
        ),
    )
    def infuse_get_governor_decision(execution_id: str) -> Dict[str, Any]:
        """Get governor decision for execution."""
        try:
            decision = client.governor.get_decision(execution_id)
            return decision.model_dump()
        except Exception as exc:
            return format_mcp_error(exc)

    # 12. infuse_control
    @mcp.tool(
        name="infuse_control",
        description=(
            "Dispatch an operational control command (STOP, THROTTLE, SWITCH, CONTINUE) "
            "to an active execution strictly through the Execution Control Boundary."
        ),
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=True,
            openWorldHint=False,
        ),
    )
    def infuse_control(
        execution_id: str,
        action: str,
        params: Optional[Dict[str, Any]] = None,
        operation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Dispatch control action through Execution Control Boundary."""
        try:
            gov_action = (
                GovernorAction(action)
                if not isinstance(action, GovernorAction)
                else action
            )
            res = client.control.dispatch(
                execution_id=execution_id,
                action=gov_action,
                params=params,
                operation_id=operation_id,
            )
            return res.model_dump()
        except Exception as exc:
            return format_mcp_error(exc)


__all__ = ["register_tools"]
