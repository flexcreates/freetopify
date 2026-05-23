from __future__ import annotations

import os

from fastapi.testclient import TestClient


def _env_setup(tmp_path):
    music = tmp_path / "music"
    data = tmp_path / "data"
    logs = tmp_path / "logs"
    music.mkdir(parents=True, exist_ok=True)
    data.mkdir(parents=True, exist_ok=True)
    logs.mkdir(parents=True, exist_ok=True)

    os.environ["MUSIC_LIBRARY_PATH"] = str(music)
    os.environ["SERVER_PORT"] = "7171"
    os.environ["SERVER_HOST"] = "0.0.0.0"
    os.environ["SECRET_KEY"] = "test-secret-key-32-bytes-minimum-len"
    os.environ["TOKEN_EXPIRE_HOURS"] = "12"
    os.environ["ADMIN_USERNAME"] = "admin"
    os.environ["ADMIN_PASSWORD"] = "freetopify"
    os.environ["DATABASE_PATH"] = str(data / "freetopify.db")
    os.environ["YTDLP_PATH"] = "yt-dlp"
    os.environ["VENV_PATH"] = "./venv"
    os.environ["DEFAULT_DOWNLOAD_FORMAT"] = "mp3"
    os.environ["DEFAULT_DOWNLOAD_BITRATE"] = "320k"
    os.environ["LOG_LEVEL"] = "INFO"
    os.environ["LOG_FILE"] = str(logs / "freetopify.log")
    os.environ["MDNS_HOSTNAME"] = "freetopify"
    os.environ["TAILSCALE_IP"] = ""


def _login(client: TestClient) -> str:
    res = client.post("/auth/login", json={"username": "admin", "password": "freetopify"})
    assert res.status_code == 200
    return res.json()["access_token"]


def test_health(tmp_path):
    _env_setup(tmp_path)
    from server.main import app

    with TestClient(app) as client:
        res = client.get("/api/v1/system/health")
        assert res.status_code == 200


def test_login_and_browse(tmp_path):
    _env_setup(tmp_path)
    from server.main import app

    song = tmp_path / "music" / "a.mp3"
    song.write_bytes(b"ID3dummy")

    with TestClient(app) as client:
        token = _login(client)
        res = client.get("/api/v1/library/browse", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        assert isinstance(res.json().get("items"), list)


def test_path_traversal_blocked(tmp_path):
    _env_setup(tmp_path)
    from server.main import app

    with TestClient(app) as client:
        token = _login(client)
        res = client.get("/stream/%2E%2E/%2E%2E/etc/passwd", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 403
