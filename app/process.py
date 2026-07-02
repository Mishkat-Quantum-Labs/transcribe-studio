"""Single-instance lock via PID file — avoids orphaned servers holding the port."""

from __future__ import annotations

import atexit
import os
import signal
import socket
import subprocess
import sys
from pathlib import Path

from app.paths import data_dir

PID_FILENAME = "transcribe-studio.pid"


def pid_file_path() -> Path:
    return data_dir() / PID_FILENAME


def read_pid_file() -> dict[str, str] | None:
    path = pid_file_path()
    if not path.exists():
        return None
    try:
        lines = path.read_text(encoding="utf-8").strip().splitlines()
        if len(lines) < 3:
            return None
        return {"pid": lines[0], "host": lines[1], "port": lines[2]}
    except OSError:
        return None


def is_process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    else:
        return True


def clear_pid_file() -> None:
    try:
        pid_file_path().unlink(missing_ok=True)
    except OSError:
        pass


def write_pid_file(host: str, port: int) -> None:
    data_dir().mkdir(parents=True, exist_ok=True)
    pid_file_path().write_text(f"{os.getpid()}\n{host}\n{port}\n", encoding="utf-8")
    atexit.register(clear_pid_file)


def port_is_bound(host: str, port: int) -> bool:
    """Return True if something is already listening on host:port."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            return sock.connect_ex((host, port)) == 0
    except OSError:
        return False


def pids_listening_on_port(port: int) -> list[int]:
    """Best-effort list of PIDs bound to TCP port (Windows + Unix)."""
    pids: list[int] = []
    try:
        if sys.platform == "win32":
            out = subprocess.run(
                ["netstat", "-ano"],
                check=False,
                capture_output=True,
                text=True,
            ).stdout
            needle = f":{port}"
            for line in out.splitlines():
                if "LISTENING" not in line or needle not in line:
                    continue
                parts = line.split()
                if len(parts) < 5:
                    continue
                try:
                    pids.append(int(parts[-1]))
                except ValueError:
                    continue
        else:
            out = subprocess.run(
                ["lsof", "-ti", f"tcp:{port}"],
                check=False,
                capture_output=True,
                text=True,
            ).stdout
            for token in out.split():
                try:
                    pids.append(int(token))
                except ValueError:
                    continue
    except OSError:
        pass
    return sorted(set(pids))


def pids_for_uvicorn_port(port: int) -> list[int]:
    """Find uvicorn/python workers for app.main on a port (no PID file needed)."""
    pids: list[int] = []
    port_token = f"--port {port}"
    port_token_eq = f"--port={port}"
    try:
        if sys.platform == "win32":
            ps = (
                "Get-CimInstance Win32_Process "
                "-Filter \"Name='python.exe' OR Name='python3.13.exe' OR Name='uvicorn.exe'\" "
                "| Where-Object { "
                "$_.CommandLine -and "
                "($_.CommandLine -like '*uvicorn*' -or $_.CommandLine -like '*app.main*') "
                "} "
                f"| Where-Object {{ $_.CommandLine -like '*{port_token}*' "
                f"-or $_.CommandLine -like '*{port_token_eq}*' "
                f"-or $_.CommandLine -like '*:{port}*' }} "
                "| ForEach-Object { $_.ProcessId }"
            )
            out = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps],
                check=False,
                capture_output=True,
                text=True,
                timeout=15,
            ).stdout
            for token in out.split():
                try:
                    pids.append(int(token))
                except ValueError:
                    continue
        else:
            out = subprocess.run(
                ["pgrep", "-f", f"uvicorn.*{port}"],
                check=False,
                capture_output=True,
                text=True,
            ).stdout
            for token in out.split():
                try:
                    pids.append(int(token))
                except ValueError:
                    continue
    except (OSError, subprocess.TimeoutExpired):
        pass
    return sorted(set(pids))


def kill_port_listeners(port: int) -> list[int]:
    """Stop processes listening on port; returns PIDs we attempted to kill."""
    stopped: list[int] = []
    candidates = sorted(set(pids_listening_on_port(port) + pids_for_uvicorn_port(port)))
    for pid in candidates:
        if kill_process(pid):
            stopped.append(pid)
    return stopped


def kill_process(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        if sys.platform == "win32":
            result = subprocess.run(
                ["taskkill", "/PID", str(pid), "/F", "/T"],
                check=False,
                capture_output=True,
            )
            if result.returncode == 0:
                return True
            return is_process_alive(pid) is False
        if not is_process_alive(pid):
            return False
        os.kill(pid, signal.SIGTERM)
        return True
    except OSError:
        return False


def running_instance(port: int | None = None) -> dict[str, str | int] | None:
    """Return metadata for a live server, optionally filtered by port."""
    info = read_pid_file()
    if not info:
        return None
    pid = int(info["pid"])
    if not is_process_alive(pid):
        clear_pid_file()
        return None
    if port is not None and int(info["port"]) != port:
        return None
    return {"pid": pid, "host": info["host"], "port": int(info["port"])}


def ensure_can_start(host: str, port: int, *, force: bool = False) -> None:
    """Raise SystemExit if another instance is running or port is taken."""
    existing = running_instance()
    if existing:
        url = f"http://{existing['host']}:{existing['port']}"
        if force:
            print(f"Stopping existing instance (PID {existing['pid']})…")
            kill_process(int(existing["pid"]))
            clear_pid_file()
        else:
            print(
                f"Transcribe Studio is already running at {url} (PID {existing['pid']}).\n"
                f"  Stop it:  transcribe-studio stop\n"
                f"  Or force: transcribe-studio start --force\n"
                f"  Or use:   transcribe-studio start --port {port + 1}",
                file=sys.stderr,
            )
            raise SystemExit(1)

    if port_is_bound(host, port):
        if force:
            pids = kill_port_listeners(port)
            if pids:
                print(f"Freed port {port} (stopped PIDs: {', '.join(map(str, pids))})")
            clear_pid_file()
            if port_is_bound(host, port):
                ghost = pids_listening_on_port(port)
                ghost_msg = (
                    f" (netstat PIDs: {', '.join(map(str, ghost))}, not killable — reboot may be required)"
                    if ghost
                    else ""
                )
                print(
                    f"Port {port} is still in use on {host} after --force.{ghost_msg}\n"
                    f"  Close any terminal running uvicorn/transcribe-studio\n"
                    f"  Or reboot Windows, then run: python -m app --force\n"
                    f"  Or use another port: python -m app --port {port + 1}",
                    file=sys.stderr,
                )
                raise SystemExit(1)
        else:
            print(
                f"Port {port} is already in use on {host}.\n"
                f"  Try: transcribe-studio stop\n"
                f"  Or:  transcribe-studio start --force\n"
                f"  Or:  transcribe-studio start --port {port + 1}",
                file=sys.stderr,
            )
            raise SystemExit(1)


def cmd_stop(port: int | None = None) -> int:
    info = running_instance(port)
    if not info:
        clear_pid_file()
        target_port = port if port is not None else default_port_from_env()
        if port_is_bound("127.0.0.1", target_port):
            pids = kill_port_listeners(target_port)
            if pids:
                print(f"Stopped process(es) on port {target_port}: {', '.join(map(str, pids))}")
                return 0
            ghost = pids_listening_on_port(target_port)
            if ghost:
                print(
                    f"Port {target_port} is in use (PIDs: {', '.join(map(str, ghost))}) "
                    f"but could not be stopped. Reboot, or use: python -m app --port {target_port + 1}",
                    file=sys.stderr,
                )
                return 1
        print("No running Transcribe Studio instance found.")
        return 0
    pid = int(info["pid"])
    url = f"http://{info['host']}:{info['port']}"
    if kill_process(pid):
        print(f"Stopped Transcribe Studio at {url} (PID {pid}).")
    else:
        print(f"Could not stop PID {pid}. Try closing the terminal or Task Manager.", file=sys.stderr)
        return 1
    clear_pid_file()
    return 0


def default_port_from_env() -> int:
    try:
        return int(os.environ.get("TRANSCRIBE_STUDIO_PORT", "8082"))
    except ValueError:
        return 8082


def cmd_status() -> int:
    info = running_instance()
    if not info:
        print("Transcribe Studio is not running.")
        return 1
    url = f"http://{info['host']}:{info['port']}"
    print(f"Running at {url} (PID {info['pid']})")
    return 0