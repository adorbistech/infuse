"""INFUSE CLI Output Formatters (Block 29).

Provides deterministic human-readable and machine-readable JSON formatting
for all SDK models, execution summaries, governance policies, and error responses.
"""

import json
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel

from infuse.contracts.control import ControlResult, ControlStatus
from infuse.contracts.execution import ExecutionResult
from infuse.contracts.frontend import ExecutionSummaryViewModel
from infuse.contracts.policy import GovernancePolicy
from infuse.sdk.config import ClientConfig
from infuse.sdk.errors import redact_sdk_secrets
from infuse.sdk.models import (
    EventIngestResponse,
    ExecutionListResponse,
    GovernorInfo,
    PolicyListResponse,
    StateInfo,
)


def _to_serializable(data: Any) -> Any:
    """Convert SDK models or nested structures into JSON-serializable dictionaries."""
    if isinstance(data, BaseModel):
        return data.model_dump(mode="json")
    if isinstance(data, dict):
        return {k: _to_serializable(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_to_serializable(item) for item in data]
    return data


def format_json(data: Any) -> str:
    """Serialize any data payload to deterministic, indented JSON string with secrets redacted."""
    serializable = _to_serializable(data)
    json_str = json.dumps(serializable, indent=2, default=str)
    return redact_sdk_secrets(json_str)


def format_error(
    message: str,
    error_code: str = "ERROR",
    details: Optional[Dict[str, Any]] = None,
    json_mode: bool = False,
) -> str:
    """Format an error payload for terminal output or JSON output."""
    clean_msg = redact_sdk_secrets(message)
    if json_mode:
        err_obj: Dict[str, Any] = {
            "error": clean_msg,
            "code": error_code,
        }
        if details:
            err_obj["details"] = _to_serializable(details)
        return format_json(err_obj)

    out = f"Error [{error_code}]: {clean_msg}"
    if details:
        out += f"\nDetails: {details}"
    return out


def format_execution_result(result: ExecutionResult, json_mode: bool = False) -> str:
    """Format an ExecutionResult model."""
    if json_mode:
        return format_json(result)

    telemetry = result.execution
    provider = getattr(telemetry, "provider", None) or (telemetry.get("provider") if isinstance(telemetry, dict) else "N/A") or "N/A"
    model = getattr(telemetry, "model", None) or (telemetry.get("model") if isinstance(telemetry, dict) else "N/A") or "N/A"
    input_tokens = getattr(telemetry, "input_tokens", None) if not isinstance(telemetry, dict) else telemetry.get("input_tokens", 0)
    output_tokens = getattr(telemetry, "output_tokens", None) if not isinstance(telemetry, dict) else telemetry.get("output_tokens", 0)
    cost_usd = getattr(telemetry, "cost_usd", None) if not isinstance(telemetry, dict) else telemetry.get("cost_usd", 0.0)

    status_str = result.status.value if hasattr(result.status, "value") else str(result.status)
    lines = [
        f"Execution ID:    {result.execution_id}",
        f"Status:          {status_str}",
        f"Provider:        {provider}",
        f"Model:           {model}",
        f"Prompt Tokens:   {input_tokens or 0}",
        f"Comp. Tokens:    {output_tokens or 0}",
        f"Total Cost:      ${(cost_usd or 0.0):.6f}",
    ]
    if result.response and getattr(result.response, "content", None):
        lines.append(f"\nResponse Content:\n{result.response.content}")
    return "\n".join(lines)


def format_execution_summary(summary: ExecutionSummaryViewModel, json_mode: bool = False) -> str:
    """Format an ExecutionSummaryViewModel."""
    if json_mode:
        return format_json(summary)

    lines = [
        f"Execution ID:     {summary.execution_id}",
        f"Status:           {summary.status}",
        f"Agent Name:       {summary.agent_name}",
        f"Task Description: {summary.task_description}",
        f"Provider:         {summary.provider}",
        f"Model:            {summary.model}",
        f"Tokens Total:     {summary.tokens_total:,}",
        f"Cost USD:         ${summary.cost_usd:.6f}",
        f"Latency:          {summary.latency_ms} ms",
        f"Live:             {'Yes' if summary.is_live else 'No'}",
    ]
    if summary.started_at:
        lines.append(f"Started At:       {summary.started_at}")
    return "\n".join(lines)


def format_execution_list(resp: ExecutionListResponse, json_mode: bool = False) -> str:
    """Format a list of execution summaries."""
    if json_mode:
        return format_json(resp)

    if not resp.items:
        return f"No executions found (Total: {resp.total})."

    header = f"{'EXECUTION ID':<32} {'STATUS':<12} {'AGENT':<18} {'PROVIDER/MODEL':<24} {'COST ($)':<10} {'LATENCY'}"
    divider = "-" * len(header)
    rows = [header, divider]

    for item in resp.items:
        prov_model = f"{item.provider}/{item.model}"[:24]
        rows.append(
            f"{item.execution_id:<32} {item.status:<12} {item.agent_name[:17]:<18} {prov_model:<24} ${item.cost_usd:<9.4f} {item.latency_ms}ms"
        )
    rows.append(divider)
    rows.append(f"Total: {resp.total} (Showing {len(resp.items)}, Offset {resp.offset}, Limit {resp.limit})")
    return "\n".join(rows)


def format_state_info(state_info: StateInfo, json_mode: bool = False) -> str:
    """Format StateInfo inspection response."""
    if json_mode:
        return format_json(state_info)

    state_val = state_info.state.value if hasattr(state_info.state, "value") else str(state_info.state)
    lines = [
        f"Execution ID:        {state_info.execution_id}",
        f"Evaluated State:     {state_val}",
        f"Boundary Threshold:  {state_info.boundary_threshold_percent:.1f}%",
        f"Evaluated At:        {state_info.evaluated_at or 'N/A'}",
        f"Reason Codes:        {', '.join(state_info.reason_codes) if state_info.reason_codes else 'None'}",
    ]
    return "\n".join(lines)


def format_governor_info(gov_info: GovernorInfo, json_mode: bool = False) -> str:
    """Format GovernorInfo inspection response."""
    if json_mode:
        return format_json(gov_info)

    action_val = gov_info.action.value if hasattr(gov_info.action, "value") else str(gov_info.action)
    lines = [
        f"Execution ID:        {gov_info.execution_id}",
        f"Governor Action:     {action_val}",
        f"Banner Title:        {gov_info.action_banner_title}",
        f"Banner Description:  {gov_info.action_banner_description}",
        f"Reason Codes:        {', '.join(gov_info.reason_codes) if gov_info.reason_codes else 'None'}",
    ]
    return "\n".join(lines)


def format_control_result(ctrl_result: ControlResult, json_mode: bool = False) -> str:
    """Format a ControlResult response."""
    if json_mode:
        return format_json(ctrl_result)

    status_val = ctrl_result.status.value if hasattr(ctrl_result.status, "value") else str(ctrl_result.status)
    action_val = ctrl_result.action.value if hasattr(ctrl_result.action, "value") else str(ctrl_result.action)
    lines = [
        f"Operation ID:  {ctrl_result.operation_id}",
        f"Execution ID:  {ctrl_result.execution_id}",
        f"Action:        {action_val}",
        f"Status:        {status_val}",
        f"Message:       {ctrl_result.message or 'N/A'}",
        f"Executed At:   {getattr(ctrl_result, 'executed_at', None) or 'N/A'}",
    ]
    if getattr(ctrl_result, "details", None):
        lines.append(f"Details:       {json.dumps(ctrl_result.details)}")
    elif getattr(ctrl_result, "metadata", None):
        lines.append(f"Metadata:      {json.dumps(ctrl_result.metadata)}")
    return "\n".join(lines)


def format_policy(policy: Optional[GovernancePolicy], json_mode: bool = False) -> str:
    """Format a GovernancePolicy."""
    if json_mode:
        return format_json(policy)

    if not policy:
        return "No policy found."

    lines = [
        f"Policy ID:       {policy.policy_id}",
        f"Name:            {policy.name}",
        f"Version:         {policy.version}",
        f"Active:          {'Yes' if policy.is_active else 'No'}",
    ]
    desc = getattr(policy, "description", None)
    if desc:
        lines.append(f"Description:     {desc}")
    updated = getattr(policy, "updated_at", None)
    if updated:
        lines.append(f"Updated At:      {updated}")
    budget = getattr(policy, "budget", None) or getattr(policy, "budget_controls", None)
    if budget:
        max_cost = getattr(budget, "max_cost_per_task", None) or getattr(budget, "max_budget_usd", None)
        if max_cost is not None:
            lines.append(f"Budget Limit:    ${max_cost:.2f}")
    tokens = getattr(policy, "tokens", None) or getattr(policy, "token_controls", None)
    if tokens:
        max_tok = getattr(tokens, "max_total_tokens", None) or getattr(tokens, "max_tokens_per_execution", None)
        if max_tok is not None:
            lines.append(f"Max Tokens:      {max_tok:,}")
    return "\n".join(lines)


def format_policy_list(resp: PolicyListResponse, json_mode: bool = False) -> str:
    """Format PolicyListResponse."""
    if json_mode:
        return format_json(resp)

    if not resp.policies:
        return "No governance policies configured."

    header = f"{'POLICY ID':<24} {'NAME':<28} {'VERSION':<10} {'ACTIVE'}"
    divider = "-" * len(header)
    rows = [header, divider]

    for p in resp.policies:
        active_str = "YES" if p.is_active else "NO"
        rows.append(f"{p.policy_id:<24} {p.name[:27]:<28} {p.version:<10} {active_str}")

    rows.append(divider)
    if resp.active_policy:
        rows.append(f"Active Policy ID: {resp.active_policy.policy_id} ({resp.active_policy.name})")
    return "\n".join(rows)


def format_event_response(resp: EventIngestResponse, json_mode: bool = False) -> str:
    """Format EventIngestResponse."""
    if json_mode:
        return format_json(resp)

    lines = [
        f"Event ID:        {resp.event_id}",
        f"Execution ID:    {resp.execution_id}",
        f"Status:          {resp.status}",
        f"Schema Version:  {resp.schema_version}",
    ]
    return "\n".join(lines)


def format_config(config: ClientConfig, json_mode: bool = False) -> str:
    """Format ClientConfig with secrets strictly redacted."""
    cfg_dict = config.model_dump(mode="json")
    if cfg_dict.get("api_key"):
        cfg_dict["api_key"] = "[REDACTED]"

    if json_mode:
        return format_json(cfg_dict)

    lines = [
        "INFUSE SDK / CLI Configuration:",
        f"  Base URL:        {cfg_dict.get('base_url')}",
        f"  API Key:         {'[CONFIGURED]' if config.api_key else '[NONE]'}",
        f"  Timeout (s):     {cfg_dict.get('timeout_seconds')}",
        f"  Correlation ID:  {cfg_dict.get('correlation_id_prefix')}",
    ]
    return "\n".join(lines)


__all__ = [
    "format_json",
    "format_error",
    "format_execution_result",
    "format_execution_summary",
    "format_execution_list",
    "format_state_info",
    "format_governor_info",
    "format_control_result",
    "format_policy",
    "format_policy_list",
    "format_event_response",
    "format_config",
]
