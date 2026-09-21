"""Tests for Universal Execution Contract."""

import unittest
from infuse.contracts.execution import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    TaskContext,
    OperationRequest,
    ExecutionRequirements,
    ExecutionContext,
    NormalizedResponse,
    ExecutionTelemetry,
)
from infuse.contracts.governor import GovernorAction, GovernorDecision
from infuse.contracts.state import ExecutionState


class TestExecutionContract(unittest.TestCase):
    """Test serialization, validation, and extensibility of execution contract."""

    def test_valid_execution_request(self):
        req = ExecutionRequest(
            request_id="req_001",
            task=TaskContext(task_id="task_101", description="Refactor auth middleware"),
            request=OperationRequest(
                messages=[{"role": "user", "content": "Refactor JWT validator"}],
                parameters={"temperature": 0.2}
            ),
            requirements=ExecutionRequirements(
                supports_tools=True,
                supports_vision=False,
                preferred_providers=["anthropic", "openai"]
            ),
            execution_context=ExecutionContext(
                session_id="sess_abc",
                agent_id="opencode",
                step_index=1
            )
        )
        self.assertEqual(req.request_id, "req_001")
        self.assertEqual(req.task.task_id, "task_101")
        self.assertTrue(req.requirements.supports_tools)
        self.assertEqual(req.schema_version, "1.0.0")

        # Roundtrip serialization
        json_data = req.model_dump_json()
        loaded = ExecutionRequest.model_validate_json(json_data)
        self.assertEqual(loaded.request_id, "req_001")
        self.assertEqual(loaded.task.description, "Refactor auth middleware")

    def test_valid_execution_result(self):
        res = ExecutionResult(
            execution_id="exec_001",
            request_id="req_001",
            status=ExecutionStatus.COMPLETED,
            response=NormalizedResponse(
                content="Refactored code snippet",
                role="assistant",
                finish_reason="stop"
            ),
            execution=ExecutionTelemetry(
                provider="anthropic",
                model="claude-sonnet",
                input_tokens=1500,
                cached_tokens=400,
                output_tokens=600,
                total_tokens=2100,
                cost_usd=0.015,
                latency_ms=840.5,
                state=ExecutionState.NORMAL
            ),
            decision=GovernorDecision(
                action=GovernorAction.CONTINUE,
                reason_codes=["WITHIN_BUDGET"]
            )
        )
        self.assertEqual(res.execution_id, "exec_001")
        self.assertEqual(res.status, ExecutionStatus.COMPLETED)
        self.assertEqual(res.execution.total_tokens, 2100)
        self.assertEqual(res.decision.action, GovernorAction.CONTINUE)

        # JSON Roundtrip
        json_str = res.model_dump_json()
        loaded = ExecutionResult.model_validate_json(json_str)
        self.assertEqual(loaded.execution.cost_usd, 0.015)
        self.assertEqual(loaded.execution.provider, "anthropic")

    def test_required_fields_validation(self):
        # Missing required task & request
        with self.assertRaises(Exception):
            ExecutionRequest(request_id="req_bad")

    def test_execution_telemetry_defaults(self):
        telemetry = ExecutionTelemetry()
        self.assertEqual(telemetry.input_tokens, 0)
        self.assertEqual(telemetry.cost_usd, 0.0)
        self.assertEqual(telemetry.state, ExecutionState.NORMAL)
        self.assertEqual(telemetry.requests_count, 1)


if __name__ == "__main__":
    unittest.main()
