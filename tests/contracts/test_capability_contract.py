"""Tests for Adapter Capability Contract."""

import unittest
from infuse.contracts.capabilities import (
    AdapterType,
    AgentCapability,
    ProviderCapability,
    AdapterRegistration,
)
from infuse.contracts.control import ControlCapability
from infuse.contracts.governor import GovernorAction


class TestCapabilityContract(unittest.TestCase):
    """Test capability declarations for agents and providers without coupling core."""

    def test_agent_capability_declaration(self):
        agent_cap = AgentCapability(
            agent_name="opencode",
            supported_protocols=["http", "stdio"],
            control_capabilities=ControlCapability(
                supports_cancel=True,
                supports_throttle=True,
                supports_next_step_switch=True,
                supported_actions=[
                    GovernorAction.CONTINUE,
                    GovernorAction.OPTIMIZE,
                    GovernorAction.SWITCH,
                    GovernorAction.THROTTLE,
                    GovernorAction.STOP
                ]
            ),
            supports_streaming_events=True,
            supports_tool_interception=True,
            supported_models=["claude-3-5-sonnet", "deepseek-chat"]
        )
        self.assertEqual(agent_cap.agent_name, "opencode")
        self.assertTrue(agent_cap.control_capabilities.supports_next_step_switch)

        reg = AdapterRegistration(
            adapter_id="adapter_agent_opencode_1",
            name="OpenCode Universal Adapter",
            version="1.0.0",
            adapter_type=AdapterType.AGENT,
            agent_capability=agent_cap
        )
        self.assertEqual(reg.adapter_type, AdapterType.AGENT)
        self.assertIsNotNone(reg.agent_capability)

    def test_provider_capability_declaration(self):
        prov_cap = ProviderCapability(
            provider_name="anthropic",
            supported_models=["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"],
            supports_streaming=True,
            supports_tool_calling=True,
            supports_caching=True,
            supports_vision=True,
            supports_structured_output=True,
            max_context_window=200000
        )
        self.assertEqual(prov_cap.provider_name, "anthropic")
        self.assertTrue(prov_cap.supports_caching)
        self.assertEqual(prov_cap.max_context_window, 200000)

        reg = AdapterRegistration(
            adapter_id="adapter_prov_anthropic_1",
            name="Anthropic LiteLLM Adapter",
            version="1.0.0",
            adapter_type=AdapterType.PROVIDER,
            provider_capability=prov_cap
        )
        self.assertEqual(reg.adapter_type, AdapterType.PROVIDER)
        self.assertIsNotNone(reg.provider_capability)


if __name__ == "__main__":
    unittest.main()
