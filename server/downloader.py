from __future__ import annotations

import asyncio
import json
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path

from server.models import DownloadJob

_HISTORY_FILE = Path("logs/download_history.log")


def _ensure_history_dir() -> None:
    _HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)


def _append_history(entries: list[dict]) -> None:
    """Append completed track entries to the permanent download history log."""
    if not entries:
        return
    _ensure_history_dir()
    with _HISTORY_FILE.open("a", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_history(limit: int = 200) -> list[dict]:
    """Read the last `limit` entries from the history log, newest first."""
    if not _HISTORY_FILE.exists():
        return []
    try:
        lines = _HISTORY_FILE.read_text(encoding="utf-8").splitlines()
        entries = []
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
            if len(entries) >= limit:
                break
        return entries
    except Exception:
        return []


class Downloader:
    def __init__(self, ytdlp_path: str, library_root: Path, max_jobs: int = 5) -> None:
        self.ytdlp_path = ytdlp_path
        self.library_root = library_root
        self.max_jobs = max_jobs
        self.jobs: dict[str, DownloadJob] = {}
        self.processes: dict[str, asyncio.subprocess.Process] = {}

    def _job_folder(self, job_type: str, genre: str) -> Path:
        category = self.library_root / genre
        if genre.lower() == "music":
            if job_type == "podcast":
                return category / "Podcasts"
            if job_type == "single":
                return category / "Singles"
            if job_type == "mix":
                return category / "Mixes"
            return category / "Playlists"
        return category

    @staticmethod
    def _sanitize_component(value: str) -> str:
        cleaned = re.sub(r'[\\/:*?"<>|]', "-", value).strip()
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned or "Unknown"

    def _output_template(self, job: DownloadJob, output_dir: Path) -> str:
        if job.type == "single":
            return str(output_dir / "%(title)s.%(ext)s")
        if job.type == "podcast":
            return str(output_dir / "%(uploader)s" / "%(title)s.%(ext)s")
        if job.type == "mix":
            return str(output_dir / "%(playlist_title,s_title)s" / "%(title)s.%(ext)s")
        return str(output_dir / "%(playlist_title,s_title)s" / "%(title)s.%(ext)s")

    async def _run(self, job: DownloadJob, bitrate: str) -> None:
        output_dir = Path(job.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        output_tpl = self._output_template(job, output_dir)

        cmd = [
            self.ytdlp_path,
            "--extract-audio",
            "--audio-format",
            job.format,
            "--audio-quality",
            bitrate,
            "--embed-metadata",
            "--embed-thumbnail",
            "--newline",
            "-o",
            output_tpl,
            job.url,
        ]

        try:
            job.status = "running"
            job.started_at = datetime.now(UTC)
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            self.processes[job.job_id] = process

            assert process.stdout is not None
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace").rstrip()
                job.log_lines.append(text)
                if "Destination:" in text:
                    job.tracks_downloaded += 1

            code = await process.wait()
            self.processes.pop(job.job_id, None)

            if code == 0:
                job.status = "done"
                # Parse downloaded track titles from yt-dlp "Destination:" lines
                completed_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
                history_entries = []
                for log_line in job.log_lines:
                    if "Destination:" in log_line:
                        # e.g. "[download] Destination: /path/to/Song Title.mp3"
                        dest = log_line.split("Destination:", 1)[-1].strip()
                        track_name = Path(dest).stem
                        history_entries.append({
                            "ts": completed_at,
                            "title": track_name,
                            "folder": job.genre,
                            "format": job.format,
                            "url": job.url,
                        })
                if history_entries:
                    _append_history(history_entries)
                elif job.tracks_downloaded == 0:
                    # fallback: log the URL with no title parsed
                    _append_history([{
                        "ts": completed_at,
                        "title": job.url,
                        "folder": job.genre,
                        "format": job.format,
                        "url": job.url,
                    }])
            else:
                job.status = "failed"
                job.error = f"yt-dlp exited with {code}"
                job.tracks_failed += 1
        except Exception as exc:
            self.processes.pop(job.job_id, None)
            job.status = "failed"
            job.error = str(exc)
            job.tracks_failed += 1
            job.log_lines.append(f"ERROR: {exc}")
        finally:
            job.finished_at = datetime.now(UTC)

    async def _start_job(self, url: str, job_type: str, genre: str, fmt: str, bitrate: str, output_dir: Path) -> str:
        active = sum(1 for j in self.jobs.values() if j.status in {"queued", "running"})
        if active >= self.max_jobs:
            raise RuntimeError("Too many concurrent jobs")

        clean_genre = self._sanitize_component(genre or "Music")
        job_id = str(uuid.uuid4())
        job = DownloadJob(
            job_id=job_id,
            url=url,
            type=job_type,
            status="queued",
            genre=clean_genre,
            format=fmt,
            output_dir=str(output_dir),
        )
        self.jobs[job_id] = job
        asyncio.create_task(self._run(job, bitrate))
        return job_id

    async def download_single(self, url: str, genre: str, fmt: str, bitrate: str, output_dir: str | None = None) -> str:
        clean_genre = self._sanitize_component(genre or "Music")
        target = Path(output_dir) if output_dir else self._job_folder("single", clean_genre)
        return await self._start_job(url, "single", clean_genre, fmt, bitrate, target)

    async def download_playlist(self, url: str, genre: str, fmt: str, bitrate: str, output_dir: str | None = None) -> str:
        clean_genre = self._sanitize_component(genre or "Music")
        target = Path(output_dir) if output_dir else self._job_folder("playlist", clean_genre)
        return await self._start_job(url, "playlist", clean_genre, fmt, bitrate, target)

    async def download_podcast(self, url: str, output_dir: str | None = None) -> str:
        target = Path(output_dir) if output_dir else self._job_folder("podcast", "")
        return await self._start_job(url, "podcast", "Podcast", "mp3", "320k", target)

    def get_job_status(self, job_id: str) -> DownloadJob | None:
        return self.jobs.get(job_id)

    def list_jobs(self) -> list[DownloadJob]:
        return sorted(self.jobs.values(), key=lambda j: j.started_at or datetime.min.replace(tzinfo=UTC), reverse=True)

    async def cancel_job(self, job_id: str) -> bool:
        process = self.processes.get(job_id)
        if not process:
            return False
        process.terminate()
        await process.wait()
        job = self.jobs.get(job_id)
        if job:
            job.status = "failed"
            job.error = "Cancelled"
            job.finished_at = datetime.now(UTC)
        return True
