from __future__ import annotations

from pathlib import Path

import aiosqlite
from fastapi import APIRouter, Header, HTTPException, Query, Request, status
from fastapi.responses import FileResponse, Response, StreamingResponse
from mutagen import File as MutagenFile

from server.auth import get_current_user_from_request

router = APIRouter(tags=["stream"])

MIME_TYPES = {
    ".mp3": "audio/mpeg",
    ".flac": "audio/flac",
    ".ogg": "audio/ogg",
    ".m4a": "audio/mp4",
    ".aac": "audio/aac",
    ".opus": "audio/opus",
    ".wav": "audio/wav",
    ".wv": "audio/x-wavpack",
}


def safe_path(library_root: Path, requested_path: str) -> Path:
    root = library_root.resolve()
    resolved = root.joinpath(requested_path).resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")
    return resolved


def _parse_range(range_header: str, file_size: int) -> tuple[int, int]:
    if not range_header.startswith("bytes="):
        raise HTTPException(status_code=416, detail="Invalid range")
    value = range_header.replace("bytes=", "", 1)
    start_s, end_s = value.split("-", 1)
    start = int(start_s) if start_s else 0
    end = int(end_s) if end_s else file_size - 1
    if start > end or end >= file_size:
        raise HTTPException(status_code=416, detail="Invalid range")
    return start, end


async def _iter_file_range(path: Path, start: int, end: int, chunk_size: int = 1024 * 256):
    with path.open("rb") as f:
        f.seek(start)
        remaining = end - start + 1
        while remaining > 0:
            size = min(chunk_size, remaining)
            data = f.read(size)
            if not data:
                break
            remaining -= len(data)
            yield data


@router.get("/stream/{file_path:path}")
async def stream_audio(
    file_path: str,
    request: Request,
    range_header: str | None = Header(default=None, alias="Range"),
    token: str | None = Query(default=None),
):
    get_current_user_from_request(request, token_query=token)
    settings = request.app.state.settings
    file = safe_path(settings.music_library_path, file_path)
    if not file.exists() or not file.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    file_size = file.stat().st_size
    media_type = MIME_TYPES.get(file.suffix.lower(), "application/octet-stream")

    if range_header:
        start, end = _parse_range(range_header, file_size)
        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(end - start + 1),
            "Content-Type": media_type,
        }
        return StreamingResponse(
            _iter_file_range(file, start, end),
            status_code=status.HTTP_206_PARTIAL_CONTENT,
            headers=headers,
            media_type=media_type,
        )

    return FileResponse(file, media_type=media_type, headers={"Accept-Ranges": "bytes"})


def _extract_embedded_art(path: Path) -> tuple[bytes, str] | None:
    audio = MutagenFile(path)
    if not audio:
        return None

    # MP3/ID3 APIC
    if getattr(audio, "tags", None):
        for tag in audio.tags.values():
            mime = getattr(tag, "mime", None)
            data = getattr(tag, "data", None)
            if mime and data:
                return data, mime

    # FLAC pictures
    pics = getattr(audio, "pictures", None)
    if pics:
        pic = pics[0]
        return pic.data, pic.mime or "image/jpeg"

    # MP4 covr
    tags = getattr(audio, "tags", None)
    if tags and "covr" in tags and tags["covr"]:
        data = bytes(tags["covr"][0])
        return data, "image/jpeg"

    return None


@router.get("/thumbnail/{track_ref:path}")
async def thumbnail(
    track_ref: str,
    request: Request,
    token: str | None = Query(default=None),
):
    get_current_user_from_request(request, token_query=token)
    settings = request.app.state.settings

    # Accept either relative path or DB id.
    candidate: Path | None = None
    rel_like = track_ref.strip("/")
    if rel_like:
        p = safe_path(settings.music_library_path, rel_like)
        if p.exists() and p.is_file():
            candidate = p

    if candidate is None:
        async with aiosqlite.connect(str(settings.database_path)) as db:
            cur = await db.execute("SELECT absolute_path FROM tracks WHERE id = ? OR relative_path = ?", (track_ref, track_ref))
            row = await cur.fetchone()
        if row:
            p = Path(row[0]).resolve()
            try:
                p.relative_to(settings.music_library_path.resolve())
            except ValueError:
                raise HTTPException(status_code=403, detail="Access denied")
            if p.exists() and p.is_file():
                candidate = p

    if candidate is None:
        raise HTTPException(status_code=404, detail="Track not found")

    art = _extract_embedded_art(candidate)
    if not art:
        raise HTTPException(status_code=404, detail="No embedded art")

    data, mime = art
    return Response(content=data, media_type=mime)
