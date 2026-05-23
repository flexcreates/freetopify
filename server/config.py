from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    music_library_path: Path
    server_port: int
    server_host: str
    secret_key: str
    token_expire_hours: int
    admin_username: str
    admin_password: str
    database_path: Path
    ytdlp_path: str
    venv_path: Path
    default_download_format: str
    default_download_bitrate: str
    log_level: str
    log_file: Path
    mdns_hostname: str
    tailscale_ip: str


REQUIRED_KEYS = [
    "MUSIC_LIBRARY_PATH",
    "SERVER_PORT",
    "SERVER_HOST",
    "SECRET_KEY",
    "TOKEN_EXPIRE_HOURS",
    "ADMIN_USERNAME",
    "ADMIN_PASSWORD",
    "DATABASE_PATH",
    "YTDLP_PATH",
    "VENV_PATH",
    "DEFAULT_DOWNLOAD_FORMAT",
    "DEFAULT_DOWNLOAD_BITRATE",
    "LOG_LEVEL",
    "LOG_FILE",
    "MDNS_HOSTNAME",
]


def _required_env(key: str) -> str:
    value = os.getenv(key)
    if value is None or value == "":
        raise RuntimeError(f"Missing required env var: {key}")
    return value


def _optional_env(key: str, default: str = "") -> str:
    value = os.getenv(key)
    if value is None:
        return default
    return value


def load_settings() -> Settings:
    load_dotenv()
    missing = [key for key in REQUIRED_KEYS if os.getenv(key) is None]
    if missing:
        raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")

    return Settings(
        music_library_path=Path(_required_env("MUSIC_LIBRARY_PATH")).resolve(),
        server_port=int(_required_env("SERVER_PORT")),
        server_host=_required_env("SERVER_HOST"),
        secret_key=_required_env("SECRET_KEY"),
        token_expire_hours=int(_required_env("TOKEN_EXPIRE_HOURS")),
        admin_username=_required_env("ADMIN_USERNAME"),
        admin_password=_required_env("ADMIN_PASSWORD"),
        database_path=Path(_required_env("DATABASE_PATH")),
        ytdlp_path=_required_env("YTDLP_PATH"),
        venv_path=Path(_required_env("VENV_PATH")),
        default_download_format=_required_env("DEFAULT_DOWNLOAD_FORMAT"),
        default_download_bitrate=_required_env("DEFAULT_DOWNLOAD_BITRATE"),
        log_level=_required_env("LOG_LEVEL"),
        log_file=Path(_required_env("LOG_FILE")),
        mdns_hostname=_required_env("MDNS_HOSTNAME"),
        tailscale_ip=_optional_env("TAILSCALE_IP", ""),
    )
