from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import FileResponse, StreamingResponse

from server.auth import get_current_user

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
    if not str(resolved).startswith(str(root)):
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
    _user: str = Depends(get_current_user),
):
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
