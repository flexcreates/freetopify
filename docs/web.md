# Web Build Doc

## Big Goal
Web is a light client. No Node. No npm. No framework. Pure static HTML/CSS/JS.

## Must Have
- Modern browser (Chrome 90+, Firefox 88+, Safari 14+)
- Server running on `:7171`
- ES Module support

## Design System (Gen Z Edition)
The web UI uses a neon glassmorphism design language:

| Token | Value |
|---|---|
| Primary | Violet `#7c3aed` |
| Accent 1 | Pink `#ec4899` |
| Accent 2 | Cyan `#06b6d4` |
| Background | Deep space `#06060f` |
| Surface 0 | `rgba(10,8,24,0.75)` with `backdrop-filter:blur(20px)` |
| Fonts | Space Grotesk (headings) · Inter (body) via Google Fonts |

**Effects in use:** Animated mesh gradient orbs, glassmorphism panels with shimmer borders,
neon glow box-shadows, spring easing animations, vinyl disk spin, ambient pulse.

## Web Folder Tree
```txt
web/
├── index.html          # Main app shell (sidebar + content-wrap + now-bar)
├── login.html          # Login page (glassmorphism card, animated mesh bg)
├── css/
│   ├── reset.css       # Google Fonts import + box-sizing reset
│   ├── variables.css   # Design tokens (colors, spacing, radius, animation)
│   └── app.css         # All component styles + 5-tier responsive breakpoints
├── js/
│   ├── api.js          # Fetch helpers and API wrappers
│   ├── auth.js         # Login/logout, cookie handling, role handling
│   ├── player.js       # Audio element, queue, playback state (singleton)
│   ├── library.js      # Folder/track rendering, context menu
│   ├── downloader.js   # Visual folder-picker, multi-select, parallel job dispatch, SSE logs, history
│   ├── websocket.js    # /ws/live connection and live updates
│   └── app.js          # View routing, render functions, keyboard shortcuts
└── icons/
```

## Responsive Breakpoints
| Breakpoint | Behaviour |
|---|---|
| `≤1240px` | Queue panel hidden; sidebar 210px |
| `≤1024px` | Sidebar narrows; now-bar compresses; player stacks vertically |
| `≤900px` | Sidebar collapses to horizontal scrollable tab bar at top |
| `≤600px` | Mobile: icon labels hidden, touch targets ≥44px, player bar stacks |
| `≤375px` | Brand hidden; 2-column folder grid |

## Build Order
1. `css/reset.css`
2. `css/variables.css`
3. `css/app.css`
4. `login.html`
5. `js/api.js`
6. `js/auth.js`
7. `js/websocket.js`
8. `js/player.js`
9. `js/library.js`
10. `js/downloader.js`
11. `js/app.js`
12. `index.html`

## Rules
- Hash routes: `#library #player #downloads #settings #about`
- Save token in `localStorage`
- Login screen: role first (Admin / Guest), then only the required fields
- No CDN, no internet dependency (except Google Fonts preconnect in HTML)
- All assets served from the Freetopify server itself
- **No manual cache-busting needed** — server sends `Cache-Control: no-cache` on all `/web/*.js|html|css`
- All JS module imports must use bare (no `?v=`) paths so the browser treats them as a single module instance

## Login Flows
- **Admin**: `POST /auth/login` with username + password → JWT cookie
- **Guest**: `POST /auth/guest` with display name + shared PIN → short-lived JWT cookie
- Keep helper text short; never expose internal env var names in UI copy

## API Use
- Login: `POST /auth/login`
- Guest: `POST /auth/guest`
- Browse: `GET /api/v1/library/browse?path=` (items include `absolute_path`)
- Create folder: `POST /api/v1/library/mkdir`
- Stream: `GET /stream/{file_path}`
- Start download: `POST /api/v1/download/start` (body: `url, type, genre, format, output_dir?`)
- Job list: `GET /api/v1/download/jobs` (polled only while active jobs exist)
- Download progress: `GET /api/v1/download/progress/{job_id}` (SSE)
- Download history: `GET /api/v1/download/history` (permanent local JSONL log)
- Live updates: `GET /ws/live?token=...` (WebSocket)

## UX Must
- Folder-first browsing (real disk tree)
- Content header with Back button
- Player bar always visible (glassmorphism now-bar at bottom)
- Queue panel (right sidebar, hidden ≤1240px)
- Keyboard shortcuts: Space (play/pause), ←→ (prev/next), M (mute)
- Context menu on right-click / long-press: cut, copy, paste, rename, delete, edit metadata
- Responsive: mobile (390px), tablet (768px), desktop (1440px)
- About page with developer credits, GitHub/Instagram links, live elapsed timer, donate placeholder

## Test Quick
- Open web → login works (admin + guest)
- Browse folder → works with no reload
- Click track → plays, now-bar updates, vinyl spins, Now Playing view syncs
- Controls (play/pause/next/prev/shuffle/repeat) all respond correctly
- File added to library → auto-refresh via WebSocket (only after full audio file write, not during .part download)
- Downloads panel → visual folder grid, multi-select, New Folder modal, parallel jobs
- Each job → live SSE log card, badge updates, history row appears on completion
- History persists across page refresh (reads from `logs/download_history.log`)
- Resize to 390px → sidebar collapses to horizontal pills
- Context menu → appears clamped within viewport with glass styling

## Safari Smoke Checklist
- Open app in Safari over HTTP (`http://...`) and verify live library updates still connect.
- Open app in Safari over HTTPS (`https://...`) and verify live library updates connect via `wss://`.
- Confirm no visible panel transparency breakage when `backdrop-filter` is unavailable.
- Verify login, browse, playback controls, and downloads panel behavior are unchanged from Chrome/Firefox.

## Git Flow
- `web: add auth and api modules`
- `web: implement library browser`
- `web: add player and queue ui`
- `style: gen z redesign — neon glassmorphism, responsive, animations`
