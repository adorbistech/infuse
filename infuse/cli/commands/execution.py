"""Execution commands for INFUSE CLI (Block 29)."""

import json
import os
import sys
import uuid
from typing import Any, Dict, Optional

from infuse.cli.exit_codes import EXIT_SUCCESS, EXIT_USAGE_ERROR
from infuse.cli.formatter import (
    format_error,
    format_execution_list,
    format_execution_result,
    format_execution_summary,
    format_state_info,
)
from infuse.contracts.execution import (
    ExecutionContext,
    ExecutionRequirements,
    ExecutionRequest,
    OperationRequest,
    TaskContext,
)
from infuse.sdk.client import InfuseClient


def handle_execute(
    client: InfuseClient,
    task: Optional[str] = None,
    prompt: Optional[str] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    agent: Optional[str] = None,
    input_file: Optional[str] = None,
    json_mode: bool = False,
) -> int:
    """Execute a task via the Block 28 SDK."""
    if input_file:
        if not os.path.exists(input_file):
            print(
                format_error(f"Input file not found: {input_file}", "FILE_NOT_FOUND", json_mode=json_mode),
                file=sys.stderr,
            )
            return EXIT_USAGE_ERROR
        try:
            with open(input_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            request = ExecutionRequest.model_validate(data)
        except Exception as exc:
            print(
                format_error(f"Failed to load execution request from file: {exc}", "INVALID_INPUT", json_mode=json_mode),
                file=sys.stderr,
            )
            return EXIT_USAGE_ERROR
    else:
        req_id = f"req_{uuid.uuid4().hex[:8]}"
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        task_desc = task or "CLI execution request"
        req_content = prompt or task_desc

        preferred_providers = [provider] if provider else []
        preferred_models = [model] if model else []

        request = ExecutionRequest(
            request_id=req_id,
            task=TaskContext(
                task_id=task_id,
                description=task_desc,
            ),
            request=OperationRequest(
                messages=[{"role": "user", "content": req_content}],
            ),
            requirements=ExecutionRequirements(
                preferred_providers=preferred_providers,
                preferred_models=preferred_models,
            ),
            execution_context=ExecutionContext(
                agent_id=agent or "CLI-Agent",
            ),
        )

    result = client.executions.execute(request)
    print(format_execution_result(result, json_mode=json_mode))
    return EXIT_SUCCESS


def handle_executions_get(
    client: InfuseClient,
    execution_id: str,
    json_mode: bool = False,
) -> int:
    """Get execution telemetry by ID."""
    summary = client.executions.get(execution_id)
    print(format_execution_summary(summary, json_mode=json_mode))
    return EXIT_SUCCESS


def handle_executions_state(
    client: InfuseClient,
    execution_id: str,
    json_mode: bool = False,
) -> int:
    """Get execution state by ID."""
    state_info = client.executions.get_state(execution_id)
    print(format_state_info(state_info, json_mode=json_mode))
    return EXIT_SUCCESS


def handle_executions_result(
    client: InfuseClient,
    execution_id: str,
    json_mode: bool = False,
) -> int:
    """Get execution result / summary by ID."""
    summary = client.executions.get(execution_id)
    print(format_execution_summary(summary, json_mode=json_mode))
    return EXIT_SUCCESS


def handle_executions_list(
    client: InfuseClient,
    query: Optional[str] = None,
    state: Optional[str] = None,
    agent: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    json_mode: bool = False,
) -> int:
    """List execution history."""
    resp = client.executions.list(
        query=query,
        state=state,
        agent=agent,
        limit=limit,
        offset=offset,
    )
    print(format_execution_list(resp, json_mode=json_mode))
    return EXIT_SUCCESS


__all__ = [
    "handle_execute",
    "handle_executions_get",
    "handle_executions_state",
    "handle_executions_result",
    "handle_executions_list",
]
