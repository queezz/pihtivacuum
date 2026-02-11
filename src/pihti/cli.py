"""CLI for pihti Flask server."""

import argparse
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(prog="pihti")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run the Flask server")
    run_parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    run_parser.add_argument("--port", type=int, default=5000, help="Port to bind")
    run_parser.add_argument("--nohup", action="store_true", help="Run with nohup (Linux)")

    args = parser.parse_args()

    if args.command == "run":
        if args.nohup:
            _run_nohup(args.host, args.port)
        else:
            _run_server(args.host, args.port)


def _run_server(host: str, port: int):
    """Start Flask app normally."""
    from pihti.server import app
    app.run(host=host, port=port, debug=True)


def _run_nohup(host: str, port: int):
    """Spawn Flask server via real Linux nohup. Does not recursively use --nohup."""
    cmd = [
        "nohup",
        sys.executable, "-m", "pihti", "run",
        "--host", host,
        "--port", str(port),
    ]
    with open("pihti.log", "a") as logf:
        subprocess.Popen(
            cmd,
            stdout=logf,
            stderr=subprocess.STDOUT,
        )
    print("Pihti started with nohup. Log file: pihti.log")
