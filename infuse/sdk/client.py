"""Main Developer Entrypoint for the INFUSE SDK (Block 28).

InfuseClient coordinates access across execution, policy, event,
governor visibility, and control interfaces.
"""

from typing import Any, Dict, List, Optional, Union

from infuse.contracts.control import ControlCapability, ControlResult
from infuse.contracts.events import ExecutionEvent
from infuse.contracts.execution import (
    ExecutionRequest,
    ExecutionResult,
)
from infuse.contracts.frontend import ExecutionSummaryViewModel
from infuse.contracts.governor import GovernorAction
from infuse.contracts.policy import GovernancePolicy
from infuse.control.interfaces import IExecutionControlBoundary
from infuse.sdk.config import ClientConfig
from infuse.sdk.control import ControlClient
from infuse.sdk.events import EventClient
from infuse.sdk.execution import ExecutionClient
from infuse.sdk.governor import GovernorClient
from infuse.sdk.models import (
    EventIngestResponse,
    ExecutionListResponse,
    GovernorInfo,
    PolicyListResponse,
    StateInfo,
)
from infuse.sdk.policy import PolicyClient
from infuse.sdk.transport import HttpTransport, ITransport


class InfuseClient:
    """Universal developer client for INFUSE Execution Intelligence & Governance."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        config: Optional[ClientConfig] = None,
        transport: Optional[ITransport] = None,
        control_boundary: Optional[IExecutionControlBoundary] = None,
    ) -> None:
        if config is not None:
            self.config = config
        else:
            self.config = ClientConfig(
                base_url=base_url or "http://localhost:8000",
                api_key=api_key,
            )

        self.transport = transport or HttpTransport(config=self.config)

        # Specialized sub-clients
        self.executions = ExecutionClient(transport=self.transport)
        self.policies = PolicyClient(transport=self.transport)
        self.events = EventClient(transport=self.transport)
        self.governor = GovernorClient(transport=self.transport)
        self.control = ControlClient(transport=self.transport, boundary=control_boundary)

    # ── Convenience Shortcuts ──────────────────────────────────────────

    def execute(self, request: Union[ExecutionRequest, Dict[str, Any]]) -> ExecutionResult:
        """Submit an execution request to INFUSE."""
        return self.executions.execute(request)

    def get_execution(self, execution_id: str) -> ExecutionSummaryViewModel:
        """Retrieve execution telemetry and status."""
        return self.executions.get(execution_id)

    def list_executions(
        self,
        query: Optional[str] = None,
        state: Optional[str] = None,
        agent: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ExecutionListResponse:
        """List and search execution history."""
        return self.executions.list(
            query=query,
            state=state,
            agent=agent,
            limit=limit,
            offset=offset,
        )

    def get_state(self, execution_id: str) -> StateInfo:
        """Inspect execution state and rationale."""
        return self.executions.get_state(execution_id)

    def get_active_policy(self) -> Optional[GovernancePolicy]:
        """Retrieve the currently active governance policy."""
        return self.policies.get_active()

    def update_policy(
        self,
        policy_id: str,
        policy: Union[GovernancePolicy, Dict[str, Any]],
    ) -> GovernancePolicy:
        """Update a governance policy revision."""
        return self.policies.update(policy_id, policy)

    def publish_event(
        self,
        execution_id: str,
        event: Union[ExecutionEvent, Dict[str, Any]],
    ) -> EventIngestResponse:
        """Publish a telemetry event for an execution."""
        return self.events.publish(execution_id, event)

    def get_governor_decision(self, execution_id: str) -> GovernorInfo:
        """Retrieve Governor decision and regulation info."""
        return self.governor.get_decision(execution_id)

    def cancel(self, execution_id: str) -> ControlResult:
        """Cancel an active execution."""
        return self.control.cancel(execution_id)

    def terminate(self, execution_id: str) -> ControlResult:
        """Hard terminate an active execution."""
        return self.control.terminate(execution_id)

    def get_control_capability(self, execution_id: str) -> Optional[ControlCapability]:
        """Inspect declared control capabilities."""
        return self.control.get_capability(execution_id)


__all__ = ["InfuseClient"]
