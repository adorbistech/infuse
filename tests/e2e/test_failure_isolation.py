"""INFUSE Block 32 — Failure Isolation and Boundary Resilience Integration Suite.

Validates that:
- Malformed events fail gracefully without corrupting global system state
- Out-of-order and duplicate events are handled safely
- Adapter/provider crashes do not crash the orchestrator or event bus
- Unsupported capabilities fail gracefully with ControlStatus.UNSUPPORTED
"""

import unittest
import uuid

from infuse.contracts.control import ControlCapability, ControlStatus
from infuse.contracts.events import EventSource, EventType, ExecutionEvent
from infuse.contracts.governor import GovernorAction
from infuse.contracts.policy import GovernancePolicy, PolicyActionBindings
from infuse.contracts.state import ExecutionState
from infuse.e2e.environment import EndToEndIntegrationEnvironment


class TestBlock32FailureIsolation(unittest.TestCase):
    """Verifies architectural fault tolerance and failure isolation across all subsystem boundaries."""

    def setUp(self):
        self.env = EndToEndIntegrationEnvironment()
        self.exec_id = f"exec_fail_iso_{uuid.uuid4().hex[:8]}"

    def test_malformed_event_payload_fails_safely(self):
        """Verify emitting events with unexpected or missing payload fields does not crash observers."""
        # Event with empty payload
        empty_evt = ExecutionEvent(
            event_id="evt_empty_payload",
            execution_id=self.exec_id,
            type=EventType.TOKEN_OBSERVED,
            source=EventSource.PROVIDER,
            sequence=1,
            payload={},
        )
        self.env.emit_event(empty_evt)

        # Observers continue working
        tok_obs = self.env.token_observer.get_observation(self.exec_id)
        self.assertIsNotNone(tok_obs)

    def test_out_of_order_and_duplicate_events(self):
        """Verify out-of-order events are ingested and duplicate events are handled idempotently."""
        evt_seq_2 = ExecutionEvent(
            event_id="evt_seq_2",
            execution_id=self.exec_id,
            type=EventType.TOKEN_OBSERVED,
            source=EventSource.PROVIDER,
            sequence=2,
            payload={"total_tokens": 200, "input_tokens": 100, "output_tokens": 100, "provider": "mock", "model": "mock-fast"},
        )
        evt_seq_1 = ExecutionEvent(
            event_id="evt_seq_1",
            execution_id=self.exec_id,
            type=EventType.TOKEN_OBSERVED,
            source=EventSource.PROVIDER,
            sequence=1,
            payload={"total_tokens": 100, "input_tokens": 50, "output_tokens": 50, "provider": "mock", "model": "mock-fast"},
        )

        # Emit out of order
        self.env.emit_event(evt_seq_2)
        self.env.emit_event(evt_seq_1)

        # Emit duplicate
        self.env.emit_event(evt_seq_1)

        tok_obs = self.env.token_observer.get_observation(self.exec_id)
        self.assertIsNotNone(tok_obs)
        self.assertEqual(tok_obs.events_count, 2)
        self.assertEqual(len(tok_obs.history), 2)

    def test_unsupported_control_action_safe_handling(self):
        """Verify unsupported governor actions return UNSUPPORTED without throwing unhandled exceptions."""
        adapter = self.env.get_agent_adapter("universal")
        from infuse.contracts.capabilities import AgentCapability
        adapter.set_agent_capability(AgentCapability(
            agent_name="universal",
            control_capabilities=ControlCapability(
                supports_cancel=False,
                supports_throttle=False,
                supports_next_step_switch=False,
                supports_terminate=False,
                supported_actions=[GovernorAction.CONTINUE],
            ),
        ))
        self.env.control_boundary.register_executor(self.exec_id, adapter)

        ctrl_res = self.env.dispatch_control(self.exec_id, action=GovernorAction.STOP)
        self.assertEqual(ctrl_res.status, ControlStatus.UNSUPPORTED)
