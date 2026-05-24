# Changelog
This file records notable changes made to the Freetopify project as work progresses.
The entries below represent an initial snapshot of the repository state and history up to 2026-05-24.

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

Example entry (future):

- 2026-05-25 — Add track metadata caching
  - Files: `server/scanner.py`, `server/database.py`
  - Notes: Adds in-memory cache to avoid repeated metadata extraction during scans.

---

End of initial snapshot.

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

