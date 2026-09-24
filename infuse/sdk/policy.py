"""Policy Client for the INFUSE SDK (Block 28).

Provides typed operations for retrieving, listing, and updating governance policies.
The SDK does NOT evaluate policies locally; it delegates to the INFUSE Policy service.
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import ValidationError

from infuse.contracts.policy import GovernancePolicy
from infuse.sdk.errors import (
    NotFoundError,
    ValidationError as SdkValidationError,
)
from infuse.sdk.models import PolicyListResponse
from infuse.sdk.transport import ITransport


class PolicyClient:
    """Developer-facing interface for Governance Policy access."""

    def __init__(self, transport: ITransport) -> None:
        self._transport = transport

    def list(self) -> PolicyListResponse:
        """Retrieve all active policies and policy revisions.

        Maps to: GET /v1/policies
        """
        resp = self._transport.send_request(
            method="GET",
            path="/v1/policies",
        )

        raw = resp.data or {}
        policies: List[GovernancePolicy] = []
        active_policy: Optional[GovernancePolicy] = None

        if isinstance(raw, dict):
            for p in raw.get("policies", []):
                try:
                    policies.append(GovernancePolicy.model_validate(p))
                except Exception:
                    pass
            if raw.get("active_policy"):
                try:
                    active_policy = GovernancePolicy.model_validate(raw["active_policy"])
                except Exception:
                    pass

        return PolicyListResponse(
            policies=policies,
            active_policy=active_policy,
        )

    def get_active(self) -> Optional[GovernancePolicy]:
        """Retrieve the currently active governance policy."""
        res = self.list()
        return res.active_policy

    def update(
        self,
        policy_id: str,
        policy: Union[GovernancePolicy, Dict[str, Any]],
    ) -> GovernancePolicy:
        """Create or update a governance policy revision.

        Maps to: PUT /v1/policies/{id}
        """
        if not policy_id or not policy_id.strip():
            raise ValueError("policy_id must not be empty.")

        clean_id = policy_id.strip()

        if isinstance(policy, dict):
            # Ensure policy_id matches path
            policy_dict = dict(policy)
            policy_dict["policy_id"] = clean_id
            try:
                validated_policy = GovernancePolicy.model_validate(policy_dict)
            except ValidationError as exc:
                raise SdkValidationError(
                    message="Invalid governance policy schema.",
                    details={"errors": exc.errors()},
                ) from exc
        elif isinstance(policy, GovernancePolicy):
            validated_policy = policy
        else:
            raise ValueError("policy must be a GovernancePolicy instance or a valid dictionary.")

        payload = validated_policy.model_dump(mode="json")
        resp = self._transport.send_request(
            method="PUT",
            path=f"/v1/policies/{clean_id}",
            json_data=payload,
        )

        try:
            return GovernancePolicy.model_validate(resp.data)
        except ValidationError as exc:
            raise SdkValidationError(
                message="Server returned an invalid GovernancePolicy structure.",
                details={"errors": exc.errors()},
            ) from exc


__all__ = ["PolicyClient"]
