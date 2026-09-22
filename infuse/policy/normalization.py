"""Governance Policy normalization logic."""

from typing import List, Optional
from infuse.contracts.policy import (
    GovernancePolicy,
    BudgetControls,
    TokenControls,
    RequestControls,
    RuntimeControls,
    ProviderAccessControls,
    WebAccessControls,
    ToolAccessControls,
    RetryPolicy,
    AnomalyProtection,
    PolicyActionBindings,
)
from infuse.version import SCHEMA_VERSION


def _clean_str_list(items: Optional[List[str]]) -> Optional[List[str]]:
    """Trim strings, remove empty items, and deduplicate while preserving order."""
    if items is None:
        return None
    cleaned = []
    seen = set()
    for item in items:
        if isinstance(item, str):
            s = item.strip()
            if s and s not in seen:
                seen.add(s)
                cleaned.append(s)
    return cleaned


def normalize_policy(policy: GovernancePolicy) -> GovernancePolicy:
    """Normalize a governance policy representation deterministically."""
    # 1. Budget normalization
    budget = policy.budget or BudgetControls()
    norm_budget = BudgetControls(
        max_cost_per_task=budget.max_cost_per_task,
        max_cost_per_day=budget.max_cost_per_day,
        max_cost_per_month=budget.max_cost_per_month,
        currency=(budget.currency or "USD").strip().upper(),
        schema_version=SCHEMA_VERSION,
        extensions=dict(budget.extensions)
    )

    # 2. Token normalization
    tokens = policy.tokens or TokenControls()
    norm_tokens = TokenControls(
        max_input_tokens=tokens.max_input_tokens,
        max_output_tokens=tokens.max_output_tokens,
        max_total_tokens=tokens.max_total_tokens,
        schema_version=SCHEMA_VERSION,
        extensions=dict(tokens.extensions)
    )

    # 3. Request normalization
    requests = policy.requests or RequestControls()
    norm_requests = RequestControls(
        max_rpm=requests.max_rpm,
        max_requests_per_task=requests.max_requests_per_task,
        schema_version=SCHEMA_VERSION,
        extensions=dict(requests.extensions)
    )

    # 4. Runtime normalization
    runtime = policy.runtime or RuntimeControls()
    norm_runtime = RuntimeControls(
        max_execution_time_seconds=runtime.max_execution_time_seconds,
        schema_version=SCHEMA_VERSION,
        extensions=dict(runtime.extensions)
    )

    # 5. Provider normalization
    prov = policy.providers or ProviderAccessControls()
    norm_providers = ProviderAccessControls(
        allowed_providers=_clean_str_list(prov.allowed_providers),
        allowed_models=_clean_str_list(prov.allowed_models),
        blocked_providers=_clean_str_list(prov.blocked_providers),
        blocked_models=_clean_str_list(prov.blocked_models),
        schema_version=SCHEMA_VERSION,
        extensions=dict(prov.extensions)
    )

    # 6. Web normalization
    web = policy.web or WebAccessControls()
    norm_web = WebAccessControls(
        enabled=web.enabled,
        allowed_domains=_clean_str_list(web.allowed_domains),
        blocked_domains=_clean_str_list(web.blocked_domains),
        max_web_requests_per_task=web.max_web_requests_per_task,
        schema_version=SCHEMA_VERSION,
        extensions=dict(web.extensions)
    )

    # 7. Tool normalization
    tools = policy.tools or ToolAccessControls()
    norm_tools = ToolAccessControls(
        enabled=tools.enabled,
        allowed_tools=_clean_str_list(tools.allowed_tools),
        blocked_tools=_clean_str_list(tools.blocked_tools),
        max_tool_calls_per_task=tools.max_tool_calls_per_task,
        max_consecutive_tool_failures=tools.max_consecutive_tool_failures,
        schema_version=SCHEMA_VERSION,
        extensions=dict(tools.extensions)
    )

    # 8. Retry normalization
    retries = policy.retries or RetryPolicy()
    norm_retries = RetryPolicy(
        max_retries=retries.max_retries,
        backoff_factor=retries.backoff_factor,
        retry_on_errors=_clean_str_list(retries.retry_on_errors),
        fallback_provider_on_failure=retries.fallback_provider_on_failure,
        schema_version=SCHEMA_VERSION,
        extensions=dict(retries.extensions)
    )

    # 9. Anomaly normalization
    anomaly = policy.anomaly or AnomalyProtection()
    norm_anomaly = AnomalyProtection(
        token_velocity_surge_threshold=anomaly.token_velocity_surge_threshold,
        repetitive_loop_threshold=anomaly.repetitive_loop_threshold,
        circuit_breaker_enabled=anomaly.circuit_breaker_enabled,
        schema_version=SCHEMA_VERSION,
        extensions=dict(anomaly.extensions)
    )

    # 10. Actions normalization
    actions = policy.actions or PolicyActionBindings()
    norm_actions = PolicyActionBindings(
        budget_action=actions.budget_action,
        token_action=actions.token_action,
        request_action=actions.request_action,
        runtime_action=actions.runtime_action,
        provider_failure_action=actions.provider_failure_action,
        anomaly_action=actions.anomaly_action,
        schema_version=SCHEMA_VERSION,
        extensions=dict(actions.extensions)
    )

    return GovernancePolicy(
        policy_id=(policy.policy_id or "").strip(),
        name=(policy.name or "Governance Policy").strip(),
        version=(policy.version or "1.0.0").strip(),
        is_active=bool(policy.is_active),
        budget=norm_budget,
        tokens=norm_tokens,
        requests=norm_requests,
        runtime=norm_runtime,
        providers=norm_providers,
        web=norm_web,
        tools=norm_tools,
        retries=norm_retries,
        anomaly=norm_anomaly,
        actions=norm_actions,
        schema_version=SCHEMA_VERSION,
        extensions=dict(policy.extensions)
    )
