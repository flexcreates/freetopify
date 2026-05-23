from __future__ import annotations

import os
from pathlib import Path

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
    from server.auth import _login_attempts

    _login_attempts.clear()


def _login(client: TestClient) -> str:
    res = client.post("/auth/login", json={"username": "admin", "password": "freetopify"})
    assert res.status_code == 200
    return res.json()["access_token"]


def _make_fake_mp3(path: Path) -> None:
    path.write_bytes(b"ID3" + b"\x00" * 2048)


def test_health(tmp_path):
    _env_setup(tmp_path)
    from server.main import app

    with TestClient(app) as client:
        res = client.get("/api/v1/system/health")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"


def test_protected_routes_require_auth(tmp_path):
    _env_setup(tmp_path)
    from server.main import app

    with TestClient(app) as client:
        assert client.get("/auth/me").status_code == 401
        assert client.get("/api/v1/library/browse").status_code in (401, 403)
        assert client.get("/api/v1/system/stats").status_code in (401, 403)


def test_login_and_browse_and_me(tmp_path):
    _env_setup(tmp_path)
    from server.main import app

    song = tmp_path / "music" / "a.mp3"
    _make_fake_mp3(song)

    with TestClient(app) as client:
        token = _login(client)
        auth = {"Authorization": f"Bearer {token}"}

        me = client.get("/auth/me", headers=auth)
        assert me.status_code == 200
        assert me.json()["username"] == "admin"

        res = client.get("/api/v1/library/browse", headers=auth)
        assert res.status_code == 200
        items = res.json().get("items", [])
        assert any(i.get("name") == "a.mp3" for i in items)


def test_stream_full_and_range(tmp_path):
    _env_setup(tmp_path)
    from server.main import app

    song = tmp_path / "music" / "b.mp3"
    song.write_bytes(b"ID3" + (b"x" * 4096))

    with TestClient(app) as client:
        token = _login(client)
        auth = {"Authorization": f"Bearer {token}"}

        full = client.get("/stream/b.mp3", headers=auth)
        assert full.status_code == 200
        assert full.headers.get("accept-ranges") == "bytes"

        part = client.get("/stream/b.mp3", headers={**auth, "Range": "bytes=0-99"})
        assert part.status_code == 206
        assert part.headers.get("accept-ranges") == "bytes"
        assert part.headers.get("content-range", "").startswith("bytes 0-99/")
        assert len(part.content) == 100


def test_path_traversal_blocked(tmp_path):
    _env_setup(tmp_path)
    from server.main import app

    with TestClient(app) as client:
        token = _login(client)
        res = client.get("/stream/%2E%2E/%2E%2E/etc/passwd", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 403


def test_websocket_requires_valid_token(tmp_path):
    _env_setup(tmp_path)
    from server.main import app

    with TestClient(app) as client:
        token = _login(client)
        with client.websocket_connect(f"/ws/live?token={token}") as ws:
            ws.send_text("ping")


def test_login_rate_limit(tmp_path):
    _env_setup(tmp_path)
    from server.main import app

    with TestClient(app) as client:
        for _ in range(10):
            r = client.post("/auth/login", json={"username": "admin", "password": "bad"})
            assert r.status_code == 401

        blocked = client.post("/auth/login", json={"username": "admin", "password": "bad"})
        assert blocked.status_code == 429
