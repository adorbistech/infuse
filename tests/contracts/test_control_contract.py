"""Tests for Execution Control Boundary Contract."""

import unittest
from infuse.contracts.control import (
    ControlCapability,
    ControlOperation,
    ControlResult,
    ControlStatus,
)
from infuse.contracts.governor import GovernorAction


class TestControlContract(unittest.TestCase):
    """Test control boundary capabilities, dispatch operations, and safe outcome models."""

    def test_capability_discovery_defaults(self):
        cap = ControlCapability()
        self.assertFalse(cap.supports_cancel)
        self.assertFalse(cap.supports_throttle)
        self.assertFalse(cap.supports_next_step_switch)
        self.assertFalse(cap.supports_terminate)
        self.assertEqual(cap.supported_actions, [GovernorAction.CONTINUE])

    def test_full_capability_declaration(self):
        cap = ControlCapability(
            supports_cancel=True,
            supports_throttle=True,
            supports_next_step_switch=True,
            supports_terminate=True,
            supported_actions=[
                GovernorAction.CONTINUE,
                GovernorAction.OPTIMIZE,
                GovernorAction.SWITCH,
                GovernorAction.THROTTLE,
                GovernorAction.STOP
            ]
        )
        self.assertTrue(cap.supports_cancel)
        self.assertIn(GovernorAction.STOP, cap.supported_actions)

    def test_control_operation_and_result(self):
        op = ControlOperation(
            operation_id="op_991",
            execution_id="exec_100",
            action=GovernorAction.THROTTLE,
            params={"delay_ms": 500}
        )
        self.assertEqual(op.action, GovernorAction.THROTTLE)
        self.assertEqual(op.params["delay_ms"], 500)

        # Successful result
        res_ok = ControlResult(
            operation_id="op_991",
            execution_id="exec_100",
            action=GovernorAction.THROTTLE,
            status=ControlStatus.COMPLETED,
            message="Throttle applied successfully"
        )
        self.assertEqual(res_ok.status, ControlStatus.COMPLETED)

        # Safe unsupported failure result
        res_unsupported = ControlResult(
            operation_id="op_992",
            execution_id="exec_100",
            action=GovernorAction.DOWNGRADE,
            status=ControlStatus.UNSUPPORTED,
            message="Agent runtime does not support dynamic mid-flight downgrade"
        )
        self.assertEqual(res_unsupported.status, ControlStatus.UNSUPPORTED)


if __name__ == "__main__":
    unittest.main()
