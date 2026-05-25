#!/usr/bin/env python3
from __future__ import annotations

import argparse
import platform
import shlex
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
LOG_DIR = PROJECT_ROOT / "logs"
LOG_FILE = LOG_DIR / "media-cli.log"


def log(level: str, message: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {message}"
    print(line)
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass


def detect_os() -> str:
    name = platform.system().lower()
    if "windows" in name:
        return "windows"
    if "darwin" in name or "mac" in name:
        return "macos"
    return "linux"


def run(cmd: list[str]) -> int:
    display = " ".join(shlex.quote(x) for x in cmd)
    log("INFO", f"Running: {display}")
    try:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, check=False)
    except FileNotFoundError as exc:
        log("ERROR", f"Command not found: {cmd[0]} ({exc})")
        return 127
    except OSError as exc:
        log("ERROR", f"Launch failed: {exc}")
        return 1
    log("INFO", f"Exit code: {result.returncode}")
    return result.returncode


def resolve_powershell() -> str | None:
    for candidate in ("pwsh", "powershell"):
        if subprocess.run([candidate, "-NoProfile", "-Command", "$PSVersionTable.PSVersion > $null"], cwd=PROJECT_ROOT, check=False).returncode == 0:
            return candidate
    return None


def command_for(task: str, os_name: str) -> list[str] | None:
    if task == "download":
        if os_name == "windows":
            ps = resolve_powershell()
            return [ps, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(PROJECT_ROOT / "scripts" / "ftsmdl.ps1")] if ps else None
        return ["bash", str(PROJECT_ROOT / "scripts" / "ftsmdl.sh")]

    if task == "organize":
        if os_name == "windows":
            ps = resolve_powershell()
            return [ps, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(PROJECT_ROOT / "scripts" / "organize_music_library.ps1")] if ps else None
        return ["bash", str(PROJECT_ROOT / "scripts" / "organize_music_library.sh")]

    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Freetopify media CLI orchestrator")
    parser.add_argument("command", choices=["download", "organize", "doctor"])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    os_name = detect_os()

    if args.command == "doctor":
        log("INFO", f"Detected OS: {os_name}")
        log("INFO", f"Project root: {PROJECT_ROOT}")
        return 0

    cmd = command_for(args.command, os_name)
    if not cmd:
        log("ERROR", f"No command resolver available for command={args.command} os={os_name}")
        return 1
    return run(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
