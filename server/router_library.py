from __future__ import annotations

import os
from pathlib import Path
import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from server.auth import get_current_user
from server.models import BrowseResponse
from server.router_stream import safe_path

router = APIRouter(prefix="/api/v1/library", tags=["library"])
AUDIO_EXTS = {".mp3", ".flac", ".ogg", ".m4a", ".aac", ".opus", ".wav", ".wv"}


def _count_audio_recursive(folder) -> int:
    total = 0
    for root, _dirs, files in os.walk(folder):
        for name in files:
            if Path(name).suffix.lower() in AUDIO_EXTS:
                total += 1
    return total


@router.get("/browse", response_model=BrowseResponse)
async def browse(
    request: Request,
    path: str = Query(default=""),
    _user: str = Depends(get_current_user),
) -> BrowseResponse:
    settings = request.app.state.settings
    target = safe_path(settings.music_library_path, path)
    if not target.exists() or not target.is_dir():
        raise HTTPException(status_code=404, detail="Folder not found")

    items: list[dict] = []
    for child in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        rel = str(child.relative_to(settings.music_library_path))
        if child.is_dir():
            subfolders = sum(1 for x in child.iterdir() if x.is_dir())
            tracks = _count_audio_recursive(child)
            items.append(
                {
                    "name": child.name,
                    "path": rel,
                    "type": "folder",
                    "child_count": subfolders,
                    "track_count": tracks,
                }
            )
        else:
            if child.suffix.lower() not in AUDIO_EXTS:
                continue
            ext = child.suffix.lower().lstrip(".")
            items.append(
                {
                    "id": rel,
                    "name": child.name,
                    "path": rel,
                    "type": "track",
                    "title": child.stem,
                    "duration": None,
                    "format": ext,
                    "size_bytes": child.stat().st_size,
                }
            )

    return BrowseResponse(path=path, items=items)


@router.get("/search")
async def search(request: Request, q: str, _user: str = Depends(get_current_user)) -> dict:
    settings = request.app.state.settings
    async with aiosqlite.connect(str(settings.database_path)) as db:
        cur = await db.execute(
            """
            SELECT id, relative_path, filename, title, artist, album, duration_seconds, format, bitrate_kbps, file_size_bytes
            FROM tracks
            WHERE filename LIKE ? OR title LIKE ? OR artist LIKE ? OR album LIKE ?
            ORDER BY filename ASC
            LIMIT 200
            """,
            (f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%"),
        )
        rows = await cur.fetchall()

    return {
        "query": q,
        "items": [
            {
                "id": r[0],
                "path": r[1],
                "name": r[2],
                "title": r[3],
                "artist": r[4],
                "album": r[5],
                "duration": r[6],
                "format": r[7],
                "bitrate": r[8],
                "size_bytes": r[9],
                "type": "track",
            }
            for r in rows
        ],
    }


@router.get("/track/{track_id}")
async def track(request: Request, track_id: str, _user: str = Depends(get_current_user)) -> dict:
    settings = request.app.state.settings
    async with aiosqlite.connect(str(settings.database_path)) as db:
        cur = await db.execute("SELECT * FROM tracks WHERE id = ?", (track_id,))
        row = await cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Track not found")
    return {
        "id": row[0],
        "relative_path": row[1],
        "absolute_path": row[2],
        "filename": row[3],
        "title": row[4],
        "artist": row[5],
        "album": row[6],
        "duration_seconds": row[11],
        "format": row[14],
    }


@router.get("/stats")
async def stats(request: Request, _user: str = Depends(get_current_user)) -> dict:
    settings = request.app.state.settings
    async with aiosqlite.connect(str(settings.database_path)) as db:
        t = await (await db.execute("SELECT COUNT(*) FROM tracks")).fetchone()
        f = await (await db.execute("SELECT COUNT(*) FROM folders")).fetchone()
        s = await (await db.execute("SELECT COALESCE(SUM(file_size_bytes), 0) FROM tracks")).fetchone()
    return {"total_tracks": t[0], "total_folders": f[0], "total_size_bytes": s[0]}
