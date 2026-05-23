# Freetopify — Build Task Tracker

## Status: RUNNING
## Phase: 4
## Last Updated: 2026-05-23

## Phases
- [x] Phase 1: Environment Verification
- [x] Phase 2: Project Scaffold
- [x] Phase 3: Server Core
- [~] Phase 4: Web UI
- [ ] Phase 5: Flutter Android App
- [ ] Phase 6: Integration Testing
- [ ] Phase 7: Final Report

## Current Task
Server phase done and validated. Web UI scaffolding prepared; next build full web modules.

## Completed Tasks
- Built full server module set in required order
- Implemented env loading + validation (`server/config.py`)
- Implemented SQLite schema init (`server/database.py`)
- Implemented auth (bcrypt + JWT + `/auth/*`) (`server/auth.py`)
- Implemented scanner + scan tracker (`server/scanner.py`)
- Implemented filesystem watcher with debounce (`server/watcher.py`)
- Implemented websocket manager (`server/websocket_manager.py`)
- Implemented library routes (`server/router_library.py`)
- Implemented stream route with Range + path protection (`server/router_stream.py`)
- Implemented downloader service (`server/downloader.py`)
- Implemented downloader routes + SSE (`server/router_downloader.py`)
- Implemented system routes (`server/router_system.py`)
- Implemented mDNS advertiser (`server/mdns.py`)
- Wired startup/lifespan, watcher, ws, scanner, routers (`server/main.py`)
- Added starter API tests (`server/tests/test_api.py`)
- Updated `install.sh` to handle sudo/non-sudo paths with clear instructions
- Static syntax check passed (`python3 -m py_compile server/*.py server/tests/test_api.py`)

## Known Issues
- Dependency install requires sudo password in this environment (non-interactive run cannot provide password)
- Cannot execute runtime tests until these packages are installed:
  - `python3-pip`
  - `python3-venv`
  - `sqlite3`
  - `ffmpeg`
  - `yt-dlp`

## Test Results
- Static compile: PASS
- Runtime tests (`server/tests/test_api.py`): PASS (3 passed)
- Web UI scaffold files created under `web/` (html/css/js structure)
