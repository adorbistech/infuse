"""Cross-adapter integration and execution isolation tests for Block 27 adapters."""

import unittest
from typing import List

from infuse.agents.hermes import HermesAdapter, HermesReferenceTransport
from infuse.agents.openclaw import OpenClawAdapter, OpenClawReferenceTransport
from infuse.agents.lovable import LovableAdapter, LovableReferenceTransport
from infuse.agents.interfaces import IUniversalAgentAdapter
from infuse.agents.models import AgentStepRequest
from infuse.contracts.control import ControlOperation, ControlStatus
from infuse.contracts.events import EventType, ExecutionEvent
from infuse.contracts.governor import GovernorAction
from infuse.events.bus import InMemoryEventBus


class TestMultiAgentIsolation(unittest.TestCase):
    """Test suite proving isolation and contract parity across Hermes, OpenClaw, and Lovable."""

    def setUp(self) -> None:
        self.bus = InMemoryEventBus()
        self.hermes_transport = HermesReferenceTransport()
        self.openclaw_transport = OpenClawReferenceTransport()
        self.lovable_transport = LovableReferenceTransport()

        self.hermes = HermesAdapter(
            agent_id="hermes_agent",
            transport=self.hermes_transport,
            event_bus=self.bus,
        )
        self.openclaw = OpenClawAdapter(
            agent_id="openclaw_agent",
            transport=self.openclaw_transport,
            event_bus=self.bus,
        )
        self.lovable = LovableAdapter(
            agent_id="lovable_agent",
            transport=self.lovable_transport,
            event_bus=self.bus,
        )

    def test_01_all_adapters_satisfy_universal_contract(self) -> None:
        adapters: List[IUniversalAgentAdapter] = [self.hermes, self.openclaw, self.lovable]
        for adp in adapters:
            self.assertIsInstance(adp, IUniversalAgentAdapter)
            cap = adp.get_agent_capability()
            self.assertTrue(cap.control_capabilities.supports_cancel)
            self.assertTrue(cap.control_capabilities.supports_terminate)
            self.assertFalse(cap.control_capabilities.supports_throttle)
            self.assertFalse(cap.control_capabilities.supports_next_step_switch)

    def test_02_concurrent_execution_isolation(self) -> None:
        events: List[ExecutionEvent] = []
        self.bus.subscribe(lambda e: events.append(e))

        req_h = AgentStepRequest(execution_id="exec_hermes_99", step_index=0, prompt="Task Hermes")
        req_o = AgentStepRequest(execution_id="exec_openclaw_99", step_index=0, prompt="Task OpenClaw")
        req_l = AgentStepRequest(execution_id="exec_lovable_99", step_index=0, prompt="Task Lovable")

        resp_h = self.hermes.execute_step(req_h)
        resp_o = self.openclaw.execute_step(req_o)
        resp_l = self.lovable.execute_step(req_l)

        # Check distinct execution IDs
        self.assertEqual(resp_h.execution_id, "exec_hermes_99")
        self.assertEqual(resp_o.execution_id, "exec_openclaw_99")
        self.assertEqual(resp_l.execution_id, "exec_lovable_99")

        # Check distinct transport invocations
        self.assertEqual(len(self.hermes_transport.invocations), 1)
        self.assertEqual(len(self.openclaw_transport.invocations), 1)
        self.assertEqual(len(self.lovable_transport.invocations), 1)

        self.assertEqual(self.hermes_transport.invocations[0]["execution_id"], "exec_hermes_99")
        self.assertEqual(self.openclaw_transport.invocations[0]["execution_id"], "exec_openclaw_99")
        self.assertEqual(self.lovable_transport.invocations[0]["execution_id"], "exec_lovable_99")

        # Check events published on bus carry exact execution IDs
        hermes_evs = [e for e in events if e.execution_id == "exec_hermes_99"]
        openclaw_evs = [e for e in events if e.execution_id == "exec_openclaw_99"]
        lovable_evs = [e for e in events if e.execution_id == "exec_lovable_99"]

        self.assertEqual(len(hermes_evs), 1)
        self.assertEqual(len(openclaw_evs), 1)
        self.assertEqual(len(lovable_evs), 1)

    def test_03_control_isolation_across_adapters(self) -> None:
        op_h = ControlOperation(operation_id="op_h", execution_id="exec_hermes_99", action=GovernorAction.STOP)
        op_o = ControlOperation(operation_id="op_o", execution_id="exec_openclaw_99", action=GovernorAction.STOP)
        op_l = ControlOperation(operation_id="op_l", execution_id="exec_lovable_99", action=GovernorAction.STOP)

        res_h = self.hermes.execute_control(op_h)
        res_o = self.openclaw.execute_control(op_o)
        res_l = self.lovable.execute_control(op_l)

        self.assertEqual(res_h.status, ControlStatus.COMPLETED)
        self.assertEqual(res_o.status, ControlStatus.COMPLETED)
        self.assertEqual(res_l.status, ControlStatus.COMPLETED)

        self.assertIn("exec_hermes_99", self.hermes_transport.cancelled_executions)
        self.assertNotIn("exec_hermes_99", self.openclaw_transport.cancelled_executions)
        self.assertNotIn("exec_hermes_99", self.lovable_transport.cancelled_executions)

    def test_04_unsupported_actions_consistently_rejected(self) -> None:
        adapters = [self.hermes, self.openclaw, self.lovable]
        for adp in adapters:
            op_throttle = ControlOperation(operation_id="op_t", execution_id="exec_iso_x", action=GovernorAction.THROTTLE)
            op_switch = ControlOperation(operation_id="op_s", execution_id="exec_iso_x", action=GovernorAction.SWITCH)

            res_t = adp.execute_control(op_throttle)
            res_s = adp.execute_control(op_switch)

            self.assertEqual(res_t.status, ControlStatus.UNSUPPORTED)
            self.assertEqual(res_s.status, ControlStatus.UNSUPPORTED)


if __name__ == "__main__":
    unittest.main()
