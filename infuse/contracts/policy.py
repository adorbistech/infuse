"""Governance Policy contract definitions.

All thresholds, limits, and action bindings are defined as policy data.
INFUSE never hard-codes business limits, budgets, or pricing into core execution logic.
"""

from typing import Any, Dict, List, Optional
from pydantic import Field

from infuse.contracts.common import InfuseBaseModel
from infuse.contracts.governor import GovernorAction


class BudgetControls(InfuseBaseModel):
    """Budget limits and monetary constraints."""
    max_cost_per_task: Optional[float] = Field(
        default=None,
        description="Maximum cost in USD for a single execution task."
    )
    max_cost_per_day: Optional[float] = Field(
        default=None,
        description="Maximum daily aggregate spend limit in USD."
    )
    max_cost_per_month: Optional[float] = Field(
        default=None,
        description="Maximum monthly aggregate spend limit in USD."
    )
    currency: str = Field(
        default="USD",
        description="Currency code for monetary calculations."
    )


class TokenControls(InfuseBaseModel):
    """Token consumption boundaries."""
    max_input_tokens: Optional[int] = Field(
        default=None,
        description="Maximum prompt/context input tokens permitted."
    )
    max_output_tokens: Optional[int] = Field(
        default=None,
        description="Maximum completion output tokens permitted."
    )
    max_total_tokens: Optional[int] = Field(
        default=None,
        description="Maximum cumulative tokens (input + output) per task."
    )


class RequestControls(InfuseBaseModel):
    """Rate and volume limits for requests."""
    max_rpm: Optional[int] = Field(
        default=None,
        description="Maximum requests per minute allowed."
    )
    max_requests_per_task: Optional[int] = Field(
        default=None,
        description="Maximum number of provider invocations allowed for a single task."
    )


class RuntimeControls(InfuseBaseModel):
    """Execution time boundaries."""
    max_execution_time_seconds: Optional[int] = Field(
        default=None,
        description="Maximum allowable wall-clock execution duration in seconds."
    )


class ProviderAccessControls(InfuseBaseModel):
    """Provider and model allowlists and blocklists."""
    allowed_providers: Optional[List[str]] = Field(
        default=None,
        description="List of permitted provider identifiers. If None, all available are allowed."
    )
    allowed_models: Optional[List[str]] = Field(
        default=None,
        description="List of permitted model identifiers. If None, all available are allowed."
    )
    blocked_providers: Optional[List[str]] = Field(
        default=None,
        description="Explicitly forbidden providers."
    )
    blocked_models: Optional[List[str]] = Field(
        default=None,
        description="Explicitly forbidden models."
    )


class WebAccessControls(InfuseBaseModel):
    """Web browsing and network access permissions for agents."""
    enabled: bool = Field(
        default=True,
        description="Whether agent web access is permitted."
    )
    allowed_domains: Optional[List[str]] = Field(
        default=None,
        description="Allowlist of accessible domains. If None, access is unrestricted unless blocked."
    )
    blocked_domains: Optional[List[str]] = Field(
        default=None,
        description="Explicitly forbidden domains."
    )
    max_web_requests_per_task: Optional[int] = Field(
        default=None,
        description="Maximum number of external web requests allowed per task."
    )


class ToolAccessControls(InfuseBaseModel):
    """Tool invocation rules and safety bounds."""
    enabled: bool = Field(
        default=True,
        description="Whether agent tool usage is permitted."
    )
    allowed_tools: Optional[List[str]] = Field(
        default=None,
        description="Allowlist of callable tools. If None, all declared tools are allowed."
    )
    blocked_tools: Optional[List[str]] = Field(
        default=None,
        description="Explicitly forbidden tools."
    )
    max_tool_calls_per_task: Optional[int] = Field(
        default=None,
        description="Maximum number of tool invocations allowed per task."
    )
    max_consecutive_tool_failures: Optional[int] = Field(
        default=None,
        description="Maximum consecutive tool errors before triggering anomaly regulation."
    )


class RetryPolicy(InfuseBaseModel):
    """Policy governing automatic retries and fallback upon provider failures."""
    max_retries: int = Field(
        default=3,
        description="Maximum retry attempts on transient errors."
    )
    backoff_factor: float = Field(
        default=1.5,
        description="Exponential backoff multiplier between retries."
    )
    retry_on_errors: Optional[List[str]] = Field(
        default=None,
        description="Specific error categories that trigger retries (e.g. rate_limit, timeout)."
    )
    fallback_provider_on_failure: bool = Field(
        default=True,
        description="Whether to switch to a fallback provider when primary provider is exhausted."
    )


class AnomalyProtection(InfuseBaseModel):
    """Thresholds for runaway and anomalous agent behavior."""
    token_velocity_surge_threshold: Optional[float] = Field(
        default=None,
        description="Maximum token generation rate (tokens/sec) before flagging surge."
    )
    repetitive_loop_threshold: Optional[int] = Field(
        default=None,
        description="Max repeated identical tool calls or queries before declaring a loop."
    )
    circuit_breaker_enabled: bool = Field(
        default=True,
        description="Enable automatic circuit breaker halt when runaway state is declared."
    )


class PolicyActionBindings(InfuseBaseModel):
    """Explicit mapping from limit breaches to Governor actions."""
    budget_action: GovernorAction = Field(
        default=GovernorAction.OPTIMIZE,
        description="Action to take when budget threshold is reached."
    )
    token_action: GovernorAction = Field(
        default=GovernorAction.OPTIMIZE,
        description="Action to take when token ceiling is reached."
    )
    request_action: GovernorAction = Field(
        default=GovernorAction.THROTTLE,
        description="Action to take when RPM or request ceiling is reached."
    )
    runtime_action: GovernorAction = Field(
        default=GovernorAction.STOP,
        description="Action to take when execution time limit is exceeded."
    )
    provider_failure_action: GovernorAction = Field(
        default=GovernorAction.SWITCH,
        description="Action to take when provider fails or degrades."
    )
    anomaly_action: GovernorAction = Field(
        default=GovernorAction.STOP,
        description="Action to take when runaway/anomaly behavior is detected."
    )


class GovernancePolicy(InfuseBaseModel):
    """Canonical user-defined governance envelope for AI execution."""
    policy_id: str = Field(
        ...,
        description="Unique policy identifier."
    )
    name: str = Field(
        default="Default Execution Policy",
        description="Human-readable policy name."
    )
    version: str = Field(
        default="1.0.0",
        description="Policy revision version."
    )
    is_active: bool = Field(
        default=True,
        description="Whether this policy is currently active."
    )
    budget: BudgetControls = Field(
        default_factory=BudgetControls,
        description="Budget and spend boundaries."
    )
    tokens: TokenControls = Field(
        default_factory=TokenControls,
        description="Token usage boundaries."
    )
    requests: RequestControls = Field(
        default_factory=RequestControls,
        description="Request volume and rate boundaries."
    )
    runtime: RuntimeControls = Field(
        default_factory=RuntimeControls,
        description="Wall-clock time limits."
    )
    providers: ProviderAccessControls = Field(
        default_factory=ProviderAccessControls,
        description="Provider and model access constraints."
    )
    web: WebAccessControls = Field(
        default_factory=WebAccessControls,
        description="Web access permissions."
    )
    tools: ToolAccessControls = Field(
        default_factory=ToolAccessControls,
        description="Tool usage permissions."
    )
    retries: RetryPolicy = Field(
        default_factory=RetryPolicy,
        description="Retry and fallback rules."
    )
    anomaly: AnomalyProtection = Field(
        default_factory=AnomalyProtection,
        description="Runaway detection and protection parameters."
    )
    actions: PolicyActionBindings = Field(
        default_factory=PolicyActionBindings,
        description="Governor action bindings for each trigger."
    )
