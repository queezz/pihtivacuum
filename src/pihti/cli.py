"""CLI for pihti Flask server."""

import argparse
import os


def main():
    parser = argparse.ArgumentParser(prog="pihti")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run the Flask server")
    run_parser.add_argument(
        "--host", default=os.environ.get("PIHTI_HOST", "127.0.0.1"), help="Host to bind"
    )
    run_parser.add_argument("--port", type=int, default=5000, help="Port to bind")
    run_parser.add_argument("--debug", action="store_true", help="Enable loopback-only debug mode")

    args = parser.parse_args()

    if args.command == "run":
        if args.debug and args.host not in {"127.0.0.1", "localhost", "::1"}:
            parser.error("--debug may only be used with a loopback host")
        _run_server(args.host, args.port, args.debug)


def _run_server(host: str, port: int, debug: bool = False):
    """Start Flask app normally."""
    from pihti.server import app
    app.run(host=host, port=port, debug=debug)
