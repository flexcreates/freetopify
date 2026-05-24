from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from server.auth import ensure_default_admin, router as auth_router
from server.config import load_settings
from server.database import init_db
from server.downloader import Downloader
from server.mdns import MDNSAdvertiser
from server.router_downloader import router as downloader_router
from server.router_library import router as library_router
from server.router_stream import router as stream_router
from server.router_system import router as system_router
from server.scanner import ScanTracker, scan_library
from server.watcher import LibraryWatcher
from server.websocket_manager import WebSocketManager


def _setup_logging(log_file: Path, level: str) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler(log_file)],
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings()
    app.state.settings = settings

    Path("data").mkdir(parents=True, exist_ok=True)
    Path("logs").mkdir(parents=True, exist_ok=True)
    try:
        settings.music_library_path.mkdir(parents=True, exist_ok=True)
    except PermissionError as exc:
        raise RuntimeError(
            f"Cannot create or access MUSIC_LIBRARY_PATH={settings.music_library_path}. "
            "Set a writable path in .env (example: /home/<user>/Music/freetopify)."
        ) from exc

    _setup_logging(settings.log_file, settings.log_level)
    logging.info("Starting Freetopify server")

    await init_db(str(settings.database_path))
    await ensure_default_admin(str(settings.database_path), settings.admin_username, settings.admin_password)

    app.state.ws_manager = WebSocketManager()
    app.state.scan_tracker = ScanTracker()
    app.state.scanner = scan_library

    await scan_library(settings.music_library_path, str(settings.database_path), app.state.scan_tracker)

    app.state.downloader = Downloader(settings.ytdlp_path, settings.music_library_path)

    _scan_lock = asyncio.Lock()

    async def on_fs_event(event) -> None:
        # Guard: skip if a scan is already running (don't stack scans)
        if _scan_lock.locked():
            logging.debug("Scan already in progress, skipping event: %s", getattr(event, "src_path", "?"))
            return
        async with _scan_lock:
            logging.info("Filesystem event: %s", getattr(event, "src_path", "unknown"))
            await scan_library(settings.music_library_path, str(settings.database_path), app.state.scan_tracker)
            await app.state.ws_manager.broadcast(
                {
                    "event": "library_update",
                    "data": {"path": getattr(event, "src_path", ""), "action": getattr(event, "event_type", "changed")},
                }
            )

    loop = asyncio.get_running_loop()
    app.state.watcher = LibraryWatcher(settings.music_library_path, loop, on_fs_event)
    app.state.watcher.start()

    app.state.mdns = None
    if settings.enable_mdns and not os.getenv("PYTEST_CURRENT_TEST"):
        app.state.mdns = MDNSAdvertiser(settings.mdns_hostname, settings.server_port)
        try:
            await app.state.mdns.start()
        except Exception:
            logging.exception("mDNS startup failed")

    yield

    try:
        app.state.watcher.stop()
    except Exception:
        logging.exception("Watcher shutdown failed")

    if app.state.mdns is not None:
        try:
            await app.state.mdns.stop()
        except Exception:
            logging.exception("mDNS shutdown failed")


app = FastAPI(title="Freetopify Server", version="1.0.0", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(system_router)
app.include_router(library_router)
app.include_router(stream_router)
app.include_router(downloader_router)
app.mount("/web", StaticFiles(directory="web"), name="web")


@app.middleware("http")
async def no_cache_web_assets(request: Request, call_next):
    """Force browsers to always revalidate /web/ static files.

    Without this, Firefox aggressively caches ES modules and serves stale
    instances even after version strings change, causing the player state
    singleton to split into two disconnected instances (one plays audio,
    one the UI listens to — controls and Now Playing view stop updating).

    Setting Cache-Control: no-cache tells the browser to always send a
    conditional request (If-None-Match / ETag). If the file hasn't changed,
    the server returns 304 Not Modified — fast and bandwidth-efficient.
    If the file changed, it returns the new content.
    """
    response = await call_next(request)
    path = request.url.path
    if path.startswith("/web/") and (
        path.endswith(".js")
        or path.endswith(".html")
        or path.endswith(".css")
    ):
        response.headers["Cache-Control"] = "no-cache"
    return response


@app.get("/")
async def root_redirect():
    return RedirectResponse(url="/web/index.html")


@app.websocket("/ws/live")
async def ws_live(websocket: WebSocket):
    token = websocket.query_params.get("token", "") or websocket.cookies.get("freetopify_token", "")
    settings = websocket.app.state.settings
    from server.auth import decode_access_token

    try:
        decode_access_token(settings.secret_key, token)
    except Exception:
        await websocket.close(code=4401)
        return

    manager = websocket.app.state.ws_manager
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
