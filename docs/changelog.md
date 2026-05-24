# Changelog
This file records notable changes made to the Freetopify project as work progresses.

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
