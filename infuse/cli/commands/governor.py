"""Governor commands for INFUSE CLI (Block 29)."""

from infuse.cli.exit_codes import EXIT_SUCCESS
from infuse.cli.formatter import format_governor_info
from infuse.sdk.client import InfuseClient


def handle_governor(
    client: InfuseClient,
    execution_id: str,
    json_mode: bool = False,
) -> int:
    """Inspect Governor regulation posture and decision for an execution."""
    gov_info = client.get_governor_decision(execution_id)
    print(format_governor_info(gov_info, json_mode=json_mode))
    return EXIT_SUCCESS


__all__ = ["handle_governor"]
