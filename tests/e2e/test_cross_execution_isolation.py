"""INFUSE Block 32 — Cross-Execution Isolation and Concurrency Suite.

Validates that:
- Multiple concurrent executions run in complete isolation
- `execution_id` correlation is strictly preserved across all observers, state, and governance
- State or telemetry from Execution A never leaks into Execution B
"""

import concurrent.futures
import unittest
import uuid

from infuse.contracts.events import EventSource, EventType, ExecutionEvent
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


class TestBlock32CrossExecutionIsolation(unittest.TestCase):
    """Verifies strict cross-execution isolation, correlation, and multi-threaded safety."""

    def setUp(self):
        self.env = EndToEndIntegrationEnvironment()

    def test_concurrent_executions_have_zero_cross_leakage(self):
        """Verify executing 10 concurrent requests preserves complete isolation."""
        num_executions = 10

        def run_single(index: int):
            req_id = f"req_conc_{index}_{uuid.uuid4().hex[:6]}"
            req = ExecutionRequest(
                request_id=req_id,
                task=TaskContext(
                    task_id=f"task_{index}",
                    description=f"Concurrent execution task number {index}",
                ),
                request=OperationRequest(
                    messages=[{"role": "user", "content": f"Execute concurrent step {index}"}]
                ),
            )
            return self.env.execute_e2e(request=req)

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
            futures = [pool.submit(run_single, i) for i in range(num_executions)]
            audits = [f.result() for f in futures]

        self.assertEqual(len(audits), num_executions)

        # Check unique execution IDs
        exec_ids = [a.execution_id for a in audits]
        self.assertEqual(len(set(exec_ids)), num_executions)

        # Verify telemetry isolation for each execution
        for a in audits:
            tok_obs = self.env.token_observer.get_observation(a.execution_id)
            self.assertIsNotNone(tok_obs)
            self.assertEqual(tok_obs.execution_id, a.execution_id)

            health = self.env.health_engine.get_execution_health(a.execution_id)
            self.assertIsNotNone(health)
            self.assertEqual(health.execution_id, a.execution_id)

            econ = self.env.economics_engine.get_summary(a.execution_id)
            self.assertIsNotNone(econ)
            self.assertEqual(econ.execution_id, a.execution_id)

            # Confirm events belonging to this execution only
            for evt in a.events_recorded:
                self.assertEqual(evt.execution_id, a.execution_id)

    def test_execution_id_correlation_preserved_across_pipeline(self):
        """Verify correlation IDs match from request through result."""
        req_id = f"req_corr_{uuid.uuid4().hex[:8]}"
        req = ExecutionRequest(
            request_id=req_id,
            task=TaskContext(task_id="task_corr", description="Verify correlation tracking"),
            request=OperationRequest(messages=[{"role": "user", "content": "Trace correlation"}]),
        )
        audit = self.env.execute_e2e(request=req)

        self.assertEqual(audit.request_id, req_id)
        self.assertEqual(audit.result.request_id, req_id)
        self.assertEqual(audit.result.execution_id, audit.execution_id)
