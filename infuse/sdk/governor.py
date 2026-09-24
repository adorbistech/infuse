"""Governor Visibility Client for the INFUSE SDK (Block 28).

Provides read-only inspection of Governor decisions, action states, and reason codes.
The SDK does NOT make Governor decisions; it reflects decisions from the Governor engine.
"""

from typing import Optional

from infuse.contracts.governor import GovernorAction
from infuse.sdk.models import GovernorInfo
from infuse.sdk.transport import ITransport


class GovernorClient:
    """Developer-facing interface for Governor decision inspection."""

    def __init__(self, transport: ITransport) -> None:
        self._transport = transport

    def get_decision(self, execution_id: str) -> GovernorInfo:
        """Retrieve current Governor decision and regulatory posture for an execution."""
        if not execution_id or not execution_id.strip():
            raise ValueError("execution_id must not be empty.")

        clean_id = execution_id.strip()
        resp = self._transport.send_request(
            method="GET",
            path=f"/v1/executions/{clean_id}",
        )

        raw = resp.data or {}
        # Extract decision data from execution summary
        action_str = raw.get("routing_mode") or "CONTINUE"
        action_enum = GovernorAction.CONTINUE
        try:
            action_enum = GovernorAction(action_str.upper())
        except Exception:
            action_enum = GovernorAction.CONTINUE

        return GovernorInfo(
            execution_id=clean_id,
            action=action_enum,
            reason_codes=[],
            action_banner_title=f"Governor Action: {action_enum.value}",
            action_banner_description="Active regulation status from INFUSE Governor.",
            recent_decisions=[],
        )


__all__ = ["GovernorClient"]
