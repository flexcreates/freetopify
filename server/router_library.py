from __future__ import annotations

import asyncio
import os
import shutil
from pathlib import Path
import aiosqlite
from mutagen import File as MutagenFile
from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File
from fastapi.responses import Response, RedirectResponse
from mutagen.id3 import ID3, APIC, error as ID3Error
from mutagen.flac import FLAC, Picture
from mutagen.mp4 import MP4, MP4Cover
import random
from shutil import copy2
import time
import asyncio

from server.auth import get_current_user, get_current_user_allow_guest, get_current_user_from_request, get_current_user_from_request_allow_guest
from server.models import BrowseResponse
from server.router_stream import safe_path, _extract_embedded_art
import logging

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
    _user: str = Depends(get_current_user_allow_guest),
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
                    "absolute_path": str(child),
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


@router.get("/recursive-tracks")
async def recursive_tracks(
    request: Request,
    path: str = Query(default=""),
    _user: str = Depends(get_current_user_allow_guest),
) -> dict:
    settings = request.app.state.settings
    target = safe_path(settings.music_library_path, path)
    if not target.exists() or not target.is_dir():
        raise HTTPException(status_code=404, detail="Folder not found")

    items: list[dict] = []
    # Limit recursive search to avoid massive payloads if library is huge
    max_tracks = 5000
    for root, _dirs, files in os.walk(target):
        root_path = Path(root)
        for name in sorted(files):
            p = root_path / name
            if p.suffix.lower() in AUDIO_EXTS:
                rel = str(p.relative_to(settings.music_library_path))
                ext = p.suffix.lower().lstrip(".")
                items.append({
                    "id": rel,
                    "name": name,
                    "path": rel,
                    "type": "track",
                    "title": p.stem,
                    "duration": None,
                    "format": ext,
                    "size_bytes": p.stat().st_size,
                })
                if len(items) >= max_tracks:
                    break
        if len(items) >= max_tracks:
            break

    return {"path": path, "items": items}


@router.get("/search")
async def search(request: Request, q: str, _user: str = Depends(get_current_user_allow_guest)) -> dict:
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
async def track(request: Request, track_id: str, _user: str = Depends(get_current_user_allow_guest)) -> dict:
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
async def stats(request: Request, _user: str = Depends(get_current_user_allow_guest)) -> dict:
    settings = request.app.state.settings
    async with aiosqlite.connect(str(settings.database_path)) as db:
        t = await (await db.execute("SELECT COUNT(*) FROM tracks")).fetchone()
        f = await (await db.execute("SELECT COUNT(*) FROM folders")).fetchone()
        s = await (await db.execute("SELECT COALESCE(SUM(file_size_bytes), 0) FROM tracks")).fetchone()
    return {"total_tracks": t[0], "total_folders": f[0], "total_size_bytes": s[0]}

@router.post('/mkdir')
async def make_folder(request: Request, body: dict, _user: str = Depends(get_current_user)) -> dict:
    """Create a new folder under the music library.
    Body: { "path": "relative/path/to/new/folder" }
    """
    path = body.get('path', '').strip().strip('/')
    if not path:
        raise HTTPException(status_code=400, detail='missing path')
    settings = request.app.state.settings
    target = safe_path(settings.music_library_path, path)
    if target.exists():
        raise HTTPException(status_code=409, detail='folder already exists')
    try:
        target.mkdir(parents=True, exist_ok=False)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return {'status': 'ok', 'path': path, 'absolute': str(target)}


@router.post('/delete')
async def delete_item(request: Request, body: dict, _user: str = Depends(get_current_user)) -> dict:
    """Delete a file or folder under the music library.
    Body: { "path": "relative/path/to/item" }
    """
    path = body.get('path')
    if not path:
        raise HTTPException(status_code=400, detail='missing path')
    settings = request.app.state.settings
    target = safe_path(settings.music_library_path, path)
    if not target.exists():
        raise HTTPException(status_code=404, detail='Not found')

    try:
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    # trigger rescan and broadcast
    scanner = request.app.state.scanner
    tracker = request.app.state.scan_tracker
    asyncio.create_task(scanner(settings.music_library_path, str(settings.database_path), tracker))
    await request.app.state.ws_manager.broadcast({"event": "library_update", "data": {"path": path, "action": "delete"}})
    return {"status": "ok", "path": path}


@router.post('/rename')
async def rename_item(request: Request, body: dict, _user: str = Depends(get_current_user)) -> dict:
    """Rename a file or folder. Body: { "path": "rel/old", "new_name": "newname.mp3" }
    """
    path = body.get('path')
    new_name = body.get('new_name')
    if not path or not new_name:
        raise HTTPException(status_code=400, detail='missing path or new_name')
    settings = request.app.state.settings
    src = safe_path(settings.music_library_path, path)
    if not src.exists():
        raise HTTPException(status_code=404, detail='Not found')
    new_name = Path(new_name).name
    dst = src.parent.joinpath(new_name).resolve()
    if not str(dst).startswith(str(settings.music_library_path.resolve())):
        raise HTTPException(status_code=403, detail='Access denied')
    try:
        src.rename(dst)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    scanner = request.app.state.scanner
    tracker = request.app.state.scan_tracker
    asyncio.create_task(scanner(settings.music_library_path, str(settings.database_path), tracker))
    await request.app.state.ws_manager.broadcast({"event": "library_update", "data": {"path": path, "action": "rename", "new": str(dst.relative_to(settings.music_library_path))}})
    return {"status": "ok", "old": path, "new": str(dst.relative_to(settings.music_library_path))}


@router.post('/move')
async def move_item(request: Request, body: dict, _user: str = Depends(get_current_user)) -> dict:
    """Move (or cut/paste) an item. Body: { "src": "rel/path", "dst_folder": "rel/destination/folder" }
    """
    src_p = body.get('src')
    dst_folder = body.get('dst_folder')
    if not src_p or dst_folder is None:
        raise HTTPException(status_code=400, detail='missing src or dst_folder')
    settings = request.app.state.settings
    src = safe_path(settings.music_library_path, src_p)
    if not src.exists():
        raise HTTPException(status_code=404, detail='source not found')
    dst_dir = safe_path(settings.music_library_path, dst_folder) if dst_folder != '' else settings.music_library_path
    if not dst_dir.exists() or not dst_dir.is_dir():
        raise HTTPException(status_code=404, detail='destination folder not found')
    dst = dst_dir.joinpath(src.name).resolve()
    if not str(dst).startswith(str(settings.music_library_path.resolve())):
        raise HTTPException(status_code=403, detail='Access denied')
    try:
        shutil.move(str(src), str(dst))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    scanner = request.app.state.scanner
    tracker = request.app.state.scan_tracker
    asyncio.create_task(scanner(settings.music_library_path, str(settings.database_path), tracker))
    await request.app.state.ws_manager.broadcast({"event": "library_update", "data": {"path": src_p, "action": "move", "new": str(dst.relative_to(settings.music_library_path))}})
    return {"status": "ok", "src": src_p, "dst": str(dst.relative_to(settings.music_library_path))}


@router.post('/copy')
async def copy_item(request: Request, body: dict, _user: str = Depends(get_current_user)) -> dict:
    """Copy an item. Body: { "src": "rel/path", "dst_folder": "rel/destination/folder" }
    """
    src_p = body.get('src')
    dst_folder = body.get('dst_folder')
    if not src_p or dst_folder is None:
        raise HTTPException(status_code=400, detail='missing src or dst_folder')
    settings = request.app.state.settings
    src = safe_path(settings.music_library_path, src_p)
    if not src.exists():
        raise HTTPException(status_code=404, detail='source not found')
    dst_dir = safe_path(settings.music_library_path, dst_folder) if dst_folder != '' else settings.music_library_path
    if not dst_dir.exists() or not dst_dir.is_dir():
        raise HTTPException(status_code=404, detail='destination folder not found')
    dst = dst_dir.joinpath(src.name).resolve()
    if not str(dst).startswith(str(settings.music_library_path.resolve())):
        raise HTTPException(status_code=403, detail='Access denied')
    try:
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    scanner = request.app.state.scanner
    tracker = request.app.state.scan_tracker
    asyncio.create_task(scanner(settings.music_library_path, str(settings.database_path), tracker))
    await request.app.state.ws_manager.broadcast({"event": "library_update", "data": {"path": src_p, "action": "copy", "new": str(dst.relative_to(settings.music_library_path))}})
    return {"status": "ok", "src": src_p, "dst": str(dst.relative_to(settings.music_library_path))}


@router.get('/meta')
async def get_metadata(request: Request, path: str = Query(default=''), _user: str = Depends(get_current_user_allow_guest)) -> dict:
    settings = request.app.state.settings
    if not path:
        raise HTTPException(status_code=400, detail='missing path')
    target = safe_path(settings.music_library_path, path)
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail='file not found')
    audio = MutagenFile(target)
    if not audio:
        raise HTTPException(status_code=404, detail='no metadata')
    tags = {}
    def _to_primitive(val):
        try:
            if isinstance(val, (list, tuple)) and val:
                v = val[0]
                return _to_primitive(v)
            # bytes -> try decode
            if isinstance(val, (bytes, bytearray)):
                try:
                    return val.decode('utf-8', errors='replace')
                except Exception:
                    return str(val)
            # many mutagen tag values implement __str__ sensibly
            return str(val)
        except Exception:
            return repr(val)

    if getattr(audio, 'tags', None):
        for k, v in audio.tags.items():
            tags[str(k)] = _to_primitive(v)
    info = getattr(audio, 'info', None)
    return {'tags': tags, 'info': {'length': getattr(info, 'length', None), 'bitrate': getattr(info, 'bitrate', None)}}


@router.post('/meta')
async def set_metadata(request: Request, body: dict, _user: str = Depends(get_current_user)) -> dict:
    path = body.get('path')
    tags = body.get('tags')
    if not path or tags is None:
        raise HTTPException(status_code=400, detail='missing path or tags')
    settings = request.app.state.settings
    target = safe_path(settings.music_library_path, path)
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail='file not found')
    audio = MutagenFile(target)
    if audio is None:
        raise HTTPException(status_code=400, detail='unsupported format')
    try:
        if not getattr(audio, 'tags', None):
            audio.add_tags()
    except Exception:
        pass
    for k, v in tags.items():
        try:
            audio.tags[k] = v
        except Exception:
            # some tag systems differ; attempt assignment anyway
            try:
                audio.tags[str(k)] = v
            except Exception:
                pass
    try:
        audio.save()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    scanner = request.app.state.scanner
    tracker = request.app.state.scan_tracker
    asyncio.create_task(scanner(settings.music_library_path, str(settings.database_path), tracker))
    await request.app.state.ws_manager.broadcast({"event": "library_update", "data": {"path": path, "action": "meta_update"}})
    return {'status': 'ok', 'path': path}


@router.post('/cover')
async def upload_cover(request: Request, path: str = Query(default=''), file: UploadFile = File(...), token: str | None = Query(default=None)) -> dict:
    """Upload and embed cover art into a track. Form: file, path=relative/path/to/file.mp3"""
    if not path:
        raise HTTPException(status_code=400, detail='missing path')
    # authenticate: accept token via query or Authorization header
    await get_current_user_from_request_allow_guest(request, token_query=token, allow_guest=True)
    settings = request.app.state.settings
    target = safe_path(settings.music_library_path, path)
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail='file not found')

    contents = await file.read()
    mime = file.content_type or 'image/jpeg'

    # backup original
    try:
        bak_dir = Path('data') / 'meta_backups'
        bak_dir.mkdir(parents=True, exist_ok=True)
        bak_name = bak_dir / f"{Path(path).name}.{int(time.time())}.bak"
        copy2(str(target), str(bak_name))
    except Exception:
        pass

    def _write_cover():
        try:
            suffix = target.suffix.lower()
            if suffix == '.mp3':
                try:
                    id3 = ID3(str(target))
                except ID3Error:
                    id3 = ID3()
                # remove existing APIC
                id3.delall('APIC')
                id3.add(APIC(encoding=3, mime=mime, type=3, desc='Cover', data=contents))
                id3.save(str(target))
            elif suffix == '.flac':
                fl = FLAC(str(target))
                pic = Picture()
                pic.data = contents
                pic.type = 3
                pic.mime = mime
                fl.clear_pictures()
                fl.add_picture(pic)
                fl.save()
            elif suffix in {'.m4a', '.mp4'}:
                mp4 = MP4(str(target))
                if mime == 'image/png':
                    cov = MP4Cover(contents, imageformat=MP4Cover.FORMAT_PNG)
                else:
                    cov = MP4Cover(contents, imageformat=MP4Cover.FORMAT_JPEG)
                mp4.tags['covr'] = [cov]
                mp4.save()
            else:
                # try mutagen generic tags
                audio = MutagenFile(str(target))
                if audio and hasattr(audio, 'tags'):
                    # best effort: set APIC-like if supported
                    try:
                        audio.tags['APIC'] = contents
                        audio.save()
                    except Exception:
                        raise
        except Exception as exc:
            raise

    try:
        # run file writes in thread
        await asyncio.to_thread(_write_cover)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'cover embed failed: {exc}')

    # trigger rescan and broadcast
    scanner = request.app.state.scanner
    tracker = request.app.state.scan_tracker
    asyncio.create_task(scanner(settings.music_library_path, str(settings.database_path), tracker))
    await request.app.state.ws_manager.broadcast({"event": "library_update", "data": {"path": path, "action": "cover_update"}})
    return {"status": "ok", "path": path}


@router.get('/cover')
async def get_folder_cover(request: Request, path: str = Query(default=''), token: str | None = Query(default=None)):
    """Return an embedded cover image for a folder (choose a random track in folder)."""
    # allow token query param for thumbnail access
    await get_current_user_from_request_allow_guest(request, token_query=token, allow_guest=True)
    settings = request.app.state.settings
    target = safe_path(settings.music_library_path, path) if path else settings.music_library_path
    if not target.exists() or not target.is_dir():
        raise HTTPException(status_code=404, detail='folder not found')

    # collect all audio files in folder subtree
    files: list[Path] = []
    for root, _dirs, filenames in os.walk(target):
        root_path = Path(root)
        for name in filenames:
            p = root_path / name
            if p.suffix.lower() in AUDIO_EXTS:
                files.append(p)

    if not files:
        raise HTTPException(status_code=404, detail='no audio files')

    # randomize order and try to find the first file that has embedded art
    random.shuffle(files)
    for choice in files:
        try:
            art = _extract_embedded_art(choice)
            if art:
                                data, mime = art
                                logging.getLogger('server').info('Serving folder cover from %s (mime=%s)', str(choice), mime)
                                return Response(content=data, media_type=mime)
        except Exception:
            continue
        # nothing found in the subtree -> return a small SVG placeholder so UI has something
        logging.getLogger('server').info('No embedded art found for folder %s (checked %d files)', str(target), len(files))
        svg = f"""
        <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 300 300'>
            <rect width='100%' height='100%' fill='#0c1b2b'/>
            <text x='50%' y='50%' fill='#6ea6df' font-family='sans-serif' font-size='30' text-anchor='middle' alignment-baseline='middle'>No Cover</text>
        </svg>
        """
        return Response(content=svg.encode('utf-8'), media_type='image/svg+xml')
