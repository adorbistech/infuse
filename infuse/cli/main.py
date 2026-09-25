"""INFUSE CLI Main Entrypoint (Block 29).

Provides the main parser, command routing, error normalization,
and deterministic exit code management.
"""

import argparse
import sys
from typing import List, Optional

from infuse.cli.commands.control import (
    handle_control_cancel,
    handle_control_switch,
    handle_control_terminate,
    handle_control_throttle,
)
from infuse.cli.commands.events import (
    handle_events_list,
    handle_events_publish,
)
from infuse.cli.commands.execution import (
    handle_execute,
    handle_executions_get,
    handle_executions_list,
    handle_executions_result,
    handle_executions_state,
)
from infuse.cli.commands.governor import handle_governor
from infuse.cli.commands.info import handle_config, handle_version
from infuse.cli.commands.policy import (
    handle_policy_active,
    handle_policy_get,
    handle_policy_list,
    handle_policy_update,
)
from infuse.cli.exit_codes import (
    EXIT_SUCCESS,
    EXIT_USAGE_ERROR,
    map_error_to_exit_code,
)
from infuse.cli.formatter import format_error
from infuse.sdk.client import InfuseClient
from infuse.sdk.config import ClientConfig
from infuse.version import __version__


def create_parser() -> argparse.ArgumentParser:
    """Create the comprehensive top-level argument parser for the INFUSE CLI."""
    # Parent parser for subparsers with suppressed defaults to avoid overwriting top-level flags
    sub_common_parser = argparse.ArgumentParser(add_help=False)
    sub_common_parser.add_argument(
        "--json",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Format output as machine-readable JSON",
    )
    sub_common_parser.add_argument(
        "-o",
        "--output",
        choices=["text", "json"],
        default=argparse.SUPPRESS,
        help="Output format (text or json)",
    )
    sub_common_parser.add_argument(
        "--endpoint",
        "--base-url",
        dest="base_url",
        type=str,
        default=argparse.SUPPRESS,
        help="Target INFUSE API base URL (overrides INFUSE_BASE_URL)",
    )
    sub_common_parser.add_argument(
        "--api-key",
        type=str,
        default=argparse.SUPPRESS,
        help="INFUSE authorization key / token (overrides INFUSE_API_KEY)",
    )
    sub_common_parser.add_argument(
        "--timeout",
        type=float,
        default=argparse.SUPPRESS,
        help="Request timeout in seconds (overrides INFUSE_TIMEOUT_SECONDS)",
    )

    parser = argparse.ArgumentParser(
        prog="infuse",
        description="INFUSE — Execution Intelligence & Governance CLI (Block 29)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Format output as machine-readable JSON",
    )
    parser.add_argument(
        "-o",
        "--output",
        choices=["text", "json"],
        default="text",
        help="Output format (text or json)",
    )
    parser.add_argument(
        "--endpoint",
        "--base-url",
        dest="base_url",
        type=str,
        default=None,
        help="Target INFUSE API base URL (overrides INFUSE_BASE_URL)",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="INFUSE authorization key / token (overrides INFUSE_API_KEY)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="Request timeout in seconds (overrides INFUSE_TIMEOUT_SECONDS)",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        default=False,
        help="Print INFUSE CLI version and exit",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ── version ────────────────────────────────────────────────────────
    subparsers.add_parser(
        "version",
        help="Display INFUSE version and schema information",
        parents=[sub_common_parser],
    )

    # ── config / info ──────────────────────────────────────────────────
    subparsers.add_parser(
        "config",
        help="Display current active INFUSE CLI/SDK configuration",
        parents=[sub_common_parser],
    )
    subparsers.add_parser(
        "info",
        help="Display active configuration (alias for config)",
        parents=[sub_common_parser],
    )

    # ── execute ────────────────────────────────────────────────────────
    exec_parser = subparsers.add_parser(
        "execute",
        help="Submit an execution request through the SDK",
        parents=[sub_common_parser],
    )
    exec_parser.add_argument(
        "--task",
        "-t",
        type=str,
        help="Task description / goal",
    )
    exec_parser.add_argument(
        "--prompt",
        "-p",
        type=str,
        help="Execution prompt or user message",
    )
    exec_parser.add_argument(
        "--provider",
        type=str,
        help="Explicit provider name (e.g. mock, openai, anthropic)",
    )
    exec_parser.add_argument(
        "--model",
        "-m",
        type=str,
        help="Target model identifier",
    )
    exec_parser.add_argument(
        "--agent",
        "-a",
        type=str,
        default="CLI-Agent",
        help="Agent identifier initiating the execution",
    )
    exec_parser.add_argument(
        "--file",
        "-f",
        dest="input_file",
        type=str,
        help="Path to JSON file containing full ExecutionRequest schema",
    )

    # ── execution ──────────────────────────────────────────────────────
    execution_cmd = subparsers.add_parser(
        "execution",
        help="Inspect individual execution telemetry, state, or results",
        parents=[sub_common_parser],
    )
    execution_sub = execution_cmd.add_subparsers(
        dest="execution_action",
        help="Execution subcommands",
    )

    # execution get
    exec_get = execution_sub.add_parser("get", help="Retrieve execution summary by ID", parents=[sub_common_parser])
    exec_get.add_argument("execution_id", type=str, help="Execution identifier")

    # execution state
    exec_state = execution_sub.add_parser("state", help="Inspect execution state by ID", parents=[sub_common_parser])
    exec_state.add_argument("execution_id", type=str, help="Execution identifier")

    # execution result
    exec_res = execution_sub.add_parser("result", help="Inspect execution result by ID", parents=[sub_common_parser])
    exec_res.add_argument("execution_id", type=str, help="Execution identifier")

    # ── executions ─────────────────────────────────────────────────────
    executions_cmd = subparsers.add_parser(
        "executions",
        help="List and search execution history",
        parents=[sub_common_parser],
    )
    executions_sub = executions_cmd.add_subparsers(
        dest="executions_action",
        help="Executions subcommands",
    )

    # executions list
    exec_list = executions_sub.add_parser("list", help="List executions", parents=[sub_common_parser])
    exec_list.add_argument("--query", "-q", type=str, help="Search query filter")
    exec_list.add_argument("--state", "-s", type=str, help="Filter by execution state (e.g. NORMAL, RUNAWAY)")
    exec_list.add_argument("--agent", "-a", type=str, help="Filter by agent identifier")
    exec_list.add_argument("--limit", "-l", type=int, default=50, help="Maximum number of executions to return")
    exec_list.add_argument("--offset", type=int, default=0, help="Pagination offset")

    # executions get shortcut
    execs_get = executions_sub.add_parser("get", help="Retrieve execution by ID", parents=[sub_common_parser])
    execs_get.add_argument("execution_id", type=str, help="Execution identifier")

    # executions state shortcut
    execs_state = executions_sub.add_parser("state", help="Inspect execution state by ID", parents=[sub_common_parser])
    execs_state.add_argument("execution_id", type=str, help="Execution identifier")

    # executions top-level optional flags for direct list invocation (infuse executions --limit 10)
    executions_cmd.add_argument("--query", "-q", type=str, help="Search query filter")
    executions_cmd.add_argument("--state", "-s", type=str, help="Filter by execution state")
    executions_cmd.add_argument("--agent", "-a", type=str, help="Filter by agent identifier")
    executions_cmd.add_argument("--limit", "-l", type=int, default=50, help="Maximum number of items")
    executions_cmd.add_argument("--offset", type=int, default=0, help="Pagination offset")

    # ── state ──────────────────────────────────────────────────────────
    state_cmd = subparsers.add_parser(
        "state",
        help="Inspect execution state directly",
        parents=[sub_common_parser],
    )
    state_cmd.add_argument("execution_id", type=str, help="Execution identifier")

    # ── governor ───────────────────────────────────────────────────────
    gov_cmd = subparsers.add_parser(
        "governor",
        help="Inspect Governor decision and regulation posture",
        parents=[sub_common_parser],
    )
    gov_cmd.add_argument("execution_id", type=str, help="Execution identifier")

    # ── events ─────────────────────────────────────────────────────────
    events_cmd = subparsers.add_parser(
        "events",
        help="Publish or inspect execution telemetry events",
        parents=[sub_common_parser],
    )
    events_sub = events_cmd.add_subparsers(
        dest="events_action",
        help="Events subcommands",
    )

    # events publish / emit
    for emit_alias in ("publish", "emit"):
        ev_pub = events_sub.add_parser(
            emit_alias,
            help="Publish a telemetry event",
            parents=[sub_common_parser],
        )
        ev_pub.add_argument("execution_id", type=str, help="Target execution ID")
        ev_pub.add_argument("--type", "--event-type", dest="event_type", type=str, help="Event type enum")
        ev_pub.add_argument("--source", type=str, default="AGENT", help="Event source")
        ev_pub.add_argument("--payload", "-p", type=str, help="JSON or text payload string")
        ev_pub.add_argument("--file", "-f", dest="input_file", type=str, help="Path to JSON event payload")
        ev_pub.add_argument("--sequence", type=int, default=1, help="Event sequence number")

    # events list
    ev_list = events_sub.add_parser("list", help="List timeline events for execution", parents=[sub_common_parser])
    ev_list.add_argument("execution_id", type=str, help="Execution identifier")

    # ── policy ─────────────────────────────────────────────────────────
    pol_cmd = subparsers.add_parser(
        "policy",
        help="Inspect and manage Governance Policies",
        parents=[sub_common_parser],
    )
    pol_sub = pol_cmd.add_subparsers(
        dest="policy_action",
        help="Policy subcommands",
    )

    # policy list
    pol_sub.add_parser("list", help="List all policies", parents=[sub_common_parser])

    # policy active
    pol_sub.add_parser("active", help="Get currently active policy", parents=[sub_common_parser])

    # policy get
    pol_get = pol_sub.add_parser("get", help="Get policy by ID or active", parents=[sub_common_parser])
    pol_get.add_argument("policy_id", type=str, nargs="?", default=None, help="Policy ID (optional)")

    # policy update / set
    for update_alias in ("update", "set"):
        pol_upd = pol_sub.add_parser(
            update_alias,
            help="Update or create a policy revision",
            parents=[sub_common_parser],
        )
        pol_upd.add_argument("policy_id", type=str, help="Policy ID")
        pol_upd.add_argument("--file", "-f", dest="input_file", type=str, help="Path to JSON policy file")
        pol_upd.add_argument("--data", "-d", dest="json_data", type=str, help="JSON policy data string")

    # ── control ────────────────────────────────────────────────────────
    ctrl_cmd = subparsers.add_parser(
        "control",
        help="Dispatch operational control commands through the Control Boundary",
        parents=[sub_common_parser],
    )
    ctrl_sub = ctrl_cmd.add_subparsers(
        dest="control_action",
        help="Control actions",
    )

    # control cancel
    ctrl_cancel = ctrl_sub.add_parser("cancel", help="Cancel active execution gracefully", parents=[sub_common_parser])
    ctrl_cancel.add_argument("execution_id", type=str, help="Target execution ID")
    ctrl_cancel.add_argument("--reason", type=str, help="Reason for cancellation")
    ctrl_cancel.add_argument("--yes", "-y", action="store_true", default=False, help="Automatic confirmation")

    # control terminate
    ctrl_term = ctrl_sub.add_parser("terminate", help="Terminate active execution immediately", parents=[sub_common_parser])
    ctrl_term.add_argument("execution_id", type=str, help="Target execution ID")
    ctrl_term.add_argument("--reason", type=str, help="Reason for termination")
    ctrl_term.add_argument("--yes", "-y", action="store_true", default=False, help="Automatic confirmation")

    # control throttle
    ctrl_throttle = ctrl_sub.add_parser("throttle", help="Throttle execution speed/frequency", parents=[sub_common_parser])
    ctrl_throttle.add_argument("execution_id", type=str, help="Target execution ID")
    ctrl_throttle.add_argument("--delay-ms", type=int, default=1000, help="Delay in milliseconds")
    ctrl_throttle.add_argument("--reason", type=str, help="Reason for throttle")
    ctrl_throttle.add_argument("--yes", "-y", action="store_true", default=False, help="Automatic confirmation")

    # control switch
    ctrl_switch = ctrl_sub.add_parser("switch", help="Switch model / provider for execution", parents=[sub_common_parser])
    ctrl_switch.add_argument("execution_id", type=str, help="Target execution ID")
    ctrl_switch.add_argument("--target-model", type=str, required=True, help="Target model identifier")
    ctrl_switch.add_argument("--target-provider", type=str, help="Target provider identifier")
    ctrl_switch.add_argument("--reason", type=str, help="Reason for switch")
    ctrl_switch.add_argument("--yes", "-y", action="store_true", default=False, help="Automatic confirmation")

    return parser


def run_cli(
    args: Optional[List[str]] = None,
    client: Optional[InfuseClient] = None,
) -> int:
    """Execute the CLI with given argument list and optional injected SDK client."""
    parser = create_parser()

    if args is None:
        args = sys.argv[1:]

    # Handle bare --version before parsing subcommands
    if "--version" in args and len(args) == 1:
        return handle_version(json_mode=False)

    try:
        parsed_args = parser.parse_args(args)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else EXIT_USAGE_ERROR

    json_mode = getattr(parsed_args, "json", False) or (getattr(parsed_args, "output", "text") == "json")

    if getattr(parsed_args, "version", False):
        return handle_version(json_mode=json_mode)

    if not parsed_args.command:
        parser.print_help()
        return EXIT_USAGE_ERROR

    # Initialize SDK client if not injected
    if client is None:
        cfg = ClientConfig.from_env()
        if getattr(parsed_args, "base_url", None):
            cfg.base_url = parsed_args.base_url
        if getattr(parsed_args, "api_key", None):
            cfg.api_key = parsed_args.api_key
        if getattr(parsed_args, "timeout", None):
            cfg.timeout_seconds = parsed_args.timeout
        client = InfuseClient(config=cfg)

    try:
        cmd = parsed_args.command
        if cmd == "version":
            return handle_version(json_mode=json_mode)

        elif cmd in ("config", "info"):
            return handle_config(client=client, json_mode=json_mode)

        elif cmd == "execute":
            return handle_execute(
                client=client,
                task=getattr(parsed_args, "task", None),
                prompt=getattr(parsed_args, "prompt", None),
                provider=getattr(parsed_args, "provider", None),
                model=getattr(parsed_args, "model", None),
                agent=getattr(parsed_args, "agent", "CLI-Agent"),
                input_file=getattr(parsed_args, "input_file", None),
                json_mode=json_mode,
            )

        elif cmd == "execution":
            action = getattr(parsed_args, "execution_action", None)
            if not action:
                print(
                    format_error("Must specify execution subcommand (get, state, result).", "USAGE_ERROR", json_mode=json_mode),
                    file=sys.stderr,
                )
                return EXIT_USAGE_ERROR

            if action == "get":
                return handle_executions_get(
                    client=client,
                    execution_id=parsed_args.execution_id,
                    json_mode=json_mode,
                )
            elif action == "state":
                return handle_executions_state(
                    client=client,
                    execution_id=parsed_args.execution_id,
                    json_mode=json_mode,
                )
            elif action == "result":
                return handle_executions_result(
                    client=client,
                    execution_id=parsed_args.execution_id,
                    json_mode=json_mode,
                )

        elif cmd == "executions":
            action = getattr(parsed_args, "executions_action", None)
            if action == "get":
                return handle_executions_get(
                    client=client,
                    execution_id=parsed_args.execution_id,
                    json_mode=json_mode,
                )
            elif action == "state":
                return handle_executions_state(
                    client=client,
                    execution_id=parsed_args.execution_id,
                    json_mode=json_mode,
                )
            else:
                # Default to listing executions
                query = getattr(parsed_args, "query", None)
                state = getattr(parsed_args, "state", None)
                agent = getattr(parsed_args, "agent", None)
                limit = getattr(parsed_args, "limit", 50)
                offset = getattr(parsed_args, "offset", 0)
                return handle_executions_list(
                    client=client,
                    query=query,
                    state=state,
                    agent=agent,
                    limit=limit,
                    offset=offset,
                    json_mode=json_mode,
                )

        elif cmd == "state":
            return handle_executions_state(
                client=client,
                execution_id=parsed_args.execution_id,
                json_mode=json_mode,
            )

        elif cmd == "policy":
            pol_action = getattr(parsed_args, "policy_action", None)
            if pol_action == "active":
                return handle_policy_active(client=client, json_mode=json_mode)
            elif pol_action == "get":
                return handle_policy_get(
                    client=client,
                    policy_id=getattr(parsed_args, "policy_id", None),
                    json_mode=json_mode,
                )
            elif pol_action in ("update", "set"):
                return handle_policy_update(
                    client=client,
                    policy_id=parsed_args.policy_id,
                    input_file=getattr(parsed_args, "input_file", None),
                    json_data=getattr(parsed_args, "json_data", None),
                    json_mode=json_mode,
                )
            else:
                return handle_policy_list(client=client, json_mode=json_mode)

        elif cmd == "events":
            ev_action = getattr(parsed_args, "events_action", None)
            if ev_action in ("publish", "emit"):
                return handle_events_publish(
                    client=client,
                    execution_id=parsed_args.execution_id,
                    event_type=getattr(parsed_args, "event_type", None),
                    source=getattr(parsed_args, "source", None),
                    payload_str=getattr(parsed_args, "payload", None),
                    input_file=getattr(parsed_args, "input_file", None),
                    sequence=getattr(parsed_args, "sequence", 1),
                    json_mode=json_mode,
                )
            elif ev_action == "list":
                return handle_events_list(
                    client=client,
                    execution_id=parsed_args.execution_id,
                    json_mode=json_mode,
                )
            else:
                print(
                    format_error("Must specify events subcommand (publish, emit, list).", "USAGE_ERROR", json_mode=json_mode),
                    file=sys.stderr,
                )
                return EXIT_USAGE_ERROR

        elif cmd == "governor":
            return handle_governor(
                client=client,
                execution_id=parsed_args.execution_id,
                json_mode=json_mode,
            )

        elif cmd == "control":
            ctrl_action = getattr(parsed_args, "control_action", None)
            if ctrl_action == "cancel":
                return handle_control_cancel(
                    client=client,
                    execution_id=parsed_args.execution_id,
                    reason=getattr(parsed_args, "reason", None),
                    json_mode=json_mode,
                )
            elif ctrl_action == "terminate":
                return handle_control_terminate(
                    client=client,
                    execution_id=parsed_args.execution_id,
                    reason=getattr(parsed_args, "reason", None),
                    json_mode=json_mode,
                )
            elif ctrl_action == "throttle":
                return handle_control_throttle(
                    client=client,
                    execution_id=parsed_args.execution_id,
                    delay_ms=getattr(parsed_args, "delay_ms", 1000),
                    reason=getattr(parsed_args, "reason", None),
                    json_mode=json_mode,
                )
            elif ctrl_action == "switch":
                return handle_control_switch(
                    client=client,
                    execution_id=parsed_args.execution_id,
                    target_model=parsed_args.target_model,
                    target_provider=getattr(parsed_args, "target_provider", None),
                    reason=getattr(parsed_args, "reason", None),
                    json_mode=json_mode,
                )
            else:
                print(
                    format_error("Must specify a control action (cancel, terminate, throttle, switch).", "USAGE_ERROR", json_mode=json_mode),
                    file=sys.stderr,
                )
                return EXIT_USAGE_ERROR

        else:
            print(format_error(f"Unknown command '{cmd}'.", "USAGE_ERROR", json_mode=json_mode), file=sys.stderr)
            return EXIT_USAGE_ERROR

    except Exception as exc:
        exit_code = map_error_to_exit_code(exc)
        err_msg = str(exc)
        code_str = exc.__class__.__name__
        details = getattr(exc, "details", None)
        print(
            format_error(err_msg, error_code=code_str, details=details, json_mode=json_mode),
            file=sys.stderr,
        )
        return exit_code


def main() -> None:
    """CLI entry point executed by the 'infuse' console script."""
    sys.exit(run_cli())


if __name__ == "__main__":
    main()
