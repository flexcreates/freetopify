#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shlex
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterable


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cross-platform Freetopify server runner")
    parser.add_argument("--dry-run", action="store_true", help="Print resolved command and exit")
    return parser.parse_args()


def load_dotenv_file(env_path: Path) -> None:
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def env_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default))
    try:
        return int(raw)
    except ValueError:
        return default


def command_matches_freetopify_server(command_line: str, host: str, port: int) -> bool:
    cmd = command_line.lower()
    if "uvicorn" not in cmd or "server.main:app" not in cmd:
        return False

    port_match = f"--port {port}" in cmd or f"--port={port}" in cmd
    host_match = f"--host {host.lower()}" in cmd or f"--host={host.lower()}" in cmd
    return port_match and host_match


def list_processes() -> Iterable[tuple[int, str]]:
    if os.name == "nt":
        ps_cmd = [
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-CimInstance Win32_Process | ForEach-Object {"
            "$_.ProcessId.ToString() + \"`t\" + ($_.CommandLine -replace \"`r|`n\", \" \") }",
        ]
        proc = subprocess.run(ps_cmd, capture_output=True, text=True, check=False)
        for line in proc.stdout.splitlines():
            if "\t" not in line:
                continue
            pid_raw, cmdline = line.split("\t", 1)
            pid_raw = pid_raw.strip()
            if pid_raw.isdigit():
                yield int(pid_raw), cmdline.strip()
        return

    proc = subprocess.run(
        ["ps", "-ax", "-o", "pid=,command="],
        capture_output=True,
        text=True,
        check=False,
    )
    for line in proc.stdout.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        parts = stripped.split(maxsplit=1)
        if not parts:
            continue
        pid_raw = parts[0]
        cmdline = parts[1] if len(parts) > 1 else ""
        if pid_raw.isdigit():
            yield int(pid_raw), cmdline


def is_pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        check = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}"],
            capture_output=True,
            text=True,
            check=False,
        )
        return str(pid) in check.stdout
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def terminate_pid(pid: int) -> None:
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/T"], capture_output=True, text=True, check=False)
        return
    os.kill(pid, signal.SIGTERM)


def force_kill_pid(pid: int) -> None:
    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/PID", str(pid), "/T"], capture_output=True, text=True, check=False)
        return
    os.kill(pid, signal.SIGKILL)


def stop_existing_server(host: str, port: int) -> None:
    current_pid = os.getpid()
    candidates = [
        pid
        for pid, cmd in list_processes()
        if pid != current_pid and command_matches_freetopify_server(cmd, host, port)
    ]
    if not candidates:
        return

    print("Stopping existing Freetopify server process(es)...")
    for pid in candidates:
        try:
            terminate_pid(pid)
        except OSError:
            continue

    deadline = time.time() + 6.0
    while time.time() < deadline and any(is_pid_alive(pid) for pid in candidates):
        time.sleep(0.2)

    stubborn = [pid for pid in candidates if is_pid_alive(pid)]
    if stubborn:
        print("Force-stopping stubborn server process(es)...")
        for pid in stubborn:
            try:
                force_kill_pid(pid)
            except OSError:
                continue


def resolve_uvicorn_base(venv_path: Path, project_root: Path) -> list[str]:
    venv_expanded = venv_path.expanduser()
    venv_resolved = (project_root / venv_expanded).resolve() if not venv_expanded.is_absolute() else venv_expanded.resolve()

    candidates = []
    if os.name == "nt":
        candidates.extend(
            [
                venv_resolved / "Scripts" / "uvicorn.exe",
                venv_resolved / "Scripts" / "uvicorn",
            ]
        )
    else:
        candidates.append(venv_resolved / "bin" / "uvicorn")

    for candidate in candidates:
        if candidate.exists():
            return [str(candidate)]

    if os.name == "nt":
        venv_python = venv_resolved / "Scripts" / "python.exe"
    else:
        venv_python = venv_resolved / "bin" / "python"
    if venv_python.exists():
        return [str(venv_python), "-m", "uvicorn"]

    return [sys.executable, "-m", "uvicorn"]


def main() -> int:
    args = parse_args()
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    os.chdir(project_root)
    load_dotenv_file(project_root / ".env")

    host = os.getenv("SERVER_HOST", "0.0.0.0")
    port = env_int("SERVER_PORT", 7171)
    venv_path = Path(os.getenv("VENV_PATH", "./venv"))
    max_connections = env_int("MAX_CONNECTIONS", 0)

    uvicorn_base = resolve_uvicorn_base(venv_path, project_root)
    command = uvicorn_base + ["server.main:app", "--host", host, "--port", str(port)]
    if max_connections > 0:
        command += ["--limit-concurrency", str(max_connections)]

    if args.dry_run:
        print("Dry run: would execute")
        print(shlex.join(command))
        return 0

    stop_existing_server(host=host, port=port)
    os.execvp(command[0], command)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
