"""Execution Control Boundary implementation for Block 22."""

import threading
from typing import Any, Dict, List, Optional

from infuse.contracts.common import utc_now
from infuse.contracts.control import (
    ControlCapability,
    ControlOperation,
    ControlResult,
    ControlStatus,
)
from infuse.contracts.events import EventSource, EventType, ExecutionEvent
from infuse.contracts.governor import GovernorAction
from infuse.control.interfaces import IControlExecutor, IExecutionControlBoundary
from infuse.control.models import ControlAuditRecord
from infuse.events.interfaces import IEventBus


class ExecutionControlBoundary(IExecutionControlBoundary):
    """Execution Control Boundary bridging Governor decisions and physical execution runtimes.

    Verifies declared capabilities before dispatching control commands.
    Ensures unsupported capabilities fail safely without hidden fallback governance,
    provider routing, retry loops, or lifecycle replacement.
    """

    def __init__(self, event_bus: Optional[IEventBus] = None) -> None:
        self._lock = threading.RLock()
        self._bus = event_bus
        self._capabilities: Dict[str, ControlCapability] = {}
        self._executors: Dict[str, IControlExecutor] = {}
        self._latest_results: Dict[str, ControlResult] = {}
        self._history: Dict[str, List[ControlAuditRecord]] = {}
        self._operations: Dict[str, ControlResult] = {}
        self._seq_counters: Dict[str, int] = {}

    def register_capability(self, execution_id: str, capability: ControlCapability) -> None:
        """Register declared capabilities for a given execution run."""
        if not execution_id:
            raise ValueError("execution_id must not be empty.")
        if capability is None:
            raise ValueError("capability must not be None.")
        with self._lock:
            self._capabilities[execution_id.strip()] = capability.model_copy(deep=True)

    def register_executor(self, execution_id: str, executor: IControlExecutor) -> None:
        """Register a physical control executor for a given execution run."""
        if not execution_id:
            raise ValueError("execution_id must not be empty.")
        if executor is None:
            raise ValueError("executor must not be None.")
        with self._lock:
            exec_id = execution_id.strip()
            self._executors[exec_id] = executor
            # Sync capability from executor
            cap = executor.get_capability()
            if cap is not None:
                self._capabilities[exec_id] = cap.model_copy(deep=True)

    def get_capability(self, execution_id: str) -> Optional[ControlCapability]:
        """Retrieve declared capabilities for an execution."""
        if not execution_id:
            return None
        with self._lock:
            cap = self._capabilities.get(execution_id.strip())
            return cap.model_copy(deep=True) if cap else None

    def supports_cancel(self, execution_id: str) -> bool:
        """Check whether the target execution supports cancellation."""
        cap = self.get_capability(execution_id)
        return bool(cap and cap.supports_cancel)

    def supports_throttle(self, execution_id: str) -> bool:
        """Check whether the target execution supports rate/delay throttling."""
        cap = self.get_capability(execution_id)
        return bool(cap and cap.supports_throttle)

    def supports_next_step_switch(self, execution_id: str) -> bool:
        """Check whether the target execution supports next-step model/provider switching."""
        cap = self.get_capability(execution_id)
        return bool(cap and cap.supports_next_step_switch)

    def supports_terminate(self, execution_id: str) -> bool:
        """Check whether the target execution supports process termination."""
        cap = self.get_capability(execution_id)
        return bool(cap and cap.supports_terminate)

    def supports_action(self, execution_id: str, action: GovernorAction) -> bool:
        """Check whether a specific GovernorAction can be physically handled."""
        if not execution_id or action is None:
            return False

        gov_action = GovernorAction(action) if not isinstance(action, GovernorAction) else action

        # CONTINUE is always safe and boundary-supported
        if gov_action == GovernorAction.CONTINUE:
            return True

        cap = self.get_capability(execution_id)
        if not cap:
            return False

        if gov_action in cap.supported_actions:
            return True

        if gov_action == GovernorAction.STOP:
            return bool(cap.supports_cancel or cap.supports_terminate)

        if gov_action == GovernorAction.THROTTLE:
            return bool(cap.supports_throttle)

        if gov_action == GovernorAction.SWITCH:
            return bool(cap.supports_next_step_switch)

        return False

    def dispatch_control(
        self,
        execution_id: str,
        action: GovernorAction,
        params: Optional[Dict[str, Any]] = None,
        operation_id: Optional[str] = None
    ) -> ControlResult:
        """Validate capability and dispatch a Governor decision to the physical control layer."""
        if not execution_id or not execution_id.strip():
            raise ValueError("execution_id must not be empty.")
        if action is None:
            raise ValueError("action must not be None.")

        exec_id = execution_id.strip()
        gov_action = GovernorAction(action) if not isinstance(action, GovernorAction) else action
        now = utc_now()
        params_dict = dict(params or {})

        with self._lock:
            seq = self._seq_counters.get(exec_id, 0) + 1
            self._seq_counters[exec_id] = seq

            op_id = operation_id or f"ctrl_op_{exec_id}_{seq}_{int(now.timestamp()*1000)}"

            # Idempotency check for repeated operation_id
            if op_id in self._operations:
                return self._operations[op_id].model_copy(deep=True)

            operation = ControlOperation(
                operation_id=op_id,
                execution_id=exec_id,
                action=gov_action,
                params=params_dict,
                dispatched_at=now
            )

            # 1. Publish ControlActionIssued event if bus is attached
            if self._bus is not None:
                try:
                    ev = ExecutionEvent(
                        event_id=f"ctrl_ev_{op_id}",
                        execution_id=exec_id,
                        type=EventType.CONTROL_ACTION_ISSUED,
                        source=EventSource.SYSTEM,
                        sequence=seq,
                        timestamp=now,
                        payload={
                            "action": gov_action.value if hasattr(gov_action, "value") else str(gov_action),
                            "operation_id": op_id,
                            "params": params_dict,
                            "target_boundary": "execution_control_boundary"
                        }
                    )
                    self._bus.publish(ev)
                except Exception:
                    pass

            # 2. Capability verification
            is_supported = self.supports_action(exec_id, gov_action)

            executor = self._executors.get(exec_id)
            executor_id = executor.executor_id if executor else None

            if not is_supported:
                # Safe failure: explicit UNSUPPORTED outcome, no false success or hidden fallback
                result = ControlResult(
                    operation_id=op_id,
                    execution_id=exec_id,
                    action=gov_action,
                    status=ControlStatus.UNSUPPORTED,
                    message=f"Control action '{gov_action.value}' is not supported for execution '{exec_id}'.",
                    executed_at=now,
                    metadata={"is_supported": False, "sequence": seq}
                )
            elif gov_action == GovernorAction.CONTINUE and executor is None:
                result = ControlResult(
                    operation_id=op_id,
                    execution_id=exec_id,
                    action=gov_action,
                    status=ControlStatus.COMPLETED,
                    message="Execution continue acknowledged.",
                    executed_at=now,
                    metadata={"is_supported": True, "sequence": seq}
                )
            elif executor is not None:
                try:
                    exec_result = executor.execute_control(operation)
                    # Ensure metadata and identity fidelity
                    result = ControlResult(
                        operation_id=op_id,
                        execution_id=exec_id,
                        action=gov_action,
                        status=exec_result.status,
                        message=exec_result.message,
                        executed_at=exec_result.executed_at or now,
                        metadata={**exec_result.metadata, "is_supported": True, "executor_id": executor_id, "sequence": seq}
                    )
                except Exception as ex:
                    result = ControlResult(
                        operation_id=op_id,
                        execution_id=exec_id,
                        action=gov_action,
                        status=ControlStatus.FAILED,
                        message=f"Control executor '{executor_id}' raised exception: {str(ex)}",
                        executed_at=now,
                        metadata={"is_supported": True, "error": str(ex), "sequence": seq}
                    )
            else:
                # Capability declared supported without physical executor
                result = ControlResult(
                    operation_id=op_id,
                    execution_id=exec_id,
                    action=gov_action,
                    status=ControlStatus.ACCEPTED,
                    message=f"Control action '{gov_action.value}' accepted for execution '{exec_id}'.",
                    executed_at=now,
                    metadata={"is_supported": True, "sequence": seq}
                )

            # Record caching and audit history
            audit_record = ControlAuditRecord(
                execution_id=exec_id,
                operation=operation,
                result=result,
                is_supported=is_supported,
                target_executor=executor_id,
                metadata={"sequence": seq}
            )

            self._operations[op_id] = result
            self._latest_results[exec_id] = result
            if exec_id not in self._history:
                self._history[exec_id] = [audit_record]
            else:
                self._history[exec_id].append(audit_record)

            return result.model_copy(deep=True)

    def get_latest_result(self, execution_id: str) -> Optional[ControlResult]:
        """Retrieve the most recent control result for an execution."""
        if not execution_id:
            return None
        with self._lock:
            res = self._latest_results.get(execution_id.strip())
            return res.model_copy(deep=True) if res else None

    def get_control_history(self, execution_id: str) -> List[ControlAuditRecord]:
        """Retrieve all control operations and outcomes for an execution in chronological order."""
        if not execution_id:
            return []
        with self._lock:
            hist = self._history.get(execution_id.strip(), [])
            return [rec.model_copy(deep=True) for rec in hist]

    def attach_to_bus(self, bus: IEventBus) -> None:
        """Attach to event bus for publishing ControlActionIssued events."""
        with self._lock:
            self._bus = bus

    def clear(self) -> None:
        """Clear all in-memory capabilities, executors, and history."""
        with self._lock:
            self._capabilities.clear()
            self._executors.clear()
            self._latest_results.clear()
            self._history.clear()
            self._operations.clear()
            self._seq_counters.clear()
