"""UI Card and Presentation Generators for ChatGPT Apps."""

from typing import Any, Dict, Optional
from infuse.version import SCHEMA_VERSION, __version__


def format_execution_card(execution_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a clean visual card payload for ChatGPT to render an execution."""
    exec_id = execution_data.get("execution_id", "Unknown")
    status = execution_data.get("status", "UNKNOWN")
    state = execution_data.get("state") or execution_data.get("execution", {}).get("state", "NORMAL")
    cost = execution_data.get("cost_usd") or execution_data.get("execution", {}).get("cost_usd", 0.0)
    tokens = execution_data.get("total_tokens") or execution_data.get("execution", {}).get("total_tokens", 0)
    provider = execution_data.get("provider") or execution_data.get("execution", {}).get("provider", "N/A")
    model = execution_data.get("model") or execution_data.get("execution", {}).get("model", "N/A")
    action = execution_data.get("decision", {}).get("action", "CONTINUE")

    state_badge = {
        "NORMAL": "🟢 NORMAL",
        "COST_PRESSURE": "🟡 COST_PRESSURE",
        "RUNAWAY": "🔴 RUNAWAY",
        "QUALITY_DEGRADED": "🟠 QUALITY_DEGRADED",
        "PROVIDER_CONSTRAINED": "🟣 PROVIDER_CONSTRAINED",
    }.get(state, f"⚪ {state}")

    action_badge = {
        "CONTINUE": "▶️ CONTINUE",
        "OPTIMIZE": "⚡ OPTIMIZE",
        "ESCALATE": "🔼 ESCALATE",
        "DOWNGRADE": "🔽 DOWNGRADE",
        "SWITCH": "🔄 SWITCH",
        "THROTTLE": "⏳ THROTTLE",
        "STOP": "🛑 STOP",
    }.get(action, action)

    return {
        "type": "infuse_execution_card",
        "version": "1.0",
        "header": {
            "title": f"INFUSE Execution — {exec_id}",
            "subtitle": f"Status: {status} | Governor: {action_badge}",
        },
        "state": {
            "canonical_state": state,
            "badge": state_badge,
        },
        "metrics": {
            "provider": provider,
            "model": model,
            "total_tokens": tokens,
            "cost_usd": f"${cost:.6f}",
        },
        "governor": {
            "action": action,
            "reason": execution_data.get("decision", {}).get("reason", "Within policy limits"),
        },
    }


def format_system_info_card(system_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate presentation card for system health and version overview."""
    return {
        "type": "infuse_system_card",
        "version": "1.0",
        "title": "INFUSE Execution Intelligence",
        "release": f"v{__version__}",
        "schema_version": SCHEMA_VERSION,
        "status": system_data.get("status", "HEALTHY"),
        "active_policy": system_data.get("active_policy", "pol_default"),
        "registered_providers": system_data.get("registered_providers", ["Anthropic", "OpenAI", "Gemini", "DeepSeek", "LiteLLM"]),
        "registered_agents": system_data.get("registered_agents", ["Claude Code", "OpenCode", "Codex", "Hermes", "OpenClaw", "Lovable"]),
    }
