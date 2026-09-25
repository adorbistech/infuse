"""INFUSE Block 32 — Path A: Execution Path Integration Suite.

Validates the full pipeline:
Request -> Policy -> Context -> Classifier -> Registry -> Resolver -> Router -> Provider -> Agent Adapter -> Result
across all 7 agent adapters:
- Universal
- Claude Code
- OpenCode
- Codex
- Hermes
- OpenClaw
- Lovable
"""

import unittest
import uuid

from infuse.contracts.execution import (
    ExecutionContext,
    ExecutionRequirements,
    ExecutionRequest,
    ExecutionStatus,
    OperationRequest,
    TaskContext,
)
from infuse.contracts.state import ExecutionState
from infuse.e2e.environment import EndToEndIntegrationEnvironment


class TestBlock32ExecutionPath(unittest.TestCase):
    """Verifies complete execution path integration across all supported agent adapters."""

    def setUp(self):
        self.env = EndToEndIntegrationEnvironment()

    def test_execution_path_all_agent_adapters(self):
        """Verify end-to-end execution path across all 7 supported agent adapters."""
        adapters_to_test = [
            "universal",
            "claude",
            "opencode",
            "codex",
            "hermes",
            "openclaw",
            "lovable",
        ]

        for adapter_name in adapters_to_test:
            with self.subTest(adapter=adapter_name):
                adapter = self.env.get_agent_adapter(adapter_name)
                self.assertIsNotNone(adapter, f"Adapter {adapter_name} should be available in environment.")

                req = ExecutionRequest(
                    request_id=f"req_{adapter_name}_{uuid.uuid4().hex[:6]}",
                    task=TaskContext(
                        task_id=f"task_{adapter_name}",
                        description=f"Generate unit tests using {adapter_name}",
                    ),
                    request=OperationRequest(
                        messages=[{"role": "user", "content": f"Write test for {adapter_name}"}]
                    ),
                    requirements=ExecutionRequirements(
                        preferred_providers=["mock"],
                        preferred_models=["mock-model"],
                    ),
                    execution_context=ExecutionContext(
                        session_id=f"sess_{adapter_name}",
                    ),
                )

                audit = self.env.execute_e2e(request=req, agent_adapter=adapter)

                # Verification of pipeline stages
                self.assertIsNotNone(audit.execution_id)
                self.assertEqual(audit.request_id, req.request_id)
                self.assertEqual(audit.selected_provider, "mock")
                self.assertEqual(audit.selected_model, "mock-model")
                self.assertIsNotNone(audit.workload_type)
                self.assertGreater(len(audit.events_recorded), 0)
                self.assertEqual(audit.final_state, ExecutionState.NORMAL)
                self.assertIsNotNone(audit.result)
                self.assertEqual(audit.result.status, ExecutionStatus.COMPLETED)
                self.assertIsNotNone(audit.result.response.content)
                self.assertEqual(audit.result.execution.state, ExecutionState.NORMAL)

    def test_execution_path_workload_classification_propagation(self):
        """Verify workload classification correctly infers code vs general tasks."""
        code_req = ExecutionRequest(
            request_id="req_code_task",
            task=TaskContext(
                task_id="task_code",
                description="Refactor Python class implementation and fix type annotations",
                workload_hint="coding",
            ),
            request=OperationRequest(
                messages=[{"role": "user", "content": "def test(): pass"}]
            ),
        )
        audit = self.env.execute_e2e(request=code_req)
        self.assertIn("coding", audit.workload_type.lower())
