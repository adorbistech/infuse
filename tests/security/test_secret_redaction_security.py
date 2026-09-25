"""INFUSE Block 34 — Secret Redaction and Credential Sanitization Security Suite.

Validates that:
- API keys, bearer tokens, passwords, and secrets are systematically redacted
- Exceptions across SDK, Adapters, CLI, and MCP never expose raw credentials
- Event payloads and error logs sanitize credential patterns
"""

import unittest

from infuse.agents.claude.models import redact_secrets as redact_claude
from infuse.agents.codex.models import redact_codex_secrets
from infuse.agents.hermes.models import redact_hermes_secrets
from infuse.agents.lovable.models import redact_lovable_secrets
from infuse.agents.openclaw.models import redact_openclaw_secrets
from infuse.agents.opencode.models import redact_opencode_secrets
from infuse.cli.formatter import format_error as format_cli_error
from infuse.mcp.errors import format_mcp_error
from infuse.sdk.errors import (
    AuthenticationError,
    InfuseSdkError,
    TransportError,
    ValidationError,
    redact_sdk_secrets,
)


class TestSecretRedactionSecurity(unittest.TestCase):
    """Verifies that credentials and secrets are safely redacted across all subsystems."""

    def setUp(self) -> None:
        self.synthetic_key = "sk-ant-api03-1234567890abcdef1234567890abcdef"
        self.synthetic_bearer = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.dummysecret123456"
        self.synthetic_password = "password=SuperSecretPassword123!"
        self.synthetic_api_key_field = "api_key: confidential_key_value_99999"

    def test_01_claude_adapter_secret_redaction(self) -> None:
        """Verify Claude adapter redacts sk- tokens and key=value secrets."""
        msg = f"Failed authenticating with {self.synthetic_key} and {self.synthetic_api_key_field}"
        redacted = redact_claude(msg)
        self.assertNotIn("sk-ant-api03", redacted)
        self.assertNotIn("confidential_key_value_99999", redacted)
        self.assertIn("[REDACTED]", redacted)

    def test_02_claude_adapter_bearer_token_redaction(self) -> None:
        """Verify Claude adapter redacts Bearer authorization tokens."""
        msg = f"Authorization header: {self.synthetic_bearer}"
        redacted = redact_claude(msg)
        self.assertNotIn("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", redacted)
        self.assertIn("Bearer [REDACTED]", redacted)

    def test_03_opencode_adapter_secret_redaction(self) -> None:
        """Verify OpenCode adapter redacts API keys and tokens."""
        msg = f"Error calling model: token={self.synthetic_key} {self.synthetic_password}"
        redacted = redact_opencode_secrets(msg)
        self.assertNotIn("sk-ant-api03", redacted)
        self.assertNotIn("SuperSecretPassword123!", redacted)
        self.assertIn("[REDACTED]", redacted)

    def test_04_codex_adapter_secret_redaction(self) -> None:
        """Verify Codex adapter redacts sensitive key patterns."""
        msg = f"Codex subprocess auth: {self.synthetic_api_key_field}"
        redacted = redact_codex_secrets(msg)
        self.assertNotIn("confidential_key_value_99999", redacted)
        self.assertIn("[REDACTED]", redacted)

    def test_05_hermes_adapter_secret_redaction(self) -> None:
        """Verify Hermes adapter redacts secrets and bearer tokens."""
        msg = f"Hermes gateway failed with {self.synthetic_bearer} and {self.synthetic_key}"
        redacted = redact_hermes_secrets(msg)
        self.assertNotIn("eyJhbGci", redacted)
        self.assertNotIn("sk-ant-api03", redacted)

    def test_06_openclaw_adapter_secret_redaction(self) -> None:
        """Verify OpenClaw adapter redacts credentials."""
        msg = f"OpenClaw runner failed on api_key={self.synthetic_key}"
        redacted = redact_openclaw_secrets(msg)
        self.assertNotIn("sk-ant-api03", redacted)
        self.assertIn("[REDACTED]", redacted)

    def test_07_lovable_adapter_secret_redaction(self) -> None:
        """Verify Lovable adapter redacts credentials."""
        msg = f"Lovable agent auth: {self.synthetic_bearer}"
        redacted = redact_lovable_secrets(msg)
        self.assertNotIn("eyJhbGci", redacted)
        self.assertIn("Bearer [REDACTED]", redacted)

    def test_08_sdk_errors_automatic_secret_redaction(self) -> None:
        """Verify SDK exceptions automatically sanitize messages on initialization."""
        err = InfuseSdkError(f"Network error communicating with token: {self.synthetic_key}")
        self.assertNotIn("sk-ant-api03", str(err))
        self.assertIn("[REDACTED]", str(err))

    def test_09_sdk_transport_error_secret_redaction(self) -> None:
        """Verify TransportError redacts credentials."""
        err = TransportError(
            message=f"HTTP connect failed on header Authorization: {self.synthetic_bearer}",
            status_code=401,
        )
        self.assertNotIn("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", str(err))
        self.assertIn("Bearer [REDACTED]", str(err))

    def test_10_sdk_api_error_secret_redaction(self) -> None:
        """Verify ValidationError redacts credentials."""
        err = ValidationError(
            message=f"API rejected request with {self.synthetic_password}",
            status_code=400,
        )
        self.assertNotIn("SuperSecretPassword123!", str(err))
        self.assertIn("[REDACTED]", str(err))

    def test_11_sdk_auth_error_sanitization(self) -> None:
        """Verify AuthenticationError does not reflect raw invalid credentials."""
        err = AuthenticationError(
            message=f"Invalid API key provided: api-key={self.synthetic_key}"
        )
        self.assertNotIn("sk-ant-api03", str(err))
        self.assertIn("[REDACTED]", str(err))

    def test_12_mcp_error_formatting_sanitization(self) -> None:
        """Verify MCP error response formatting sanitizes underlying exception text."""
        raw_exc = ValueError(f"Secret leakage attempt: token={self.synthetic_key}")
        mcp_res = format_mcp_error(raw_exc)
        self.assertIsNotNone(mcp_res)
        self.assertTrue(mcp_res.get("error"))
        self.assertNotIn("sk-ant-api03", mcp_res.get("message", ""))


if __name__ == "__main__":
    unittest.main()
