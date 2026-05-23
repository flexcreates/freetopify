# Freetopify — Master PRD (Lean)

Version: 1.1 (trimmed)
Project: Freetopify
Tagline: self-hosted, folder-first music server

## Purpose
This file now hold only shared vision + rules.
Detailed build docs moved to:
- [Server Doc](./server.md)
- [Web Doc](./web.md)
- [Android Doc](./android.md)

If detail duplicate here and split doc, split doc is source of truth.

## Product Summary
Freetopify has 3 parts:
- Server (FastAPI, Python): auth, library browse, stream, scan/watch, download, live events
- Web (vanilla HTML/CSS/JS): login, folder browse, player, downloads, settings
- Android (Flutter): mobile browse/player, live updates, LAN/Tailscale/Bluetooth PAN

Design rule: folder-first navigation from real disk tree.

## Goals
- Self-hosted private music system
- Live file update without manual refresh
- Works LAN + Tailscale + Bluetooth PAN
- Offline usable after setup
- Low resource use (ARM SBC friendly)

## Non-Goals (v1)
- Multi-user
- iOS app
- Video streaming
- Built-in transcoding

## Shared Technical Decisions
- Server bind: `0.0.0.0:7171`
- Public endpoint: `/api/v1/system/health`
- All other API endpoints require JWT bearer
- Streaming must support HTTP Range (`206`)
- Watcher broadcasts live update events
- Download progress uses SSE

## Shared Config Contract (.env)
Required keys (TAILSCALE_IP optional):
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

Real values in `.env` (not commit).
Template values in `.env.example` (commit).

## Security Rules (Global)
- Never serve file outside `MUSIC_LIBRARY_PATH`
- Password hash only (bcrypt), no plaintext
- JWT with `HS256` + strong `SECRET_KEY`
- Rate limit login + download job creation

## Repo Workflow
Build and ship order:
1. Server
2. Web
3. Android

Use split docs for exact file-by-file tasks:
- [Server Doc](./server.md)
- [Web Doc](./web.md)
- [Android Doc](./android.md)

## Done Definition (Project)
- Server tests pass for auth/browse/stream/range/ws/sse/path safety
- Web can login, browse folders, play, show live updates
- Android can login, browse, play, reconnect, handle LAN/Tailscale/BT

## Notes
Old long PRD content intentionally removed to avoid duplicate/conflict.
Keep this file small. Put implementation detail only in split docs.
