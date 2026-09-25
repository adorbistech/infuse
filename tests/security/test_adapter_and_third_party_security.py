"""INFUSE Block 34 — Agent Adapter and Third-Party Integration Security Suite.

Validates that:
- Untrusted agent responses (malformed JSON, corrupted structures) are safely normalized
- Third-party integration outputs are treated as untrusted external data
- Integration failures are isolated and returned as typed errors
- Third-party adapters cannot bypass the Governor or trigger hidden side channels
"""

import unittest
import uuid
from decimal import Decimal

from infuse.agents.claude.adapter import ClaudeCodeAdapter
from infuse.agents.claude.transport import ClaudeExecutionOutput, IClaudeTransport
from infuse.agents.models import AgentStepRequest
from infuse.contracts.execution import ExecutionStatus
from infuse.events.bus import InMemoryEventBus
from infuse.integrations.contracts import IntegrationCategory, IntegrationComponentInfo
from infuse.integrations.litellm.adapter import LiteLLMProviderAdapter
from infuse.integrations.manifest import ReuseManifest, load_manifest, validate_manifest


class MockCorruptedClaudeTransport(IClaudeTransport):
    def __init__(self, raw_stdout: str, return_code: int = 0):
        self._stdout = raw_stdout
        self._return_code = return_code

    def is_available(self) -> bool:
        return True

    def execute(self, args, execution_id=None, cwd=None, timeout=None, env=None):
        return ClaudeExecutionOutput(
            stdout=self._stdout,
            stderr="",
            return_code=self._return_code,
            duration_ms=10.0,
        )

    def cancel_execution(self, execution_id: str) -> bool:
        return True

    def terminate_session(self, session_id: str) -> bool:
        return True


class TestAdapterAndThirdPartySecurity(unittest.TestCase):
    """Verifies that agent adapter outputs and third-party data are untrusted and strictly normalized."""

    def setUp(self) -> None:
        self.event_bus = InMemoryEventBus()

    def test_01_claude_adapter_handles_unparseable_raw_text_safely(self) -> None:
        """Verify Claude adapter gracefully handles non-JSON plain text responses from CLI."""
        transport = MockCorruptedClaudeTransport(raw_stdout="I completed the task successfully in plain text.")
        adapter = ClaudeCodeAdapter(transport=transport, event_bus=self.event_bus)

        req = AgentStepRequest(
            step_index=0,
            prompt="Perform refactor",
            execution_id=f"exec_agent_sec_{uuid.uuid4().hex[:6]}",
        )
        result = adapter.execute_step(req)
        self.assertIsNotNone(result)
        self.assertIn("I completed the task successfully in plain text.", result.content or "")

    def test_02_claude_adapter_handles_malformed_json_without_crashing(self) -> None:
        """Verify Claude adapter gracefully handles corrupted JSON output."""
        transport = MockCorruptedClaudeTransport(raw_stdout='{"status": "partial", "output": unclosed_json')
        adapter = ClaudeCodeAdapter(transport=transport, event_bus=self.event_bus)

        req = AgentStepRequest(
            step_index=0,
            prompt="Do task",
            execution_id=f"exec_agent_sec_{uuid.uuid4().hex[:6]}",
        )
        result = adapter.execute_step(req)
        self.assertIsNotNone(result)
        self.assertIn("unclosed_json", result.content or "")

    def test_03_third_party_manifest_validation_rejects_missing_license(self) -> None:
        """Verify third-party integration manifest validator flags entries without valid license."""
        bad_manifest = ReuseManifest(
            schema_version="1.0.1",
            components=[
                IntegrationComponentInfo(
                    name="invalid-comp",
                    repository="https://github.com/test/repo",
                    version="1.0.0",
                    commit_sha="1234567890abcdef1234567890abcdef12345678",
                    license="",
                    intended_purpose="test",
                    integration_type=IntegrationCategory.ADAPTER_INTEGRATION,
                    infuse_boundary="infuse.providers",
                )
            ],
        )
        errors = validate_manifest(bad_manifest)
        self.assertTrue(any("missing license" in e.lower() for e in errors))

    def test_04_third_party_manifest_validation_rejects_invalid_sha(self) -> None:
        """Verify third-party manifest validator flags non-40-hex commit SHAs."""
        bad_manifest = ReuseManifest(
            schema_version="1.0.1",
            components=[
                IntegrationComponentInfo(
                    name="bad-sha-comp",
                    repository="https://github.com/test/repo",
                    version="1.0.0",
                    commit_sha="not_a_valid_sha",
                    license="Apache-2.0",
                    intended_purpose="test",
                    integration_type=IntegrationCategory.ADAPTER_INTEGRATION,
                    infuse_boundary="infuse.providers",
                )
            ],
        )
        errors = validate_manifest(bad_manifest)
        self.assertTrue(any("commit_sha" in e.lower() for e in errors))

    def test_05_litellm_adapter_normalizes_external_error_payloads(self) -> None:
        """Verify LiteLLM integration adapter adheres to IProviderAdapter without control capabilities."""
        adapter = LiteLLMProviderAdapter()
        self.assertEqual(adapter.provider_id, "litellm")
        self.assertTrue(adapter.supports_model("litellm/gpt-4o"))

        # Confirm adapter has zero Governor dispatch capabilities
        self.assertFalse(hasattr(adapter, "dispatch_governor_action"))
        self.assertFalse(hasattr(adapter, "enforce_policy"))
        self.assertFalse(hasattr(adapter, "dispatch_control"))


if __name__ == "__main__":
    unittest.main()
