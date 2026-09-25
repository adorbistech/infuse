"""Information and configuration commands for INFUSE CLI (Block 29)."""

from infuse.cli.exit_codes import EXIT_SUCCESS
from infuse.cli.formatter import format_config, format_json
from infuse.sdk.client import InfuseClient
from infuse.version import SCHEMA_VERSION, __version__


def handle_version(json_mode: bool = False) -> int:
    """Display INFUSE CLI and schema version."""
    if json_mode:
        data = {
            "version": __version__,
            "schema_version": SCHEMA_VERSION,
            "layer": "Block 29 — CLI",
        }
        print(format_json(data))
    else:
        print(f"INFUSE CLI v{__version__} (Schema v{SCHEMA_VERSION})")
    return EXIT_SUCCESS


def handle_config(client: InfuseClient, json_mode: bool = False) -> int:
    """Display current active client configuration."""
    print(format_config(client.config, json_mode=json_mode))
    return EXIT_SUCCESS


__all__ = [
    "handle_version",
    "handle_config",
]
