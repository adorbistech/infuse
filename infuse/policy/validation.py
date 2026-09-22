"""Governance policy structural, range, and logical validator.

Policy validation occurs during policy creation and updates.
It ensures semantic contract integrity without performing runtime Governor enforcement.
"""

from typing import List, Optional

from infuse.contracts.governor import GovernorAction
from infuse.contracts.policy import GovernancePolicy
from infuse.policy.errors import PolicyValidationError


def validate_policy(policy: GovernancePolicy) -> None:
    """Validate a governance policy against structural, range, and logical rules.
    
    Raises PolicyValidationError if one or more violations are detected.
    """
    violations: List[str] = []

    # 1. Identity & Versioning
    if not policy.policy_id or not policy.policy_id.strip():
        violations.append("policy_id cannot be empty or whitespace.")
    if not policy.version or not policy.version.strip():
        violations.append("version cannot be empty or whitespace.")

    # 2. Budget Controls
    b = policy.budget
    if b.max_cost_per_task is not None and b.max_cost_per_task < 0.0:
        violations.append(f"budget.max_cost_per_task must be >= 0.0, got {b.max_cost_per_task}.")
    if b.max_cost_per_day is not None and b.max_cost_per_day < 0.0:
        violations.append(f"budget.max_cost_per_day must be >= 0.0, got {b.max_cost_per_day}.")
    if b.max_cost_per_month is not None and b.max_cost_per_month < 0.0:
        violations.append(f"budget.max_cost_per_month must be >= 0.0, got {b.max_cost_per_month}.")

    if (
        b.max_cost_per_task is not None
        and b.max_cost_per_day is not None
        and b.max_cost_per_day < b.max_cost_per_task
    ):
        violations.append(
            f"budget.max_cost_per_day ({b.max_cost_per_day}) cannot be less than max_cost_per_task ({b.max_cost_per_task})."
        )
    if (
        b.max_cost_per_day is not None
        and b.max_cost_per_month is not None
        and b.max_cost_per_month < b.max_cost_per_day
    ):
        violations.append(
            f"budget.max_cost_per_month ({b.max_cost_per_month}) cannot be less than max_cost_per_day ({b.max_cost_per_day})."
        )

    # 3. Token Controls
    t = policy.tokens
    if t.max_input_tokens is not None and t.max_input_tokens < 0:
        violations.append(f"tokens.max_input_tokens must be >= 0, got {t.max_input_tokens}.")
    if t.max_output_tokens is not None and t.max_output_tokens < 0:
        violations.append(f"tokens.max_output_tokens must be >= 0, got {t.max_output_tokens}.")
    if t.max_total_tokens is not None and t.max_total_tokens < 0:
        violations.append(f"tokens.max_total_tokens must be >= 0, got {t.max_total_tokens}.")

    if (
        t.max_input_tokens is not None
        and t.max_total_tokens is not None
        and t.max_total_tokens < t.max_input_tokens
    ):
        violations.append(
            f"tokens.max_total_tokens ({t.max_total_tokens}) cannot be less than max_input_tokens ({t.max_input_tokens})."
        )
    if (
        t.max_output_tokens is not None
        and t.max_total_tokens is not None
        and t.max_total_tokens < t.max_output_tokens
    ):
        violations.append(
            f"tokens.max_total_tokens ({t.max_total_tokens}) cannot be less than max_output_tokens ({t.max_output_tokens})."
        )

    # 4. Request Controls
    req = policy.requests
    if req.max_rpm is not None and req.max_rpm <= 0:
        violations.append(f"requests.max_rpm must be > 0, got {req.max_rpm}.")
    if req.max_requests_per_task is not None and req.max_requests_per_task <= 0:
        violations.append(
            f"requests.max_requests_per_task must be > 0, got {req.max_requests_per_task}."
        )

    # 5. Runtime Controls
    rt = policy.runtime
    if rt.max_execution_time_seconds is not None and rt.max_execution_time_seconds <= 0:
        violations.append(
            f"runtime.max_execution_time_seconds must be > 0, got {rt.max_execution_time_seconds}."
        )

    # 6. Provider & Model Access
    prov = policy.providers
    if prov.allowed_providers is not None and prov.blocked_providers is not None:
        overlap_providers = set(prov.allowed_providers).intersection(set(prov.blocked_providers))
        if overlap_providers:
            violations.append(
                f"Providers cannot be both allowed and blocked: {sorted(overlap_providers)}."
            )
    if prov.allowed_models is not None and prov.blocked_models is not None:
        overlap_models = set(prov.allowed_models).intersection(set(prov.blocked_models))
        if overlap_models:
            violations.append(
                f"Models cannot be both allowed and blocked: {sorted(overlap_models)}."
            )

    # 7. Web Access Controls
    w = policy.web
    if w.max_web_requests_per_task is not None and w.max_web_requests_per_task < 0:
        violations.append(
            f"web.max_web_requests_per_task must be >= 0, got {w.max_web_requests_per_task}."
        )
    if w.allowed_domains is not None and w.blocked_domains is not None:
        overlap_domains = set(w.allowed_domains).intersection(set(w.blocked_domains))
        if overlap_domains:
            violations.append(
                f"Domains cannot be both allowed and blocked: {sorted(overlap_domains)}."
            )

    # 8. Tool Access Controls
    tl = policy.tools
    if tl.max_tool_calls_per_task is not None and tl.max_tool_calls_per_task < 0:
        violations.append(
            f"tools.max_tool_calls_per_task must be >= 0, got {tl.max_tool_calls_per_task}."
        )
    if (
        tl.max_consecutive_tool_failures is not None
        and tl.max_consecutive_tool_failures < 0
    ):
        violations.append(
            f"tools.max_consecutive_tool_failures must be >= 0, got {tl.max_consecutive_tool_failures}."
        )
    if tl.allowed_tools is not None and tl.blocked_tools is not None:
        overlap_tools = set(tl.allowed_tools).intersection(set(tl.blocked_tools))
        if overlap_tools:
            violations.append(
                f"Tools cannot be both allowed and blocked: {sorted(overlap_tools)}."
            )

    # 9. Retry Policy
    r = policy.retries
    if r.max_retries < 0:
        violations.append(f"retries.max_retries must be >= 0, got {r.max_retries}.")
    if r.backoff_factor < 1.0:
        violations.append(f"retries.backoff_factor must be >= 1.0, got {r.backoff_factor}.")

    # 10. Anomaly Protection
    a = policy.anomaly
    if (
        a.token_velocity_surge_threshold is not None
        and a.token_velocity_surge_threshold <= 0.0
    ):
        violations.append(
            f"anomaly.token_velocity_surge_threshold must be > 0.0, got {a.token_velocity_surge_threshold}."
        )
    if a.repetitive_loop_threshold is not None and a.repetitive_loop_threshold < 1:
        violations.append(
            f"anomaly.repetitive_loop_threshold must be >= 1, got {a.repetitive_loop_threshold}."
        )

    # 11. Action Bindings
    act = policy.actions
    valid_actions = set(GovernorAction)
    action_fields = [
        ("budget_action", act.budget_action),
        ("token_action", act.token_action),
        ("request_action", act.request_action),
        ("runtime_action", act.runtime_action),
        ("provider_failure_action", act.provider_failure_action),
        ("anomaly_action", act.anomaly_action),
    ]
    for name, action_val in action_fields:
        if action_val not in valid_actions and action_val not in [v.value for v in valid_actions]:
            violations.append(f"actions.{name} has invalid Governor action: {action_val}.")

    if violations:
        raise PolicyValidationError(
            f"Governance policy '{policy.policy_id}' failed validation with {len(violations)} violation(s).",
            violations=violations
        )
