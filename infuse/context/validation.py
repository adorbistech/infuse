"""Execution Context structural and invariant validation.

Validates the contextual integrity of an execution envelope without performing
workload classification, routing decisions, or runtime governance enforcement.
"""

from typing import List

from infuse.context.errors import ExecutionContextValidationError
from infuse.context.models import ExecutionContextRecord


def validate_execution_context(ctx: ExecutionContextRecord) -> None:
    """Validate an ExecutionContextRecord against structural and invariant constraints.

    Raises ExecutionContextValidationError if one or more violations are detected.
    """
    violations: List[str] = []

    # 1. Identity validation
    if not ctx.execution_id or not ctx.execution_id.strip():
        violations.append("execution_id cannot be empty or whitespace.")
    if not ctx.request_id or not ctx.request_id.strip():
        violations.append("request_id cannot be empty or whitespace.")

    # 2. Task context validation
    if not ctx.task or not ctx.task.task_id or not ctx.task.task_id.strip():
        violations.append("task.task_id cannot be empty or whitespace.")

    # 3. Runtime context validation
    if ctx.runtime.step_index < 0:
        violations.append(f"runtime.step_index must be >= 0, got {ctx.runtime.step_index}.")

    # 4. Constraints validation
    c = ctx.constraints
    if c.min_context_tokens is not None and c.min_context_tokens < 0:
        violations.append(f"constraints.min_context_tokens must be >= 0, got {c.min_context_tokens}.")
    if c.max_latency_ms is not None and c.max_latency_ms <= 0.0:
        violations.append(f"constraints.max_latency_ms must be > 0.0, got {c.max_latency_ms}.")

    # Check for overlapping preferred and excluded providers
    if c.preferred_providers and c.excluded_providers:
        overlap_prov = set(c.preferred_providers).intersection(set(c.excluded_providers))
        if overlap_prov:
            violations.append(
                f"Providers cannot be both preferred and excluded: {sorted(overlap_prov)}."
            )

    # Check for overlapping preferred and excluded models
    if c.preferred_models and c.excluded_models:
        overlap_mod = set(c.preferred_models).intersection(set(c.excluded_models))
        if overlap_mod:
            violations.append(
                f"Models cannot be both preferred and excluded: {sorted(overlap_mod)}."
            )

    # 5. Operation context validation
    if ctx.operation.message_count < 0:
        violations.append(f"operation.message_count must be >= 0, got {ctx.operation.message_count}.")
    if ctx.operation.tool_count < 0:
        violations.append(f"operation.tool_count must be >= 0, got {ctx.operation.tool_count}.")

    # 6. Schema version check
    if not ctx.schema_version or not (ctx.schema_version == "1.0.0" or ctx.schema_version.startswith("1.")):
        violations.append(f"Invalid schema_version: '{ctx.schema_version}'. Expected '1.0.0'.")

    if violations:
        raise ExecutionContextValidationError(
            f"ExecutionContext '{ctx.execution_id}' failed validation with {len(violations)} violation(s).",
            violations=violations
        )
