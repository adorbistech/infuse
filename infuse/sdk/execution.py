"""Execution Client for the INFUSE SDK (Block 28).

Provides typed operations for submitting executions, retrieving telemetry,
inspecting states, and listing execution histories.
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import ValidationError

from infuse.contracts.execution import (
    ExecutionRequest,
    ExecutionResult,
)
from infuse.contracts.frontend import (
    ExecutionSummaryViewModel,
)
from infuse.contracts.state import ExecutionState
from infuse.sdk.errors import (
    NotFoundError,
    ValidationError as SdkValidationError,
)
from infuse.sdk.models import (
    ExecutionListResponse,
    StateInfo,
)
from infuse.sdk.transport import ITransport


def _extract_summary_view_model(data: Any) -> ExecutionSummaryViewModel:
    """Normalize execution dictionary (ExecutionResult or ViewModel) to ExecutionSummaryViewModel."""
    if isinstance(data, dict):
        if "execution" in data and "execution_id" in data:
            telemetry = data.get("execution", {}) or {}
            metadata = telemetry.get("metadata", {}) or {}
            return ExecutionSummaryViewModel(
                execution_id=data["execution_id"],
                agent_name=metadata.get("agent_name") or "AnonymousAgent",
                task_description=metadata.get("task_description") or "Execution Task",
                status=str(data.get("status", "COMPLETED")),
                provider=telemetry.get("provider") or "DefaultProvider",
                model=telemetry.get("model") or "DefaultModel",
                is_live=(data.get("status") == "RUNNING"),
            )
        return ExecutionSummaryViewModel.model_validate(data)
    elif isinstance(data, ExecutionSummaryViewModel):
        return data
    raise ValueError(f"Cannot extract ExecutionSummaryViewModel from {type(data)}")


class ExecutionClient:
    """Developer-facing interface for execution lifecycle and telemetry."""

    def __init__(self, transport: ITransport) -> None:
        self._transport = transport

    def execute(self, request: Union[ExecutionRequest, Dict[str, Any]]) -> ExecutionResult:
        """Submit a normalized execution request to INFUSE.

        Maps to: POST /v1/execute
        """
        if isinstance(request, dict):
            try:
                validated_req = ExecutionRequest.model_validate(request)
            except ValidationError as exc:
                raise SdkValidationError(
                    message="Invalid execution request schema.",
                    details={"errors": exc.errors()},
                ) from exc
        elif isinstance(request, ExecutionRequest):
            validated_req = request
        else:
            raise ValueError("request must be an ExecutionRequest instance or a valid dictionary.")

        payload = validated_req.model_dump(mode="json")
        resp = self._transport.send_request(
            method="POST",
            path="/v1/execute",
            json_data=payload,
        )

        try:
            return ExecutionResult.model_validate(resp.data)
        except ValidationError as exc:
            raise SdkValidationError(
                message="Server returned an invalid ExecutionResult structure.",
                details={"errors": exc.errors()},
            ) from exc

    def get(self, execution_id: str) -> ExecutionSummaryViewModel:
        """Retrieve detailed execution telemetry by ID.

        Maps to: GET /v1/executions/{id}
        """
        if not execution_id or not execution_id.strip():
            raise ValueError("execution_id must not be empty.")

        exec_id = execution_id.strip()
        resp = self._transport.send_request(
            method="GET",
            path=f"/v1/executions/{exec_id}",
        )

        try:
            return _extract_summary_view_model(resp.data)
        except Exception as exc:
            raise SdkValidationError(
                message="Server returned an invalid ExecutionSummaryViewModel structure.",
            ) from exc

    def list(
        self,
        query: Optional[str] = None,
        state: Optional[str] = None,
        agent: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ExecutionListResponse:
        """List and filter execution summaries.

        Maps to: GET /v1/executions
        """
        if limit < 1 or limit > 200:
            raise ValueError("limit must be between 1 and 200.")
        if offset < 0:
            raise ValueError("offset must be non-negative.")

        params = {
            "query": query,
            "state": state,
            "agent": agent,
            "limit": limit,
            "offset": offset,
        }

        resp = self._transport.send_request(
            method="GET",
            path="/v1/executions",
            params=params,
        )

        raw = resp.data or {}
        items: List[ExecutionSummaryViewModel] = []
        raw_items: List[Any] = []
        if isinstance(raw, dict):
            raw_items = raw.get("executions") or raw.get("items") or []
        elif isinstance(raw, list):
            raw_items = raw

        for it in raw_items:
            try:
                items.append(_extract_summary_view_model(it))
            except Exception:
                pass

        total = raw.get("total", len(items)) if isinstance(raw, dict) else len(items)

        return ExecutionListResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

    def get_state(self, execution_id: str) -> StateInfo:
        """Inspect the current evaluated execution state and rationale."""
        summary = self.get(execution_id)
        st_val = getattr(summary, "status", "NORMAL")
        try:
            state_enum = ExecutionState(st_val.upper())
        except Exception:
            state_enum = ExecutionState.NORMAL

        return StateInfo(
            execution_id=summary.execution_id,
            state=state_enum,
            reason_codes=[],
            boundary_threshold_percent=80.0,
            evaluated_at=summary.started_at.isoformat() if summary.started_at else None,
        )


__all__ = ["ExecutionClient"]
