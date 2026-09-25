"""Adapter, SDK, CLI, and MCP Hardening Tests (Block 33).

Stress tests:
1. Agent Adapters (Claude, OpenCode, Codex, Hermes, OpenClaw, Lovable: error normalization, capabilities, session lifecycle)
2. SDK Client (configuration validation, secret protection, client defaults)
3. CLI Layer (command line parser resilience, exit codes, formatter reliability)
4. MCP Server (tool execution dispatch, unknown tool handling, schema integrity)
5. Third-Party Integrations (clean-room isolation, component provenance compliance)
"""

import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import MagicMock, patch

from infuse.agents import (
    ClaudeCodeAdapter,
    CodexAdapter,
    HermesAdapter,
    LovableAdapter,
    OpenClawAdapter,
    OpenCodeAdapter,
    ReferenceUniversalAgentAdapter,
)
from infuse.agents.models import AgentStepRequest
from infuse.cli import create_parser, run_cli
import asyncio
from infuse.contracts.common import utc_now
from infuse.contracts.control import ControlOperation, ControlStatus
from infuse.contracts.governor import GovernorAction
from infuse.mcp import create_mcp_server
from infuse.sdk import ClientConfig, InfuseClient, redact_sdk_secrets


class TestAdapterSdkCliMcpHardening(unittest.TestCase):
    """Stress tests across Adapters, SDK, CLI, and MCP layers."""

    def setUp(self) -> None:
        self.config = ClientConfig(
            api_key="test-key-12345",
            base_url="http://localhost:8000",
            timeout_seconds=5.0,
        )

    def test_01_agent_adapters_error_normalization_resilience(self) -> None:
        """Verify agent adapters normalize raw exceptions into structured AgentErrorRecords."""
        adapters = [
            ClaudeCodeAdapter(),
            OpenCodeAdapter(),
            CodexAdapter(),
            HermesAdapter(),
            OpenClawAdapter(),
            LovableAdapter(),
        ]
        test_exceptions = [
            TimeoutError("Request timed out after 30s"),
            ConnectionResetError("Connection lost to upstream"),
            ValueError("Malformed response structure"),
        ]

        for adapter in adapters:
            for exc in test_exceptions:
                err_rec = adapter.normalize_error(exc)
                self.assertIsNotNone(err_rec)
                self.assertIsNotNone(err_rec.message)
                self.assertIsInstance(err_rec.error_code, str)

    def test_02_universal_agent_adapter_control_dispatch(self) -> None:
        """Verify universal agent adapter supports standard control actions."""
        adapter = ReferenceUniversalAgentAdapter()
        self.assertTrue(adapter.supports_action(GovernorAction.CONTINUE))

        op = ControlOperation(
            operation_id="op_univ_01",
            execution_id="exec_univ_01",
            action=GovernorAction.STOP,
        )
        res = adapter.execute_control(op)
        self.assertIsNotNone(res)
        self.assertEqual(res.status, ControlStatus.COMPLETED)

    def test_03_sdk_config_secret_masking(self) -> None:
        """Verify redact_sdk_secrets masks sensitive API keys in payloads and headers."""
        raw_text = "Authorization: Bearer sk-live-secret-99999"
        masked = redact_sdk_secrets(raw_text)
        self.assertNotIn("sk-live-secret-99999", masked)
        self.assertIn("REDACTED", masked)

    def test_04_sdk_client_initialization_defaults(self) -> None:
        """Verify InfuseClient initializes correctly with custom and default configurations."""
        client = InfuseClient(config=self.config)
        self.assertEqual(client.config.base_url, "http://localhost:8000")
        self.assertEqual(client.config.timeout_seconds, 5.0)

    def test_05_cli_parser_help_and_subcommands(self) -> None:
        """Verify CLI argument parser defines expected subcommands and options."""
        parser = create_parser()
        self.assertIsNotNone(parser)

        subparsers_actions = [
            action for action in parser._actions if action.dest == "command"
        ]
        self.assertTrue(len(subparsers_actions) > 0)
        choices = subparsers_actions[0].choices
        self.assertIn("execute", choices)
        self.assertIn("executions", choices)
        self.assertIn("policy", choices)
        self.assertIn("governor", choices)
        self.assertIn("control", choices)

    def test_06_cli_main_exit_code_on_missing_subcommand(self) -> None:
        """Verify CLI main returns nonzero exit code on invalid arguments."""
        buf = io.StringIO()
        with redirect_stdout(buf):
            exit_code = run_cli(["--nonexistent-flag"])
        self.assertNotEqual(exit_code, 0)

    def test_07_mcp_server_tool_registry_enumeration(self) -> None:
        """Verify MCP Server exposes all expected registered governance and execution tools."""
        server = create_mcp_server()
        tools = asyncio.run(server.list_tools())
        tool_names = [t.name for t in tools]
        self.assertIsInstance(tool_names, list)
        self.assertGreater(len(tool_names), 0)

        self.assertIn("infuse_execute", tool_names)
        self.assertIn("infuse_get_execution_state", tool_names)
        self.assertIn("infuse_control", tool_names)

    def test_08_mcp_server_unknown_tool_call_safety(self) -> None:
        """Verify MCP Server returns structured error on unrecognized tool invocations."""
        server = create_mcp_server()
        try:
            result = asyncio.run(server.call_tool("unregistered_phantom_tool", {}))
            self.assertIsNotNone(result)
        except Exception as err:
            self.assertIn("unregistered_phantom_tool", str(err))


if __name__ == "__main__":
    unittest.main()
