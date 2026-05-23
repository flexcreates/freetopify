from __future__ import annotations

import aiosqlite


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tracks (
    id TEXT PRIMARY KEY,
    relative_path TEXT UNIQUE NOT NULL,
    absolute_path TEXT NOT NULL,
    filename TEXT NOT NULL,
    title TEXT,
    artist TEXT,
    album TEXT,
    album_artist TEXT,
    genre TEXT,
    year INTEGER,
    track_number INTEGER,
    duration_seconds REAL,
    bitrate_kbps INTEGER,
    sample_rate_hz INTEGER,
    format TEXT,
    file_size_bytes INTEGER,
    has_embedded_art INTEGER DEFAULT 0,
    mtime REAL,
    scanned_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS folders (
    id TEXT PRIMARY KEY,
    relative_path TEXT UNIQUE NOT NULL,
    absolute_path TEXT NOT NULL,
    name TEXT NOT NULL,
    parent_path TEXT,
    child_folder_count INTEGER DEFAULT 0,
    track_count INTEGER DEFAULT 0,
    scanned_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS download_jobs (
    id TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    job_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    genre TEXT,
    format TEXT DEFAULT 'mp3',
    bitrate TEXT DEFAULT '320k',
    output_dir TEXT,
    tracks_downloaded INTEGER DEFAULT 0,
    tracks_failed INTEGER DEFAULT 0,
    error_message TEXT,
    started_at DATETIME,
    finished_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS download_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL REFERENCES download_jobs(id),
    line TEXT NOT NULL,
    level TEXT DEFAULT 'INFO',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tracks_artist ON tracks(artist);
CREATE INDEX IF NOT EXISTS idx_tracks_album ON tracks(album);
CREATE INDEX IF NOT EXISTS idx_tracks_genre ON tracks(genre);
CREATE INDEX IF NOT EXISTS idx_tracks_parent ON tracks(relative_path);
CREATE INDEX IF NOT EXISTS idx_folders_parent ON folders(parent_path);
"""


async def init_db(database_path: str) -> None:
    async with aiosqlite.connect(database_path) as db:
        await db.executescript(SCHEMA_SQL)
        await db.commit()
