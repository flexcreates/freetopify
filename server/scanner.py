from __future__ import annotations

import hashlib
import os
from pathlib import Path

import aiosqlite
from mutagen import File as MutagenFile

AUDIO_EXTS = {".mp3", ".flac", ".ogg", ".m4a", ".aac", ".opus", ".wav", ".wv"}


class ScanTracker:
    def __init__(self) -> None:
        self.running = False
        self.scanned = 0
        self.total = 0

    def snapshot(self) -> dict[str, int | bool]:
        return {"running": self.running, "scanned": self.scanned, "total": self.total}


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _tag(tags, key: str) -> str | None:
    if not tags:
        return None
    value = tags.get(key)
    if isinstance(value, list) and value:
        return str(value[0])
    if value is not None:
        return str(value)
    return None


def _read_meta(path: Path) -> dict[str, str | int | float | None]:
    try:
        audio = MutagenFile(path)
        tags = audio.tags if audio else None
        info = audio.info if audio else None
    except Exception:
        tags = None
        info = None

    return {
        "title": _tag(tags, "title") or _tag(tags, "TIT2"),
        "artist": _tag(tags, "artist") or _tag(tags, "TPE1"),
        "album": _tag(tags, "album") or _tag(tags, "TALB"),
        "album_artist": _tag(tags, "albumartist") or _tag(tags, "TPE2"),
        "genre": _tag(tags, "genre") or _tag(tags, "TCON"),
        "duration_seconds": float(getattr(info, "length", 0.0) or 0.0),
        "bitrate_kbps": int((getattr(info, "bitrate", 0) or 0) / 1000) or None,
        "sample_rate_hz": int(getattr(info, "sample_rate", 0) or 0) or None,
    }


async def scan_library(library_root: Path, database_path: str, tracker: ScanTracker) -> None:
    tracker.running = True
    tracker.scanned = 0

    files: list[Path] = []
    folders: set[Path] = {library_root}

    for root, dirnames, filenames in os.walk(library_root):
        root_path = Path(root)
        folders.add(root_path)
        for d in dirnames:
            folders.add(root_path / d)
        for name in filenames:
            path = root_path / name
            if path.suffix.lower() in AUDIO_EXTS:
                files.append(path)

    tracker.total = len(files)

    async with aiosqlite.connect(database_path) as db:
        for folder in folders:
            rel = "." if folder == library_root else str(folder.relative_to(library_root))
            parent = None if rel == "." else str(Path(rel).parent)
            if parent == ".":
                parent = ""

            children = sum(1 for x in folders if x != folder and x.parent == folder)
            track_count = sum(1 for f in files if f.parent == folder)

            await db.execute(
                """
                INSERT INTO folders (id, relative_path, absolute_path, name, parent_path, child_folder_count, track_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(relative_path) DO UPDATE SET
                    absolute_path=excluded.absolute_path,
                    name=excluded.name,
                    parent_path=excluded.parent_path,
                    child_folder_count=excluded.child_folder_count,
                    track_count=excluded.track_count,
                    scanned_at=CURRENT_TIMESTAMP
                """,
                (
                    _sha(rel),
                    rel,
                    str(folder.resolve()),
                    folder.name if rel != "." else "/",
                    parent,
                    children,
                    track_count,
                ),
            )

        for path in files:
            tracker.scanned += 1
            rel = str(path.relative_to(library_root))
            stat = path.stat()

            cur = await db.execute("SELECT mtime FROM tracks WHERE relative_path = ?", (rel,))
            row = await cur.fetchone()
            if row and float(row[0]) == float(stat.st_mtime):
                continue

            meta = _read_meta(path)
            await db.execute(
                """
                INSERT INTO tracks (
                    id, relative_path, absolute_path, filename, title, artist, album, album_artist,
                    genre, duration_seconds, bitrate_kbps, sample_rate_hz, format,
                    file_size_bytes, has_embedded_art, mtime
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(relative_path) DO UPDATE SET
                    absolute_path=excluded.absolute_path,
                    filename=excluded.filename,
                    title=excluded.title,
                    artist=excluded.artist,
                    album=excluded.album,
                    album_artist=excluded.album_artist,
                    genre=excluded.genre,
                    duration_seconds=excluded.duration_seconds,
                    bitrate_kbps=excluded.bitrate_kbps,
                    sample_rate_hz=excluded.sample_rate_hz,
                    format=excluded.format,
                    file_size_bytes=excluded.file_size_bytes,
                    has_embedded_art=excluded.has_embedded_art,
                    mtime=excluded.mtime,
                    scanned_at=CURRENT_TIMESTAMP
                """,
                (
                    _sha(rel),
                    rel,
                    str(path.resolve()),
                    path.name,
                    meta["title"],
                    meta["artist"],
                    meta["album"],
                    meta["album_artist"],
                    meta["genre"],
                    meta["duration_seconds"],
                    meta["bitrate_kbps"],
                    meta["sample_rate_hz"],
                    path.suffix.lower().lstrip("."),
                    stat.st_size,
                    0,
                    stat.st_mtime,
                ),
            )

        await db.execute(
            "DELETE FROM tracks WHERE absolute_path NOT IN ({})".format(
                ",".join("?" for _ in files) if files else "''"
            ),
            tuple(str(f.resolve()) for f in files),
        )
        await db.commit()

    tracker.running = False
