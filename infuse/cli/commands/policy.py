"""Governance policy commands for INFUSE CLI (Block 29)."""

import json
import os
import sys
from typing import Optional

from infuse.cli.exit_codes import EXIT_NOT_FOUND, EXIT_SUCCESS, EXIT_USAGE_ERROR
from infuse.cli.formatter import (
    format_error,
    format_policy,
    format_policy_list,
)
from infuse.contracts.policy import GovernancePolicy
from infuse.sdk.client import InfuseClient


def handle_policy_list(client: InfuseClient, json_mode: bool = False) -> int:
    """List all configured governance policies."""
    resp = client.policies.list()
    print(format_policy_list(resp, json_mode=json_mode))
    return EXIT_SUCCESS


def handle_policy_active(client: InfuseClient, json_mode: bool = False) -> int:
    """Get the currently active governance policy."""
    policy = client.policies.get_active()
    if not policy:
        print(
            format_error("No active governance policy found.", "NOT_FOUND", json_mode=json_mode),
            file=sys.stderr,
        )
        return EXIT_NOT_FOUND
    print(format_policy(policy, json_mode=json_mode))
    return EXIT_SUCCESS


def handle_policy_get(
    client: InfuseClient,
    policy_id: Optional[str] = None,
    json_mode: bool = False,
) -> int:
    """Get a governance policy by ID or active policy."""
    if not policy_id:
        return handle_policy_active(client=client, json_mode=json_mode)

    resp = client.policies.list()
    target = None
    for p in resp.policies:
        if p.policy_id == policy_id:
            target = p
            break
    if not target and resp.active_policy and resp.active_policy.policy_id == policy_id:
        target = resp.active_policy

    if not target:
        print(
            format_error(f"Policy '{policy_id}' not found.", "NOT_FOUND", json_mode=json_mode),
            file=sys.stderr,
        )
        return EXIT_NOT_FOUND

    print(format_policy(target, json_mode=json_mode))
    return EXIT_SUCCESS


def handle_policy_update(
    client: InfuseClient,
    policy_id: str,
    input_file: Optional[str] = None,
    json_data: Optional[str] = None,
    json_mode: bool = False,
) -> int:
    """Update or create a governance policy."""
    data = None
    if input_file:
        if not os.path.exists(input_file):
            print(
                format_error(f"Policy file not found: {input_file}", "FILE_NOT_FOUND", json_mode=json_mode),
                file=sys.stderr,
            )
            return EXIT_USAGE_ERROR
        try:
            with open(input_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            print(
                format_error(f"Failed to read policy file: {exc}", "INVALID_INPUT", json_mode=json_mode),
                file=sys.stderr,
            )
            return EXIT_USAGE_ERROR
    elif json_data:
        try:
            data = json.loads(json_data)
        except Exception as exc:
            print(
                format_error(f"Failed to parse json_data: {exc}", "INVALID_INPUT", json_mode=json_mode),
                file=sys.stderr,
            )
            return EXIT_USAGE_ERROR
    else:
        print(
            format_error("Must specify --file or --data to update policy.", "USAGE_ERROR", json_mode=json_mode),
            file=sys.stderr,
        )
        return EXIT_USAGE_ERROR

    if not isinstance(data, dict):
        print(
            format_error("Policy data must be a valid JSON object.", "INVALID_INPUT", json_mode=json_mode),
            file=sys.stderr,
        )
        return EXIT_USAGE_ERROR

    data["policy_id"] = policy_id
    updated = client.policies.update(policy_id, data)
    print(format_policy(updated, json_mode=json_mode))
    return EXIT_SUCCESS


__all__ = [
    "handle_policy_list",
    "handle_policy_active",
    "handle_policy_get",
    "handle_policy_update",
]
