#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import platform
import shlex
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
LOG_DIR = PROJECT_ROOT / "logs"
LOG_FILE = LOG_DIR / "launcher.log"


class LauncherError(RuntimeError):
    pass


def now_ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(level: str, message: str) -> None:
    line = f"[{now_ts()}] [{level}] {message}"
    print(line)
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        # Never block startup if file logging fails.
        pass


def detect_os() -> str:
    name = platform.system().lower()
    if "windows" in name:
        return "windows"
    if "darwin" in name or "mac" in name:
        return "macos"
    return "linux"


def run_command(cmd: list[str], *, use_shell: bool = False, cwd: Path | None = None) -> int:
    display = " ".join(shlex.quote(part) for part in cmd)
    log("INFO", f"Running command: {display}")
    try:
        completed = subprocess.run(cmd if not use_shell else " ".join(cmd), cwd=cwd or PROJECT_ROOT, check=False, shell=use_shell)
    except FileNotFoundError as exc:
        log("ERROR", f"Command not found: {cmd[0]} ({exc})")
        return 127
    except OSError as exc:
        log("ERROR", f"Failed to launch command ({exc})")
        return 1
    log("INFO", f"Command exited with code {completed.returncode}")
    return completed.returncode


def have_file(path: Path) -> bool:
    return path.exists() and path.is_file()


def resolve_powershell() -> str | None:
    for candidate in ("pwsh", "powershell"):
        code = run_command([candidate, "-NoProfile", "-Command", "$PSVersionTable.PSVersion > $null"], cwd=PROJECT_ROOT)
        if code == 0:
            return candidate
    return None


def ensure_install_if_needed(os_name: str) -> int:
    env_file = PROJECT_ROOT / ".env"
    venv_dir = PROJECT_ROOT / "venv"
    if env_file.exists() and venv_dir.exists():
        return 0

    log("WARN", "Missing .env or venv. Running install flow first.")
    return do_install(os_name)


def do_install(os_name: str) -> int:
    install_linux = PROJECT_ROOT / "scripts" / "install_linux.sh"
    install_macos = PROJECT_ROOT / "scripts" / "install_macos.sh"
    install_windows = PROJECT_ROOT / "scripts" / "install_windows.ps1"

    if os_name == "linux":
        if not have_file(install_linux):
            log("ERROR", "scripts/install_linux.sh not found.")
            return 1
        return run_command(["bash", str(install_linux)])

    if os_name == "macos":
        if have_file(install_macos):
            return run_command(["bash", str(install_macos)])
        if have_file(install_linux):
            log("WARN", "scripts/install_macos.sh not found. Falling back to scripts/install_linux.sh (best-effort).")
            return run_command(["bash", str(install_linux)])
        log("ERROR", "No installer available for macOS yet.")
        return 1

    if have_file(install_windows):
        ps = resolve_powershell()
        if not ps:
            log("ERROR", "PowerShell not found. Cannot run install_windows.ps1.")
            return 1
        return run_command([ps, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(install_windows)])

    log("ERROR", "install_windows.ps1 not found. Windows installer not available yet.")
    return 1


def do_start(extra_args: list[str], os_name: str) -> int:
    code = ensure_install_if_needed(os_name)
    if code != 0:
        return code

    run_linux = PROJECT_ROOT / "scripts" / "run_server_linux.sh"
    run_macos = PROJECT_ROOT / "scripts" / "run_server_macos.sh"
    run_windows = PROJECT_ROOT / "scripts" / "run_server.ps1"
    run_python = PROJECT_ROOT / "scripts" / "run_server.py"

    if os_name == "linux" and have_file(run_linux):
        return run_command(["bash", str(run_linux), *extra_args])

    if os_name == "macos" and have_file(run_macos):
        return run_command(["bash", str(run_macos), *extra_args])

    if os_name == "windows" and have_file(run_windows):
        ps = resolve_powershell()
        if not ps:
            log("ERROR", "PowerShell not found. Cannot run Windows server launcher.")
            return 1
        return run_command([ps, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(run_windows), *extra_args])

    if have_file(run_python):
        log("WARN", "OS-specific server launcher missing. Falling back to scripts/run_server.py.")
        return run_command([sys.executable, str(run_python), *extra_args])

    log("ERROR", "No server launcher available.")
    return 1


def do_download(os_name: str) -> int:
    media_cli = PROJECT_ROOT / "freetopify_media.py"
    if not have_file(media_cli):
        log("ERROR", "freetopify_media.py not found.")
        return 1
    return run_command([sys.executable, str(media_cli), "download"])


def do_organize(os_name: str) -> int:
    media_cli = PROJECT_ROOT / "freetopify_media.py"
    if not have_file(media_cli):
        log("ERROR", "freetopify_media.py not found.")
        return 1
    return run_command([sys.executable, str(media_cli), "organize"])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Unified Freetopify launcher (auto-detects OS and picks the right scripts)."
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("install", help="Run platform installer")

    start = sub.add_parser("start", help="Start server")
    start.add_argument("--dry-run", action="store_true", help="Forward --dry-run to scripts/run_server.py")
    start.add_argument(
        "--runner-arg",
        action="append",
        default=[],
        help="Additional raw argument forwarded to scripts/run_server.py (repeatable)",
    )

    sub.add_parser("download", help="Run CLI downloader helper")
    sub.add_parser("organize", help="Run music organizer helper")
    sub.add_parser("doctor", help="Print detected platform and launcher details")

    return parser.parse_args()


def doctor(os_name: str) -> int:
    log("INFO", f"Detected OS: {os_name}")
    log("INFO", f"Python executable: {sys.executable}")
    log("INFO", f"Project root: {PROJECT_ROOT}")
    log("INFO", f"Log file: {LOG_FILE}")
    return 0


def main() -> int:
    os.chdir(PROJECT_ROOT)
    os_name = detect_os()
    args = parse_args()

    command = args.command or "start"

    if command == "install":
        return do_install(os_name)
    if command == "start":
        runner_args: list[str] = []
        if getattr(args, "dry_run", False):
            runner_args.append("--dry-run")
        runner_args.extend(getattr(args, "runner_arg", []))
        return do_start(runner_args, os_name)
    if command == "download":
        return do_download(os_name)
    if command == "organize":
        return do_organize(os_name)
    if command == "doctor":
        return doctor(os_name)

    raise LauncherError(f"Unsupported command: {command}")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except LauncherError as exc:
        log("ERROR", str(exc))
        raise SystemExit(1)
