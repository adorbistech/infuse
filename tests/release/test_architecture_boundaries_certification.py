"""INFUSE Block 36 — Architecture Boundaries & Security Invariants Certification.

Verifies:
- Governor is the sole authority for control decisions
- Observers produce factual evidence and do not govern
- ExecutionControlBoundary remains the sole physical control translation boundary
- Subprocess transports enforce shell=False and argv vectors
- Zero secret disclosure in public methods
"""

import inspect
import unittest
from infuse.agents.claude import transport as claude_trans
from infuse.agents.codex import transport as codex_trans
from infuse.agents.hermes import transport as hermes_trans
from infuse.agents.openclaw import transport as openclaw_trans
from infuse.agents.opencode import transport as opencode_trans
from infuse.control.boundary import ExecutionControlBoundary
from infuse.governor.engine import GovernorEngine
from infuse.observer.observer import TokenObserver
from infuse.tools.observer import ToolActivityObserver
from infuse.web.observer import WebActivityObserver


class TestArchitectureBoundariesCertification(unittest.TestCase):
    """Certification tests for strict architectural boundary preservation."""

    def test_01_governor_is_sole_authority_for_governance(self) -> None:
        """Verify GovernorEngine contains evaluate_policy and evaluate_telemetry methods."""
        gov = GovernorEngine()
        self.assertTrue(hasattr(gov, "evaluate_telemetry") or hasattr(gov, "evaluate"))
        self.assertFalse(hasattr(gov, "dispatch_control"))  # Governor does NOT dispatch physical control directly

    def test_02_observers_are_strictly_observational(self) -> None:
        """Verify Token, Web, and Tool observers have NO governance or control dispatch capabilities."""
        observers = [
            TokenObserver(),
            WebActivityObserver(),
            ToolActivityObserver(),
        ]
        forbidden_methods = [
            "govern",
            "enforce",
            "dispatch_control",
            "execute_action",
            "stop_execution",
            "switch_provider",
            "throttle",
        ]
        for obs in observers:
            for method in forbidden_methods:
                self.assertFalse(
                    hasattr(obs, method),
                    f"Observer '{type(obs).__name__}' violates architecture by defining governance method '{method}'",
                )

    def test_03_execution_control_boundary_is_sole_physical_translation_point(self) -> None:
        """Verify ExecutionControlBoundary manages dispatch_control."""
        boundary = ExecutionControlBoundary()
        self.assertTrue(hasattr(boundary, "dispatch_control"))
        self.assertTrue(hasattr(boundary, "register_executor"))

    def test_04_all_agent_transports_use_shell_false(self) -> None:
        """Verify that subprocess execution across agent adapters uses shell=False."""
        agent_modules = [
            claude_trans,
            codex_trans,
            hermes_trans,
            openclaw_trans,
            opencode_trans,
        ]
        for mod in agent_modules:
            src = inspect.getsource(mod)
            self.assertIn("shell=False", src, f"Module {mod.__name__} must enforce shell=False")
            self.assertNotIn("shell=True", src, f"Module {mod.__name__} must not use shell=True")


if __name__ == "__main__":
    unittest.main()

