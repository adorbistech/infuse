"""Reference Universal Agent Adapter for testing and architectural validation."""

import threading
from typing import Any, Dict, List, Optional

from infuse.contracts.capabilities import AgentCapability
from infuse.contracts.common import utc_now
from infuse.contracts.control import (
    ControlCapability,
    ControlOperation,
    ControlResult,
    ControlStatus,
)
from infuse.contracts.events import EventSource, EventType, ExecutionEvent
from infuse.contracts.governor import GovernorAction
from infuse.events.interfaces import IEventBus
from infuse.agents.errors import (
    AgentControlError,
    AgentExecutionError,
    AgentUnavailableError,
    UnsupportedAgentOperationError,
)
from infuse.agents.interfaces import IUniversalAgentAdapter
from infuse.agents.models import (
    AgentErrorRecord,
    AgentExecutionSession,
    AgentIdentity,
    AgentStepRequest,
    AgentStepResponse,
)


class ReferenceUniversalAgentAdapter(IUniversalAgentAdapter):
    """Deterministic reference implementation of IUniversalAgentAdapter.

    Used for testing the Universal Agent abstraction, Control Boundary integration,
    and event publication without coupling to any real agent CLI or SDK.
    """

    def __init__(
        self,
        agent_id: str = "ref_agent_01",
        agent_name: str = "reference",
        version: str = "1.0.0",
        capability: Optional[AgentCapability] = None,
        event_bus: Optional[IEventBus] = None,
    ) -> None:
        self._lock = threading.RLock()
        self._bus = event_bus
        self._identity = AgentIdentity(
            agent_id=agent_id,
            agent_name=agent_name,
            version=version,
            runtime_type="reference",
        )
        self._capability = capability or AgentCapability(
            agent_name=agent_name,
            supported_protocols=["http", "stdio"],
            control_capabilities=ControlCapability(
                supports_cancel=True,
                supports_throttle=True,
                supports_next_step_switch=True,
                supports_terminate=True,
                supported_actions=[
                    GovernorAction.CONTINUE,
                    GovernorAction.STOP,
                    GovernorAction.THROTTLE,
                    GovernorAction.SWITCH,
                    GovernorAction.OPTIMIZE,
                ],
            ),
            supports_streaming_events=True,
            supports_tool_interception=True,
            supported_models=["mock-model-v1", "mock-model-v2"],
        )
        self._sessions: Dict[str, AgentExecutionSession] = {}
        self._step_responses: Dict[int, AgentStepResponse] = {}
        self.should_fail_step = False
        self.should_fail_control = False
        self.should_raise_step = False
        self.should_raise_control = False
        self.executed_steps: List[AgentStepRequest] = []
        self.received_controls: List[ControlOperation] = []

    @property
    def identity(self) -> AgentIdentity:
        return self._identity.model_copy(deep=True)

    def get_agent_capability(self) -> AgentCapability:
        with self._lock:
            return self._capability.model_copy(deep=True)

    def set_agent_capability(self, capability: AgentCapability) -> None:
        with self._lock:
            self._capability = capability.model_copy(deep=True)

    def supports_cancel(self) -> bool:
        with self._lock:
            return bool(self._capability.control_capabilities.supports_cancel)

    def supports_throttle(self) -> bool:
        with self._lock:
            return bool(self._capability.control_capabilities.supports_throttle)

    def supports_next_step_switch(self) -> bool:
        with self._lock:
            return bool(self._capability.control_capabilities.supports_next_step_switch)

    def supports_terminate(self) -> bool:
        with self._lock:
            return bool(self._capability.control_capabilities.supports_terminate)

    def supports_action(self, action: GovernorAction) -> bool:
        if action is None:
            return False
        gov_action = GovernorAction(action) if not isinstance(action, GovernorAction) else action
        if gov_action == GovernorAction.CONTINUE:
            return True

        with self._lock:
            ctrl = self._capability.control_capabilities
            if gov_action in ctrl.supported_actions:
                return True
            if gov_action == GovernorAction.STOP:
                return bool(ctrl.supports_cancel or ctrl.supports_terminate)
            if gov_action == GovernorAction.THROTTLE:
                return bool(ctrl.supports_throttle)
            if gov_action == GovernorAction.SWITCH:
                return bool(ctrl.supports_next_step_switch)
            return False

    def attach_execution(
        self,
        execution_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AgentExecutionSession:
        if not execution_id or not execution_id.strip():
            raise ValueError("execution_id must not be empty.")

        exec_id = execution_id.strip()
        with self._lock:
            session = AgentExecutionSession(
                execution_id=exec_id,
                agent_id=self._identity.agent_id,
                attached_at=utc_now(),
                is_active=True,
                metadata=dict(metadata or {})
            )
            self._sessions[exec_id] = session
            return session.model_copy(deep=True)

    def detach_execution(self, execution_id: str) -> None:
        if not execution_id:
            return
        exec_id = execution_id.strip()
        with self._lock:
            if exec_id in self._sessions:
                self._sessions[exec_id].is_active = False

    def get_session(self, execution_id: str) -> Optional[AgentExecutionSession]:
        if not execution_id:
            return None
        with self._lock:
            session = self._sessions.get(execution_id.strip())
            return session.model_copy(deep=True) if session else None

    def execute_step(self, request: AgentStepRequest) -> AgentStepResponse:
        if request is None:
            raise ValueError("request must not be None.")
        if not request.execution_id or not request.execution_id.strip():
            raise ValueError("request.execution_id must not be empty.")

        exec_id = request.execution_id.strip()
        now = utc_now()

        with self._lock:
            if self.should_raise_step:
                raise AgentExecutionError("Reference agent step simulation crash")

            if self.should_fail_step:
                raise AgentExecutionError("Reference agent execution failure")

            session = self._sessions.get(exec_id)
            if session is None:
                # Auto-attach if not explicitly attached
                session = AgentExecutionSession(
                    execution_id=exec_id,
                    agent_id=self._identity.agent_id,
                    attached_at=now,
                    is_active=True
                )
                self._sessions[exec_id] = session

            session.step_count += 1
            self.executed_steps.append(request.model_copy(deep=True))

            # Return preset or deterministic step response
            if request.step_index in self._step_responses:
                resp = self._step_responses[request.step_index].model_copy(deep=True)
            else:
                resp = AgentStepResponse(
                    execution_id=exec_id,
                    step_index=request.step_index,
                    content=f"Reference step {request.step_index} completed.",
                    tool_calls=request.tools[:1] if request.tools else None,
                    finish_reason="stop",
                    metadata={"agent_id": self._identity.agent_id, "timestamp": now.isoformat()}
                )

            # Publish event if bus is attached
            if self._bus is not None:
                try:
                    ev = ExecutionEvent(
                        event_id=f"step_ev_{exec_id}_{request.step_index}_{int(now.timestamp()*1000)}",
                        execution_id=exec_id,
                        type=EventType.EXECUTION_COMPLETED,
                        source=EventSource.AGENT,
                        sequence=session.step_count,
                        timestamp=now,
                        payload={
                            "step_index": request.step_index,
                            "agent_id": self._identity.agent_id,
                            "finish_reason": resp.finish_reason
                        }
                    )
                    self._bus.publish(ev)
                except Exception:
                    pass

            return resp

    def execute_control(self, operation: ControlOperation) -> ControlResult:
        if operation is None:
            raise ValueError("operation must not be None.")

        exec_id = operation.execution_id.strip()
        now = utc_now()
        gov_action = operation.action
        action_name = gov_action.value if hasattr(gov_action, "value") else str(gov_action)

        with self._lock:
            self.received_controls.append(operation.model_copy(deep=True))

            session = self._sessions.get(exec_id)
            if session is not None:
                session.control_history.append(operation.model_copy(deep=True))

            if self.should_raise_control:
                raise AgentControlError("Reference agent hardware fault during control execution")

            if self.should_fail_control:
                return ControlResult(
                    operation_id=operation.operation_id,
                    execution_id=exec_id,
                    action=gov_action,
                    status=ControlStatus.FAILED,
                    message="Reference agent failed to apply control action.",
                    executed_at=now,
                    metadata={"agent_id": self._identity.agent_id}
                )

            is_supp = self.supports_action(gov_action)
            if not is_supp:
                return ControlResult(
                    operation_id=operation.operation_id,
                    execution_id=exec_id,
                    action=gov_action,
                    status=ControlStatus.UNSUPPORTED,
                    message=f"Agent '{self._identity.agent_id}' does not support action '{action_name}'.",
                    executed_at=now,
                    metadata={"agent_id": self._identity.agent_id, "is_supported": False}
                )

            return ControlResult(
                operation_id=operation.operation_id,
                execution_id=exec_id,
                action=gov_action,
                status=ControlStatus.COMPLETED,
                message=f"Reference agent successfully applied action '{action_name}'.",
                executed_at=now,
                metadata={"agent_id": self._identity.agent_id, "is_supported": True}
            )

    def normalize_error(self, raw_error: Any, execution_id: Optional[str] = None) -> AgentErrorRecord:
        if isinstance(raw_error, Exception):
            code = raw_error.__class__.__name__
            msg = str(raw_error) or code
        elif isinstance(raw_error, dict):
            code = str(raw_error.get("error_code") or raw_error.get("code") or "AGENT_ERROR")
            msg = str(raw_error.get("message") or raw_error.get("error") or "Unknown agent error")
        else:
            code = "AGENT_ERROR"
            msg = str(raw_error)

        return AgentErrorRecord(
            error_code=code,
            message=msg,
            details={"execution_id": execution_id} if execution_id else {},
            timestamp=utc_now()
        )

    def attach_to_bus(self, bus: IEventBus) -> None:
        with self._lock:
            self._bus = bus

    def clear(self) -> None:
        with self._lock:
            self._sessions.clear()
            self._step_responses.clear()
            self.executed_steps.clear()
            self.received_controls.clear()
            self.should_fail_step = False
            self.should_fail_control = False
            self.should_raise_step = False
            self.should_raise_control = False
