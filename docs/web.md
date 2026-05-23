# Web Build Doc (Caveman)

## Big Goal
Web is light client. No node. No npm. No framework. Just static files.

## Must Have
- Modern browser
- Server running (`:7171`)
- JS modules support

## Web Folder Tree (Need)
```txt
web/
├── index.html
├── login.html
├── css/
│   ├── reset.css
│   ├── variables.css
│   └── app.css
├── js/
│   ├── api.js
│   ├── auth.js
│   ├── player.js
│   ├── library.js
│   ├── downloader.js
│   ├── websocket.js
│   └── app.js
└── icons/
```

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
- Hash routes: `#login #library #player #downloads #settings`
- Save token in `localStorage`
- Dark default, light toggle save in `localStorage`
- Live updates from `/ws/live?token=...`
- Download progress from SSE `/api/v1/download/progress/{job_id}`
- No CDN, no internet dependency
- Use only local assets and bundled CSS/JS

## API Use
- Login: `POST /auth/login`
- Browse: `GET /api/v1/library/browse?path=`
- Stream: `GET /stream/{file_path}`
- Downloads: `POST /api/v1/download/start`

## UX Must
- Folder-first browsing (real disk tree)
- Breadcrumb
- Player bar always visible
- Queue list
- Keyboard shortcuts (space, left/right, m)
- Responsive mobile + desktop

## Test Quick
- Open web, login works
- Browse folder works no reload
- Click track plays
- File add in library auto refresh view
- Download panel shows live lines

## Git Flow
- `web: add auth and api modules`
- `web: implement library browser`
- `web: add player and queue ui`
