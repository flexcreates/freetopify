# Changelog
This file records notable changes made to the Freetopify project as work progresses.

---

## 2026-05-25 — Downloader Overhaul, Player Stability, Resource Optimisation & YouTube Fix

### YouTube Downloader — Full Fix (`server/downloader.py`)
- **Fixed YouTube JS signature solving** — the root cause of all download failures
  - Added `--remote-components ejs:github`: downloads yt-dlp's official EJS challenge solver (cached after first use)
  - Added `--js-runtimes node:<path>`: uses system Node.js for signature + n-challenge solving
  - Added `quickjs` Python package as fallback when Node.js is not available
  - Priority: `node` binary → `quickjs` → graceful degradation
- **Fixed HTTP 429 rate-limit errors**
  - Added `--cookies-from-browser <browser>`: passes logged-in YouTube session cookies
  - Added `--retries 10 --retry-sleep 5`: auto-retry on 429 instead of failing immediately
  - Added `--sleep-interval 2 --max-sleep-interval 5`: spaces out playlist track requests
- **Fixed duplicate download history entries**
  - yt-dlp emits two `Destination:` lines per track (raw `.webm` + extracted `.mp3`)
  - Now filters by job's target format extension only; deduplicates by stem as safety net
- **Fixed live history refresh** — `loadHistory()` now called automatically when a job completes (no page refresh needed)
- **Fixed live folder track count refresh** — `loadFolders()` called on job completion so counts update instantly
- Fixed `YTDLP_PATH` to point to `./venv/bin/yt-dlp` (venv binary, always correct version)

### Smart Folder-Picker Downloads (`web/js/downloader.js`)
- **Visual folder grid**: replaced text input with glassmorphism folder cards showing name + track count
- **Multi-select**: click multiple folders to download the same track to all simultaneously
- **New Folder modal**: create sub-directories on the fly without leaving the UI
- **Per-job SSE log cards**: collapsible real-time yt-dlp output per job, individual status badges
- **Adaptive polling**: jobs endpoint polled only while active jobs exist; self-cancels when all done
- **Download history section**: permanent local log shown below recent jobs (persists across restarts)
- **Scrollable panel**: fixed panel height clamp that cut off history list

### Permanent Download History (`server/router_downloader.py`, `server/downloader.py`)
- Download history written to `logs/download_history.log` (JSONL, git-ignored, never deleted)
- Entry format: `{"ts": "YYYY-MM-DD HH:MM:SS", "title": "...", "folder": "...", "format": "mp3", "url": "..."}`
- `GET /api/v1/download/history` — serves newest-first, max 200 entries
- `POST /api/v1/library/mkdir` — creates new sub-folder (path-traversal safe)

### Player State Synchronisation Fix (`web/js/*.js`, `server/main.py`)
- **Root cause**: ES module singletons split when imports used inconsistent URLs (`?v=` strings)
- **Fix 1**: Added `Cache-Control: no-cache` ASGI middleware for all `/web/*.js|html|css` responses
  - Forces every browser to revalidate static files on load (ETag-based, bandwidth-efficient)
  - Eliminates Firefox aggressive module cache issue permanently
- **Fix 2**: Removed all `?v=` version strings from JS-to-JS imports (bare imports = same URL = same singleton)
  - Reverts to the pre-regression state that worked in all browsers
  - No manual version string management ever needed again

### Resource Optimisations (`server/watcher.py`, `server/main.py`, `web/js/downloader.js`)
- **Watcher debounce**: raised 0.5s → 2.5s — prevents per-chunk scan during yt-dlp downloads
- **Watcher temp-file filter**: ignores `.part .ytdl .tmp .webp .jpg .png .webm .m4a` events entirely
  - A single track download previously triggered 11+ full library scans; now triggers 1
- **Scan concurrency lock**: `asyncio.Lock` prevents two overlapping `scan_library()` calls on same SQLite DB
- **Adaptive job poll**: replaced always-on `setInterval(refreshJobs, 3000)` with self-cancelling poll
  - Polling starts on download, stops when all jobs reach `done`/`failed`

### Install Script Overhaul (`install.sh`)
- Added `nodejs` to apt package list — fixes yt-dlp JS runtime requirement automatically
- Auto-detects installed browser (Firefox/Chrome/Chromium) → writes `YTDLP_BROWSER` to `.env`
- Sets `YTDLP_PATH=./venv/bin/yt-dlp` (venv binary, always the correct pip-managed version)
- Generated `.env` now includes all variables with section comments matching `.env.example`
- Auto-generates `SECRET_KEY` using `secrets.token_hex(32)` (cryptographically strong)
- Prompts for admin username + password (defaults to `admin`/`freetopify` if skipped)
- Existing `.env` preserved on re-run — only `MUSIC_LIBRARY_PATH`, `YTDLP_PATH`, `YTDLP_BROWSER` updated

### Configuration (`server/config.py`, `.env`, `.env.example`)
- Added `YTDLP_BROWSER` optional setting (empty = no cookie passthrough)
- Reorganised `.env.example` into 8 labelled sections with inline comments
- Added missing variables: `GUEST_PIN`, `GUEST_TOKEN_EXPIRE_HOURS`, `SECURE_COOKIES`, `MAX_CONNECTIONS`, `PARTY_BUFFER_MS`

### Dependencies (`requirements.txt`)
- Added `quickjs` — Python JS runtime, fallback for yt-dlp when Node.js unavailable
- Existing: `fastapi`, `uvicorn[standard]`, `aiosqlite`, `mutagen`, `yt-dlp`, `PyJWT`, `bcrypt`, `watchdog`, `zeroconf`, `psutil`, `pytest`, `httpx`

### Documentation (`docs/server.md`, `docs/web.md`, `README.md`)
- Updated watcher debounce value (500ms → 2500ms), documented temp-file ignore list
- Documented `Cache-Control: no-cache` middleware, scan lock, download history log format
- Added all new API endpoints to both docs
- Updated web.md: cache-busting rule removed, bare imports rule added, test checklist updated
- Root README: full rewrite with downloader section, updated config table, stack table, quick start

---

## 2026-05-24 — Gen Z UI/UX Redesign (Complete Frontend Overhaul)

A full visual redesign of the Freetopify web client. All JS logic, player features,
library navigation, auth, downloads, and API calls are **100% preserved** — this is a
pure CSS/HTML frontend overhaul.

### Design System — `web/css/variables.css`
- Replaced 5 old flat color variables with **57 design tokens**
- Neon palette: violet `#7c3aed` · pink `#ec4899` · cyan `#06b6d4` · amber `#f59e0b`
- Added spring animation easing curves and duration tokens (`--ease-spring`, `--dur-fast`, `--dur-med`)
- Glassmorphism surface levels: `--surface-0`, `--surface-1`, `--surface-2`
- Neon glow shadow tokens: `--glow-violet`, `--glow-pink`, `--glow-cyan`
- Font family tokens for Space Grotesk (headings) and Inter (body)

### Typography — `web/css/reset.css`
- Added Google Fonts `@import` for **Space Grotesk** (700 weight headings) and **Inter** (body)

### App Styles — `web/css/app.css` (full rewrite, 1485 lines)

Layout fixes:
- `app-shell` grid: `220px minmax(0,1fr) 260px` — correct column widths, no overflow
- `now-bar` grid: responsive `minmax()` 3-column — never breaks or clips at any viewport
- `player-stage` grid: `clamp(200px,32%,300px) 1fr` — vinyl never overflows
- `folder-grid`: `minmax(200px,1fr)` — folder cards fill correctly
- `track-row-btn` grid: `36px 1fr auto auto` — track title never clips
- `.view` is now a flex column with `padding:0`; `.view > .panel` takes `flex:1` and carries the padding — panels fill the full content area with zero dead space
- `player-hero` uses `flex:1` (removed fixed `min-height:420px`) — vinyl card fills entire view
- Sidebar: `flex-direction:column` + `align-self:start` — nav links compact at top, no spreading

Visual & effects:
- Animated 3-orb mesh gradient background (18s drift cycle)
- All panels: glassmorphism `backdrop-filter: blur(20px)` + subtle shimmer gradient border
- Sidebar: SVG icon + label nav links with neon active glow and slide-in indicator
- Now-bar: violet→pink play button with glow, custom range sliders with neon thumb
- Vinyl disk: `clamp()` sizing, concentric groove lines, ambient neon pulse animation, spinning state
- Folder cards: glass surface, cover art or emoji fallback, hover lift + glow
- Track rows: album art column, hover highlight, icon actions
- Buttons: `primary-btn` = violet→pink gradient pill; `secondary-btn` = violet outline pill
- Range inputs: custom thumb with neon glow, smooth height transition on hover
- Section kicker labels in violet, gradient `h2` headings

About page improvements:
- Emoji icons (🏠 🔐 📱) for feature cards
- "Connect" social links section with GitHub + Instagram pills
- `@flexcreates` handle, "Day zero 🚀" project start flavour
- Donate card with ☕ CTA and proper placeholder copy
- Live elapsed timer with yr · mo · d · hr · min · sec format

Context menu (`web/js/library.js`):
- Glassmorphism dark bg `rgba(8,6,22,0.92)` + violet border
- Spring `menuPop` keyframe animation (scale + translateY)
- Viewport-clamped position — menu never clips off screen

### Main App — `web/index.html`
- Added Google Fonts `preconnect` + `link` tags
- Added SVG icons to all 5 sidebar nav links (library, music note, download, gear, info)
- Cache-bust version bumped to `v=20260524-8`

### Login Page — `web/login.html`
- Dual-layer animated mesh gradient background (12s cycle)
- Glassmorphism card with shimmer border + spring entrance animation (`cardEntrance`)
- Neon animated logo with drop-shadow pulse (`logoPulse`)
- Role switcher tabs with violet glow on active state and spring hover lift
- Polished form inputs with focus ring
- Password visibility toggle (eye icon)
- Proper `panelFade` animation when switching between Admin/Guest panels

### JS — `web/js/app.js`
- Queue items use CSS `.queue-item` + `.playing` classes (removed all inline styles)
- Active queue track shows `▶` prefix indicator
- Player view: uses proper CSS class structure for vinyl, ambient, meta
- Settings view: inline `Check Connection` + `Logout` buttons (not full-width stretch)
- About view: complete HTML rewrite with emoji feature cards, improved stats grid, donate card

### Responsive Breakpoints — `web/css/app.css`
Full 5-tier responsive system replacing the old 2-tier system:

| Breakpoint | Layout |
|---|---|
| `≤1240px` | Queue panel hidden; sidebar narrows to 210px |
| `≤1024px` | Sidebar narrows; now-bar shrinks; player stacks |
| `≤900px` | Sidebar becomes horizontal tab bar at top; all columns collapse |
| `≤600px` | Mobile: icons hidden (text only); touch targets ≥44px; player bar stacks |
| `≤375px` | Brand hidden; 2-col folder grid; tightest spacing |

---

2026-05-24 — Update dependencies

- Added `pydantic` (used by `server/models.py`) and `requests` (used by `fastapi.testclient`) to `requirements.txt` so the test environment and runtime have all required packages.

---

2026-05-24 — Redesign login screen flow

- UI: changed `web/login.html` from two always-visible forms to a role-first flow with two clear options: Admin login or Guest access.
- UX: added step labels and helper text so users know exactly what to enter for each field.
- JS: updated `web/js/auth.js` to submit the correct credential path based on the selected role.


2026-05-24 — Initial snapshot / project state

- Project: Freetopify — self-hosted, folder-first music server (see README).
- Core server implemented using FastAPI: `server/main.py` (lifespan startup, DB init, scan, watcher, mDNS, WebSocket endpoint `/ws/live`).
- Routers included: authentication, system, library, stream, downloader (mounted in `server/main.py`).
- Downloader: `server/downloader.py` — async download job manager using `yt-dlp`/`yt-dlp` path configurable.
- Data models: `server/models.py` — Pydantic request/response models and `DownloadJob` dataclass.
- Scanning & watching: `server/scanner.py`, `server/watcher.py` (library scanning and filesystem watcher trigger broadcasts).
- mDNS: `server/mdns.py` for local network advertising (enabled via settings).
- Database: SQLite via `aiosqlite`, initialization in `server/database.py` and default admin ensured by `server/auth.py`.
- Web UI: static site served from `web/` (index.html, login.html, CSS and JS assets under `web/css` and `web/js`).
- Tests: basic API tests present at `server/tests/test_api.py`.
- Scripts & utilities: `install.sh`, `freetopify.service`, `scripts/` (helper scripts like `fix_music_tree.sh`, `nvmsdl.sh`).
- Data: `data/` folder with `meta_backups/` containing backup files.
- Docs: `docs/` contains `prd.md`, `server.md`, `web.md`, `android.md` (planning and spec docs).
- Requirements: `requirements.txt` lists runtime dependencies (FastAPI, uvicorn, aiosqlite, yt-dlp, mutagen, watchdog, zeroconf, PyJWT, bcrypt, etc.).

Notes and conventions

- Update this file for every logical change (feature, bugfix, refactor) with a one-line summary, date, and affected files.
- Format for future entries:
  - YYYY-MM-DD — Short summary
    - Files: path/to/file.py
    - Notes: optional longer detail

---

2026-05-24 — Add PIN-gated guest access (initial implementation)

- Feature: Admin-configured guest PIN via `.env` key `GUEST_PIN` enables temporary guest access.
- Files added/changed:
  - `server/config.py`: added `guest_pin` setting loaded from env `GUEST_PIN`.
  - `server/models.py`: added `GuestRequest` model.
  - `server/auth.py`: added `/auth/guest` endpoint to exchange name+PIN for a guest JWT (tokens include `role: guest` claim). Also blocked guest tokens from protected HTTP endpoints.
  - `web/login.html`: added a guest join form (name + PIN).
  - `web/js/auth.js`: added `guestJoin()` and client-side guest form binding.

- Notes: Guest tokens are issued with subject `guest:<name>` and claim `role=guest`. HTTP endpoints that require authentication will reject guest tokens; guest tokens are accepted for websocket connections and other flows that use raw token decoding (e.g., `/ws/live`).

---

2026-05-24 — Add auth audit logging and guest rate-limiting

- Security: Added audit logs for authentication events and applied rate-limiting to guest join attempts.
- Files changed:
  - `server/auth.py`: integrated `logging.getLogger('server.auth')`, logged failed/successful login attempts and guest join attempts, applied `_check_login_rate_limit` to `/auth/guest`.
- Notes: Auth events now appear in the main server log configured by `server/main.py`. Logs intentionally avoid sensitive data (passwords/tokens printed raw). Rate-limit matches existing login limits (10 attempts / 60s per IP).

---

2026-05-24 — Add guest token TTL and secure cookie option; generate SECRET_KEY

- Config: added `GUEST_TOKEN_EXPIRE_HOURS` (default 1 hour) and `SECURE_COOKIES` (default false) environment variables; `server/config.py` now loads these values.
- Auth: guest tokens now use `GUEST_TOKEN_EXPIRE_HOURS` when issuing tokens; cookie `Secure` flag is set when `SECURE_COOKIES=true`.
- Env: `.env` updated with a generated `SECRET_KEY` and the new variables.

---

2026-05-24 — Simplify login copy and finalize docs

- UI: reduced login screen copy to keep the page minimal and avoid exposing internal config details.
- Docs: updated `README.md`, `docs/server.md`, `docs/web.md`, and `docs/prd.md` to reflect guest PIN settings, guest token lifetime, secure cookie option, and the role-first login flow.
- Web: added a small cache-busting version to the login and app module imports so browsers load the updated auth/websocket modules.
- Server: websocket live connections now fall back to the auth cookie when a query token is not provided, which keeps guest/admin live updates working in normal browsers.

---

2026-05-24 — Add restart-safe server launcher

- Startup: added `scripts/run_server.sh` to stop any existing Freetopify `uvicorn` process on port `7171` before starting a fresh one.
- Packaging: updated `README.md`, `install.sh`, `docs/server.md`, and `freetopify.service` to use the launcher.

---

2026-05-24 — Add About / Developer credits page

- UI: added an About route in the web app with developer credits, official GitHub/Instagram links, project start date, and a live elapsed timer.
- UI: included a donation / buy-a-coffee placeholder card matching the existing theme.
- Docs: updated `README.md` and `docs/web.md` to mention the About page.
