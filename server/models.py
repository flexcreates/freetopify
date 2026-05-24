from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TrackItem(BaseModel):
    id: str
    name: str
    path: str
    type: str = "track"
    title: str | None = None
    artist: str | None = None
    album: str | None = None
    duration: float | None = None
    format: str | None = None
    bitrate: int | None = None
    size_bytes: int | None = None


class FolderItem(BaseModel):
    name: str
    path: str
    type: str = "folder"
    child_count: int = 0
    track_count: int = 0


class BrowseResponse(BaseModel):
    path: str
    type: str = "folder"
    items: list[dict[str, Any]]


class DownloadStartRequest(BaseModel):
    url: str
    type: str = "auto"
    genre: str = "Music"
    format: str = "mp3"
    bitrate: str = "320k"
    output_dir: str | None = None  # absolute path; if set, overrides genre-derived folder


class GuestRequest(BaseModel):
    name: str
    pin: str


@dataclass
class DownloadJob:
    job_id: str
    url: str
    type: str
    status: str
    genre: str
    format: str
    output_dir: str
    tracks_downloaded: int = 0
    tracks_failed: int = 0
    log_lines: list[str] = field(default_factory=list)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "url": self.url,
            "type": self.type,
            "status": self.status,
            "genre": self.genre,
            "format": self.format,
            "output_dir": self.output_dir,
            "tracks_downloaded": self.tracks_downloaded,
            "tracks_failed": self.tracks_failed,
            "log_lines": self.log_lines,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "error": self.error,
        }
