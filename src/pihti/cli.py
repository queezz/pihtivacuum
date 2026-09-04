"""CLI for the PIHTI diagram server and its operator roster."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from pihti import roster


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pihti")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run the Flask server")
    # The diagram is served from one machine and read on a laptop or a phone,
    # so it answers on the LAN by default (owner decision 2026-09-04).
    run_parser.add_argument(
        "--host",
        default=os.environ.get("PIHTI_HOST", "0.0.0.0"),
        help="Host to bind (default every interface; 127.0.0.1 for this machine only)",
    )
    run_parser.add_argument(
        "--port", type=int, default=int(os.environ.get("PIHTI_PORT", "5000")), help="Port to bind"
    )
    run_parser.add_argument("--debug", action="store_true", help="Enable loopback-only debug mode")

    operators = subparsers.add_parser(
        "operators", help="Manage the operator roster (names only, attribution only)"
    )
    operator_commands = operators.add_subparsers(dest="operator_command", required=True)
    operator_commands.add_parser("list", help="Print the roster names")
    add = operator_commands.add_parser("add", help="Add one or more names")
    add.add_argument("names", nargs="+")
    remove = operator_commands.add_parser("remove", help="Remove a name")
    remove.add_argument("name")
    operator_commands.add_parser(
        "import-history", help="Add every operator who appears in the diagram history log"
    )
    operator_commands.add_parser(
        "import-legacy",
        help="Add the account names from the encrypted legacy registry (needs its key)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        if args.debug and args.host not in {"127.0.0.1", "localhost", "::1"}:
            parser.error("--debug may only be used with a loopback host")
        _run_server(args.host, args.port, args.debug)
        return 0
    if args.command == "operators":
        return _operators(args)
    return 2


def _operators(args) -> int:
    root = roster.data_root()
    path = roster.roster_path(root)
    try:
        names = roster.read_roster(path) or []
        if args.operator_command == "list":
            for name in names:
                print(name)
            if not names:
                print("(no operators in the roster)", file=sys.stderr)
            return 0
        if args.operator_command == "add":
            names = roster.write_roster(path, [*names, *args.names])
        elif args.operator_command == "remove":
            before = len(names)
            names = roster.write_roster(
                path, [name for name in names if name.casefold() != args.name.casefold()]
            )
            if len(names) == before:
                print("name not in the roster", file=sys.stderr)
                return 1
        elif args.operator_command == "import-history":
            names = roster.write_roster(path, [*names, *roster.history_names(root / "logs.csv")])
        elif args.operator_command == "import-legacy":
            users_file = roster.env_path("PIHTI_USERS_FILE", root / "users.json.enc")
            key_file = roster.env_path(
                "PIHTI_USERS_KEY_FILE", roster.default_private_dir() / "users.key"
            )
            names = roster.write_roster(path, [*names, *roster.legacy_names(users_file, key_file)])
        print(f"roster now holds {len(names)} operator name(s)")
        return 0
    except FileNotFoundError as exc:
        print(f"pihti: {Path(exc.filename).name if exc.filename else exc} not found", file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(f"pihti: {exc}", file=sys.stderr)
        return 2


def _run_server(host: str, port: int, debug: bool = False):
    """Start Flask app normally."""
    from pihti.server import app
    app.run(host=host, port=port, debug=debug)
