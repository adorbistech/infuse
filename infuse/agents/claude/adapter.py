"""Claude Code Agent Adapter implementation of IUniversalAgentAdapter (Block 24)."""

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
from infuse.agents.claude.errors import (
    ClaudeAdapterError,
    ClaudeCLINotFoundError,
    ClaudeMalformedOutputError,
    ClaudeProcessError,
    ClaudeTimeoutError,
)
from infuse.agents.claude.models import (
    ClaudeAdapterConfig,
    ClaudeExecutionOutput,
    redact_secrets,
)
from infuse.agents.claude.transport import (
    ClaudeReferenceTransport,
    ClaudeSubprocessTransport,
    IClaudeTransport,
)
from infuse.agents.errors import (
    AgentAdapterError,
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


class ClaudeCodeAdapter(IUniversalAgentAdapter):
    """Universal agent adapter for Claude Code CLI and runtime.

    Translates between the INFUSE universal agent contracts and Claude Code-specific
    process and control mechanics.
    """

    def __init__(
        self,
        agent_id: str = "claude_code_adapter",
        agent_name: str = "claudecode",
        version: str = "1.0.0",
        config: Optional[ClaudeAdapterConfig] = None,
        transport: Optional[IClaudeTransport] = None,
        event_bus: Optional[IEventBus] = None,
    ) -> None:
        self._lock = threading.RLock()
        self._bus = event_bus
        self.config = config or ClaudeAdapterConfig()
        self.transport = transport or ClaudeSubprocessTransport(
            cli_path=self.config.cli_path,
            default_timeout=self.config.timeout_seconds,
        )
        self._identity = AgentIdentity(
            agent_id=agent_id,
            agent_name=agent_name,
            version=version,
            runtime_type="cli",
            metadata={"cli_available": self.transport.is_available()},
        )
        self._capability = AgentCapability(
            agent_name=agent_name,
            supported_protocols=["cli", "stdio", "json"],
            control_capabilities=ControlCapability(
                supports_cancel=True,
                supports_terminate=True,
                supports_throttle=False,
                supports_next_step_switch=False,
                supported_actions=[
                    GovernorAction.CONTINUE,
                    GovernorAction.STOP,
                ],
            ),
            supports_streaming_events=True,
            supports_tool_interception=False,
            supported_models=[
                "claude-3-7-sonnet",
                "claude-3-5-sonnet",
                "claude-3-opus",
                "claude-3-5-haiku",
            ],
            metadata={"vendor": "Anthropic Claude Code"},
        )
        self._sessions: Dict[str, AgentExecutionSession] = {}
        self.executed_steps: List[AgentStepRequest] = []
        self.received_controls: List[ControlOperation] = []

    @property
    def identity(self) -> AgentIdentity:
        with self._lock:
            return self._identity.model_copy(deep=True)

    def get_agent_capability(self) -> AgentCapability:
        with self._lock:
            return self._capability.model_copy(deep=True)

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
        metadata: Optional[Dict[str, Any]] = None,
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
                metadata=dict(metadata or {}),
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
            session = self._sessions.get(exec_id)
            if session is None:
                session = AgentExecutionSession(
                    execution_id=exec_id,
                    agent_id=self._identity.agent_id,
                    attached_at=now,
                    is_active=True,
                )
                self._sessions[exec_id] = session

            session.step_count += 1
            self.executed_steps.append(request.model_copy(deep=True))

        # Build non-interactive CLI args securely without shell interpolation
        prompt_text = request.prompt or ""
        args = [
            "-p", prompt_text,
            "--output-format", "json",
            "--permission-mode", self.config.permission_mode,
            "--no-session-persistence",
        ]
        if self.config.default_model:
            args.extend(["--model", self.config.default_model])

        try:
            output = self.transport.execute(
                args=args,
                execution_id=exec_id,
                cwd=self.config.working_directory,
                timeout=self.config.timeout_seconds,
            )
        except ClaudeAdapterError as e:
            raise AgentExecutionError(str(e)) from e
        except Exception as e:
            raise AgentExecutionError(f"Unexpected Claude Code execution failure: {e}") from e

        content = None
        raw_output = {}
        if output.parsed_json:
            raw_output = output.parsed_json
            content = output.parsed_json.get("result") or output.parsed_json.get("output") or output.stdout
        else:
            content = output.stdout or output.stderr

        resp = AgentStepResponse(
            execution_id=exec_id,
            step_index=request.step_index,
            content=content,
            tool_calls=request.tools[:1] if request.tools else None,
            finish_reason="stop",
            raw_output=raw_output if raw_output else {"stdout": output.stdout, "return_code": output.return_code},
            metadata={
                "agent_id": self._identity.agent_id,
                "duration_ms": output.duration_ms,
                "timestamp": now.isoformat(),
            },
        )

        # Publish event to event bus if attached
        if self._bus is not None:
            try:
                ev = ExecutionEvent(
                    event_id=f"step_ev_claude_{exec_id}_{request.step_index}_{int(now.timestamp()*1000)}",
                    execution_id=exec_id,
                    type=EventType.EXECUTION_COMPLETED,
                    source=EventSource.AGENT,
                    sequence=session.step_count,
                    timestamp=now,
                    payload={
                        "step_index": request.step_index,
                        "agent_id": self._identity.agent_id,
                        "agent_name": self._identity.agent_name,
                        "finish_reason": resp.finish_reason,
                    },
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

        is_supp = self.supports_action(gov_action)
        if not is_supp:
            return ControlResult(
                operation_id=operation.operation_id,
                execution_id=exec_id,
                action=gov_action,
                status=ControlStatus.UNSUPPORTED,
                message=f"Claude Code adapter does not support control action '{action_name}'.",
                executed_at=now,
                metadata={"agent_id": self._identity.agent_id, "is_supported": False},
            )

        try:
            if gov_action == GovernorAction.STOP:
                # Cancel or terminate active process
                params = operation.params or {}
                if params.get("hard") or params.get("terminate"):
                    self.transport.terminate_session(exec_id)
                else:
                    self.transport.cancel_execution(exec_id)

            return ControlResult(
                operation_id=operation.operation_id,
                execution_id=exec_id,
                action=gov_action,
                status=ControlStatus.COMPLETED,
                message=f"Claude Code adapter successfully applied action '{action_name}'.",
                executed_at=now,
                metadata={"agent_id": self._identity.agent_id, "is_supported": True},
            )
        except Exception as e:
            redacted_err = redact_secrets(str(e))
            return ControlResult(
                operation_id=operation.operation_id,
                execution_id=exec_id,
                action=gov_action,
                status=ControlStatus.FAILED,
                message=f"Claude Code adapter failed to execute control action '{action_name}': {redacted_err}",
                executed_at=now,
                metadata={"agent_id": self._identity.agent_id, "error": redacted_err},
            )

    def normalize_error(self, raw_error: Any, execution_id: Optional[str] = None) -> AgentErrorRecord:
        if isinstance(raw_error, Exception):
            code = raw_error.__class__.__name__
            msg = str(raw_error) or code
        elif isinstance(raw_error, dict):
            code = str(raw_error.get("error_code") or raw_error.get("code") or "CLAUDE_ERROR")
            msg = str(raw_error.get("message") or raw_error.get("error") or "Unknown Claude Code error")
        else:
            code = "CLAUDE_ERROR"
            msg = str(raw_error)

        return AgentErrorRecord(
            error_code=code,
            message=redact_secrets(msg),
            details={"execution_id": execution_id} if execution_id else {},
            timestamp=utc_now(),
        )

    def attach_to_bus(self, bus: IEventBus) -> None:
        with self._lock:
            self._bus = bus
