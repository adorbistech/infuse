"""Authoritative Pre-Flight Execution Governance Engine for Block 21."""

import threading
import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional

from infuse.context.models import ExecutionContextRecord
from infuse.contracts.common import utc_now
from infuse.contracts.events import EventSource, EventType, ExecutionEvent
from infuse.contracts.execution import ExecutionRequest
from infuse.contracts.governor import GovernorAction, GovernorDecision, GovernorDecisionRecord
from infuse.contracts.policy import GovernancePolicy
from infuse.contracts.state import ExecutionState
from infuse.events.interfaces import IEventBus
from infuse.governor.budget import (
    BudgetExhaustedError,
    BudgetReservation,
    BudgetReservationManager,
    BudgetStoreError,
    BudgetStoreUnavailableError,
)


class PreFlightEvaluationResult:
    """Encapsulates the pre-flight governance gate evaluation outcome."""

    def __init__(
        self,
        is_allowed: bool,
        action: GovernorAction,
        reason_codes: List[str],
        message: str,
        decision_record: GovernorDecisionRecord,
        reservation: Optional[BudgetReservation] = None,
        estimated_cost: Decimal = Decimal("0.00"),
    ) -> None:
        self.is_allowed = is_allowed
        self.action = action
        self.reason_codes = reason_codes
        self.message = message
        self.decision_record = decision_record
        self.reservation = reservation
        self.estimated_cost = estimated_cost


class PreFlightGovernanceEngine:
    """Pre-flight policy, identity, provider eligibility, and budget gating authority.

    Executes STRICTLY BEFORE any provider adapter invocation or external action dispatch.
    Emits auditable GovernorDecision records and halts execution if policy or budget is breached.
    """

    def __init__(
        self,
        budget_manager: Optional[BudgetReservationManager] = None,
        event_bus: Optional[IEventBus] = None,
    ) -> None:
        self._lock = threading.RLock()
        self.budget_manager = budget_manager or BudgetReservationManager()
        self.event_bus = event_bus

    def evaluate(
        self,
        context: ExecutionContextRecord,
        request: ExecutionRequest,
        policy: Optional[GovernancePolicy] = None,
        target_provider: Optional[str] = None,
        target_model: Optional[str] = None,
    ) -> PreFlightEvaluationResult:
        """Evaluate pre-flight governance constraints against trusted server context and policy.

        Returns PreFlightEvaluationResult. If is_allowed is False, provider dispatch MUST NOT occur.
        """
        execution_id = context.execution_id
        now = utc_now()
        reasons: List[str] = []
        action: GovernorAction = GovernorAction.CONTINUE
        denial_message: Optional[str] = None
        reservation: Optional[BudgetReservation] = None
        estimated_cost = Decimal("0.00")

        selected_provider = (
            target_provider
            or (request.requirements.preferred_providers[0] if request.requirements and request.requirements.preferred_providers else "mock")
        )
        selected_model = (
            target_model
            or (request.requirements.preferred_models[0] if request.requirements and request.requirements.preferred_models else "mock-model")
        )

        with self._lock:
            # 1. Identity & Context Verification
            if not context or not context.execution_id:
                action = GovernorAction.STOP
                reasons.append("UNVERIFIED_EXECUTION_CONTEXT")
                denial_message = "Execution rejected: missing or unverified server-side execution context."

            # 2. Policy-Based Access Controls
            if action == GovernorAction.CONTINUE and policy:
                prov_ctrl = (
                    getattr(policy, "providers", None)
                    or getattr(policy, "provider_controls", None)
                    or getattr(policy, "provider_access", None)
                )
                if prov_ctrl:
                    blocked_provs = getattr(prov_ctrl, "blocked_providers", None) or []
                    allowed_provs = getattr(prov_ctrl, "allowed_providers", None)
                    blocked_models = getattr(prov_ctrl, "blocked_models", None) or []
                    allowed_models = getattr(prov_ctrl, "allowed_models", None)

                    if selected_provider in blocked_provs:
                        action = GovernorAction.STOP
                        reasons.append("PROVIDER_BLOCKED")
                        denial_message = f"Provider '{selected_provider}' is explicitly blocked by policy '{policy.policy_id}'."

                    elif allowed_provs is not None and selected_provider not in allowed_provs:
                        action = GovernorAction.STOP
                        reasons.append("PROVIDER_NOT_ALLOWED")
                        denial_message = f"Provider '{selected_provider}' is not in allowed providers list for policy '{policy.policy_id}'."

                    elif selected_model in blocked_models:
                        action = GovernorAction.STOP
                        reasons.append("MODEL_BLOCKED")
                        denial_message = f"Model '{selected_model}' is explicitly blocked by policy '{policy.policy_id}'."

                    elif allowed_models is not None and selected_model not in allowed_models:
                        action = GovernorAction.STOP
                        reasons.append("MODEL_NOT_ALLOWED")
                        denial_message = f"Model '{selected_model}' is not in allowed models list for policy '{policy.policy_id}'."

                # Token Bounds Verification
                tok_ctrl = getattr(policy, "tokens", None) or getattr(policy, "token_controls", None)
                if action == GovernorAction.CONTINUE and tok_ctrl:
                    max_in = getattr(tok_ctrl, "max_input_tokens", None)
                    if max_in is not None and request.request and request.request.messages:
                        char_len = sum(
                            len(str(m.get("content", "") if isinstance(m, dict) else getattr(m, "content", "")))
                            for m in request.request.messages
                        )
                        est_in = max(50, char_len // 4)
                        if est_in > max_in:
                            action = GovernorAction.STOP
                            reasons.append("INPUT_TOKENS_EXCEEDED")
                            denial_message = f"Estimated input tokens ({est_in}) exceed policy max_input_tokens limit ({max_in})."

            # 3. Pre-Flight Budget Gating & Reservation
            if action == GovernorAction.CONTINUE:
                try:
                    estimated_cost = self.budget_manager.estimate_cost(
                        request=request,
                        provider_id=selected_provider,
                        model_id=selected_model,
                    )
                    reservation = self.budget_manager.reserve(
                        execution_id=execution_id,
                        estimated_cost=estimated_cost,
                        policy=policy,
                        timestamp=now,
                    )
                except BudgetExhaustedError as exc:
                    action = GovernorAction.STOP
                    reasons.append("BUDGET_EXCEEDED")
                    denial_message = f"Pre-flight budget check denied execution: {exc.message}"
                except BudgetStoreUnavailableError as exc:
                    action = GovernorAction.STOP
                    reasons.append("BUDGET_STORE_UNAVAILABLE")
                    denial_message = f"Pre-flight budget check denied execution (Fail Closed): {exc.message}"
                except BudgetStoreError as exc:
                    action = GovernorAction.STOP
                    reasons.append("BUDGET_STORE_ERROR")
                    denial_message = f"Pre-flight budget check failed (Fail Closed): {exc.message}"

            # 4. Construct Decision Record
            is_allowed = action == GovernorAction.CONTINUE
            if is_allowed:
                reasons = ["PREFLIGHT_PASSED"] if not reasons else reasons
                message = f"Pre-flight governance checks passed for provider '{selected_provider}:{selected_model}'."
            else:
                message = denial_message or f"Execution halted by pre-flight governance policy (Action: {action.value})."

            decision_id = f"dec_preflight_{execution_id}_{int(now.timestamp()*1000)}"
            decision_record = GovernorDecisionRecord(
                decision_id=decision_id,
                execution_id=execution_id,
                action=action,
                reason_codes=reasons,
                message=message,
                evaluated_at=now,
                evaluated_state=str(ExecutionState.NORMAL.value if is_allowed else ExecutionState.COST_PRESSURE.value),
                signals={
                    "preflight_allowed": is_allowed,
                    "target_provider": selected_provider,
                    "target_model": selected_model,
                    "estimated_cost": float(estimated_cost),
                },
                effective_policy_id=policy.policy_id if policy else None,
                metadata={
                    "is_preflight": True,
                    "reservation_id": reservation.reservation_id if reservation else None,
                },
            )

            # 5. Publish Pre-flight Governor Decision Event
            if self.event_bus:
                try:
                    event = ExecutionEvent(
                        event_id=f"evt_preflight_{decision_id}",
                        execution_id=execution_id,
                        type=EventType.GOVERNOR_DECISION,
                        source=EventSource.GOVERNOR,
                        sequence=0,
                        timestamp=now,
                        payload=GovernorDecision(
                            action=action,
                            reason_codes=reasons,
                            message=message,
                            metadata=decision_record.metadata,
                        ).model_dump(),
                    )
                    self.event_bus.publish(event)
                except Exception:
                    pass

            return PreFlightEvaluationResult(
                is_allowed=is_allowed,
                action=action,
                reason_codes=reasons,
                message=message,
                decision_record=decision_record,
                reservation=reservation,
                estimated_cost=estimated_cost,
            )
