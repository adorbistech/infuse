"""INFUSE Block 34 — Subprocess Security and Command Injection Resistance Suite.

Validates that:
- Subprocess executions across adapters use structural argument arrays (shell=False)
- Shell metacharacters (; && || | ` $() newline) are not evaluated by shell interpreters
- Path traversal sequences in arguments are safely handled
- Subprocess timeouts kill the process deterministically
"""

import sys
import unittest
from unittest.mock import MagicMock, patch

from infuse.agents.claude.errors import ClaudeTimeoutError
from infuse.agents.claude.transport import ClaudeSubprocessTransport
from infuse.agents.codex.transport import CodexSubprocessTransport
from infuse.agents.hermes.transport import HermesSubprocessTransport
from infuse.agents.openclaw.transport import OpenClawSubprocessTransport
from infuse.agents.opencode.transport import OpenCodeSubprocessTransport


class TestSubprocessInjectionSecurity(unittest.TestCase):
    """Verifies subprocess execution safety and command injection resistance."""

    def test_01_claude_transport_uses_shell_false_and_structural_args(self) -> None:
        """Verify Claude transport launches subprocesses with shell=False and structural argv."""
        transport = ClaudeSubprocessTransport(cli_path=sys.executable)
        malicious_args = [
            "-c",
            "import sys; print('safe_run')",
            "; rm -rf /",
            "&& touch /tmp/pwned",
            "| cat /etc/passwd",
            "`id`",
            "$(whoami)",
        ]

        with patch("subprocess.Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_proc.communicate.return_value = ('{"status": "ok"}', "")
            mock_proc.returncode = 0
            mock_popen.return_value = mock_proc

            out = transport.execute(args=malicious_args, execution_id="exec_test_claude")

            mock_popen.assert_called_once()
            call_kwargs = mock_popen.call_args[1]
            call_args = mock_popen.call_args[0][0]

            # Critical assertions: shell MUST be False, args must be exact list
            self.assertFalse(call_kwargs.get("shell", True))
            self.assertEqual(call_args[0], sys.executable)
            for malicious in malicious_args:
                self.assertIn(malicious, call_args)

    def test_02_opencode_transport_shell_false_and_command_injection_safety(self) -> None:
        """Verify OpenCode transport enforces shell=False and structural arguments."""
        transport = OpenCodeSubprocessTransport(cli_path=sys.executable)
        injection_payload = ["--prompt", "hello; cat /etc/shadow\nwhoami"]

        with patch("subprocess.Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_proc.communicate.return_value = ('{"ok": true}', "")
            mock_proc.returncode = 0
            mock_popen.return_value = mock_proc

            transport.execute(args=injection_payload, execution_id="exec_test_opencode")

            self.assertFalse(mock_popen.call_args[1].get("shell", True))
            self.assertIn("--prompt", mock_popen.call_args[0][0])
            self.assertIn(injection_payload[1], mock_popen.call_args[0][0])

    def test_03_codex_transport_shell_false_enforcement(self) -> None:
        """Verify Codex transport uses shell=False."""
        transport = CodexSubprocessTransport(cli_path=sys.executable)
        with patch("subprocess.Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_proc.communicate.return_value = ("ok", "")
            mock_proc.returncode = 0
            mock_popen.return_value = mock_proc

            transport.execute(args=["--test", "$(id)"], execution_id="exec_codex")
            self.assertFalse(mock_popen.call_args[1].get("shell", True))

    def test_04_hermes_transport_shell_false_enforcement(self) -> None:
        """Verify Hermes transport uses shell=False."""
        transport = HermesSubprocessTransport(cli_path=sys.executable)
        with patch("subprocess.Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_proc.communicate.return_value = ("ok", "")
            mock_proc.returncode = 0
            mock_popen.return_value = mock_proc

            transport.execute(args=["--eval", "`echo test`"], execution_id="exec_hermes")
            self.assertFalse(mock_popen.call_args[1].get("shell", True))

    def test_05_openclaw_transport_shell_false_enforcement(self) -> None:
        """Verify OpenClaw transport uses shell=False."""
        transport = OpenClawSubprocessTransport(cli_path=sys.executable)
        with patch("subprocess.Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_proc.communicate.return_value = ("ok", "")
            mock_proc.returncode = 0
            mock_popen.return_value = mock_proc

            transport.execute(args=["--flag", "val | nc -e /bin/sh"], execution_id="exec_openclaw")
            self.assertFalse(mock_popen.call_args[1].get("shell", True))

    def test_06_path_traversal_in_arguments_remains_literal(self) -> None:
        """Verify path traversal sequences (../../..) are preserved as inert literal strings."""
        transport = ClaudeSubprocessTransport(cli_path=sys.executable)
        traversal_args = ["--file", "../../../../../etc/passwd"]

        with patch("subprocess.Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_proc.communicate.return_value = ("{}", "")
            mock_proc.returncode = 0
            mock_popen.return_value = mock_proc

            transport.execute(args=traversal_args, execution_id="exec_traversal")
            self.assertIn("../../../../../etc/passwd", mock_popen.call_args[0][0])
            self.assertFalse(mock_popen.call_args[1].get("shell", True))

    def test_07_subprocess_timeout_termination(self) -> None:
        """Verify subprocess timeout triggers process.kill() and raises typed timeout error."""
        import subprocess
        transport = ClaudeSubprocessTransport(cli_path=sys.executable, default_timeout=0.1)

        with patch("subprocess.Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_proc.communicate.side_effect = [
                subprocess.TimeoutExpired(cmd=["test"], timeout=0.1),
                ("", ""),
            ]
            mock_popen.return_value = mock_proc

            with self.assertRaises(ClaudeTimeoutError):
                transport.execute(args=["sleep", "10"], execution_id="exec_timeout")

            mock_proc.kill.assert_called_once()


if __name__ == "__main__":
    unittest.main()
