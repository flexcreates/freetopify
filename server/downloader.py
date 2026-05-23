from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from pathlib import Path

from server.models import DownloadJob


class Downloader:
    def __init__(self, ytdlp_path: str, library_root: Path, max_jobs: int = 5) -> None:
        self.ytdlp_path = ytdlp_path
        self.library_root = library_root
        self.max_jobs = max_jobs
        self.jobs: dict[str, DownloadJob] = {}
        self.processes: dict[str, asyncio.subprocess.Process] = {}

    def _job_folder(self, job_type: str, genre: str) -> Path:
        if job_type == "podcast":
            return self.library_root / "Podcasts"
        if job_type == "single":
            return self.library_root / "Singles" / genre
        if job_type == "mix":
            return self.library_root / "Mixes"
        return self.library_root / "Playlists" / genre

    async def _run(self, job: DownloadJob, bitrate: str) -> None:
        output_dir = Path(job.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        ext = "%(ext)s" if job.format == "flac" else "mp3"
        output_tpl = str(output_dir / f"%(title)s.%(id)s.{ext}")

        cmd = [
            self.ytdlp_path,
            "--extract-audio",
            "--audio-format",
            job.format,
            "--audio-quality",
            bitrate,
            "--embed-metadata",
            "--newline",
            "-o",
            output_tpl,
            job.url,
        ]

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
            if "[download]" in text and "%" in text:
                job.tracks_downloaded += 0

        code = await process.wait()
        self.processes.pop(job.job_id, None)

        if code == 0:
            job.status = "done"
        else:
            job.status = "failed"
            job.error = f"yt-dlp exited with {code}"
            job.tracks_failed += 1

        job.finished_at = datetime.now(UTC)

    async def _start_job(self, url: str, job_type: str, genre: str, fmt: str, bitrate: str, output_dir: Path) -> str:
        active = sum(1 for j in self.jobs.values() if j.status in {"queued", "running"})
        if active >= self.max_jobs:
            raise RuntimeError("Too many concurrent jobs")

        job_id = str(uuid.uuid4())
        job = DownloadJob(
            job_id=job_id,
            url=url,
            type=job_type,
            status="queued",
            genre=genre,
            format=fmt,
            output_dir=str(output_dir),
        )
        self.jobs[job_id] = job
        asyncio.create_task(self._run(job, bitrate))
        return job_id

    async def download_single(self, url: str, genre: str, fmt: str, bitrate: str, output_dir: str | None = None) -> str:
        target = Path(output_dir) if output_dir else self._job_folder("single", genre)
        return await self._start_job(url, "single", genre, fmt, bitrate, target)

    async def download_playlist(self, url: str, genre: str, fmt: str, bitrate: str, output_dir: str | None = None) -> str:
        target = Path(output_dir) if output_dir else self._job_folder("playlist", genre)
        return await self._start_job(url, "playlist", genre, fmt, bitrate, target)

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
