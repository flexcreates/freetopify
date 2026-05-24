# Server Build Doc (Caveman)

## Big Goal
Server first. Server give API, stream, auth, scan, watch, download, live push.

## Must Have
- Python `>=3.11`
- `pip`
- `sqlite3`
- `yt-dlp`
- `ffmpeg` (good for downloader art/embed)
- Linux machine

## Root Files We Make/Update
- `.env` (local only, secret)
- `.env.example` (safe template)
- `.gitignore`
- `requirements.txt`
- `install.sh`
- `freetopify.service`
- `TASK.md`
- `README.md`

## Root Folder Tree (Need)
```txt
freetopify/
├── .env
├── .env.example
├── .gitignore
├── README.md
├── TASK.md
├── requirements.txt
├── install.sh
├── freetopify.service
├── server/
├── web/
├── android/
├── scripts/
├── data/
└── logs/
```

## Server Folder Tree (Need)
```txt
server/
├── __init__.py
├── main.py
├── config.py
├── database.py
├── models.py
├── auth.py
├── router_library.py
├── router_stream.py
├── router_downloader.py
├── router_system.py
├── watcher.py
├── scanner.py
├── websocket_manager.py
├── downloader.py
└── tests/
    └── test_api.py
```

## Requirements.txt (Put)
```txt
fastapi
uvicorn[standard]
aiosqlite
python-dotenv
PyJWT
bcrypt
mutagen
watchdog
zeroconf
python-multipart
yt-dlp
psutil
pytest
httpx
```

## .gitignore (Put)
```gitignore
.env
venv/
__pycache__/
*.pyc
data/
logs/
android/build/
android/.dart_tool/
android/.gradle/
```

## .env.example (Put)
Use PRD values. Keep placeholders only. Never real secret.

Must keys:
- `MUSIC_LIBRARY_PATH`
- `SERVER_PORT`
- `SERVER_HOST`
- `SECRET_KEY`
- `TOKEN_EXPIRE_HOURS`
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`
- `DATABASE_PATH`
- `YTDLP_PATH`
- `VENV_PATH`
- `DEFAULT_DOWNLOAD_FORMAT`
- `DEFAULT_DOWNLOAD_BITRATE`
- `LOG_LEVEL`
- `LOG_FILE`
- `MDNS_HOSTNAME`
- `TAILSCALE_IP`

Optional guest config:
- `GUEST_PIN`
- `GUEST_TOKEN_EXPIRE_HOURS`
- `SECURE_COOKIES`

## .env (Local)
Copy from `.env.example`. Change `SECRET_KEY` now.

## Build Order (Do Exact)
1. `server/config.py`
2. `server/database.py`
3. `server/models.py`
4. `server/auth.py`
5. `server/scanner.py`
6. `server/watcher.py`
7. `server/websocket_manager.py`
8. `server/router_library.py`
9. `server/router_stream.py`
10. `server/downloader.py`
11. `server/router_downloader.py`
12. `server/router_system.py`
13. `server/mdns.py`
14. `server/main.py`

After each file:
```bash
python3 -c "import server.<module_name>"
```

## Rules While Coding
- All endpoints auth required except `/api/v1/system/health`
- Guest access can be enabled with `GUEST_PIN`; keep guest scope read-only on the web client
- Protect path traversal with safe path check
- Stream endpoint support Range (`206`, `Accept-Ranges`, `Content-Range`)
- Watcher debounce **2500ms** (raised from 500ms to survive yt-dlp part-file storms)
- Watcher ignores temp suffixes: `.part .ytdl .tmp .webp .jpg .png .webm .m4a`
- `on_fs_event` is guarded by `asyncio.Lock` — concurrent scans on the same SQLite DB are skipped
- WebSocket event `library_update` only fires after a real audio file changes
- SSE for download progress
- DB schema match PRD exactly
- `Cache-Control: no-cache` set on all `/web/*.js|html|css` responses via ASGI middleware

## Download System
- `POST /api/v1/download/start` — start a download job; accepts optional `output_dir`
- `GET /api/v1/download/progress/{job_id}` — SSE stream of yt-dlp log lines
- `GET /api/v1/download/jobs` — list of recent jobs (polled only while active jobs exist)
- `DELETE /api/v1/download/jobs/{job_id}` — cancel running job
- `GET /api/v1/download/history` — read permanent local history log (newest-first, max 200)
- Download history written to `logs/download_history.log` (JSONL, git-ignored)
  - Only final audio files logged (extension matches job format); deduped by stem
  - Format: `{"ts": "YYYY-MM-DD HH:MM:SS", "title": "...", "folder": "...", "format": "mp3", "url": "..."}`

## Library API
- `GET /api/v1/library/browse?path=` — folder tree; items include `absolute_path`
- `POST /api/v1/library/mkdir` — create a new sub-folder (path-traversal safe)
- `GET /api/v1/library/cover?path=` — folder cover art (first embedded thumbnail found)

## Quick Verify
```bash
./scripts/run_server.sh
curl http://127.0.0.1:7171/api/v1/system/health
```

## Start / Restart
- Use `./scripts/run_server.sh` to stop any existing Freetopify `uvicorn` process for port `7171` and start a fresh one.
- Systemd service `freetopify.service` uses the same launcher.

## Test List (Must Pass)
- health 200
- login gives JWT
- browse works
- stream full file 200
- stream range 206
- websocket connects
- create file -> library_update in <=2s
- download job creates
- SSE opens
- `/stream/../../etc/passwd` => 403

## Git Flow
- Commit small, one logical chunk
- Good commit name:
  - `server: add config and env validation`
  - `server: implement auth and jwt`
  - `server: add stream range endpoint`

## Team Talk Rule
- Keep messages short
- Say: what file changed, why changed, how tested
- If blocked, say exact command + exact error
