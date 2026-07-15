"""Command-line entry point for transcribe-studio."""

from __future__ import annotations

import app._bootstrap  # noqa: F401 — Windows console fix (must be first)

import argparse
import os
import sys

from dotenv import load_dotenv

# Load .env before anything else reads environment variables
load_dotenv()

HELP_EPILOG = """
examples:
  transcribe                           Start on 127.0.0.1:8082 (foreground)
  transcribe -p 8083                   Start on port 8083
  transcribe-studio                    Same as transcribe
  ts                                   Short alias
  transcribe-studio -p 8083            Start on port 8083
  transcribe-studio --host 0.0.0.0     Listen on all interfaces
  transcribe-studio stop               Stop a stuck instance, free the port
  transcribe-studio status             Check if the server is running
  transcribe-studio start --force      Replace existing instance

  python -m app -h                     Same commands if not on PATH (Windows)

defaults (flags → env → built-in):
  --host   TRANSCRIBE_STUDIO_HOST   127.0.0.1
  --port   TRANSCRIBE_STUDIO_PORT   8082

The server runs in the foreground and holds the terminal until you press
Ctrl+C or run `transcribe-studio stop` from another terminal. It does not
daemonize or run in the background.
""".strip()


def default_host() -> str:
    return os.environ.get("TRANSCRIBE_STUDIO_HOST", "127.0.0.1")


def default_port() -> int:
    return int(os.environ.get("TRANSCRIBE_STUDIO_PORT", "8082"))


def build_parser() -> argparse.ArgumentParser:
    host_def = default_host()
    port_def = default_port()

    parser = argparse.ArgumentParser(
        prog="transcribe-studio",
        description=(
            "Transcribe Studio — local classroom audio transcription. "
            "Runs in the foreground (not background)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=HELP_EPILOG,
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="start",
        choices=("start", "stop", "status"),
        metavar="command",
        help="start (default): run web UI in foreground | stop: free port | status: show PID",
    )
    parser.add_argument(
        "--host",
        default=host_def,
        metavar="ADDR",
        help=f"Bind address for start (default: {host_def}, env TRANSCRIBE_STUDIO_HOST)",
    )
    parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=port_def,
        metavar="PORT",
        help=f"TCP port for start, or filter for stop (default: {port_def}, env TRANSCRIBE_STUDIO_PORT)",
    )
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="start only: stop any existing instance before starting",
    )
    return parser


def cmd_start(host: str, port: int, *, force: bool = False) -> None:
    if not (1 <= port <= 65535):
        print("Error: --port must be between 1 and 65535", file=sys.stderr)
        raise SystemExit(2)

    from app.process import ensure_can_start, write_pid_file
    from app.main import serve

    ensure_can_start(host, port, force=force)
    write_pid_file(host, port)

    url = f"http://{host}:{port}"
    print(f"Transcribe Studio — foreground mode")
    print(f"Open: {url}")
    print("Stop: Ctrl+C in this terminal, or run `transcribe stop` in another")
    serve(host=host, port=port)


def _port_flag_passed(argv: list[str]) -> bool:
    return any(
        a in ("--port", "-p") or a.startswith("--port=") for a in argv
    )


def main(argv: list[str] | None = None) -> None:
    raw = sys.argv[1:] if argv is None else argv
    args = build_parser().parse_args(raw)

    if args.command == "stop":
        from app.process import cmd_stop

        port_filter = args.port if _port_flag_passed(raw) else None
        raise SystemExit(cmd_stop(port_filter))

    if args.command == "status":
        from app.process import cmd_status

        raise SystemExit(cmd_status())

    cmd_start(args.host, args.port, force=args.force)


if __name__ == "__main__":
    main()