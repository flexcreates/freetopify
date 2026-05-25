from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from server.auth import get_current_user, get_current_user_from_request
from server.downloader import read_history
from server.models import DownloadStartRequest

router = APIRouter(prefix="/api/v1/download", tags=["download"])


@router.post("/start")
async def start_download(body: DownloadStartRequest, request: Request, _user: str = Depends(get_current_user)) -> dict:
    downloader = request.app.state.downloader

    job_type = body.type
    if job_type == "auto":
        job_type = "playlist" if "list=" in body.url else "single"

    if body.format not in {"mp3", "flac"}:
        raise HTTPException(status_code=400, detail="format must be mp3 or flac")
    if job_type not in {"single", "playlist", "podcast", "mix"}:
        raise HTTPException(status_code=400, detail="invalid download type")

    try:
        if job_type == "podcast":
            job_id = await downloader.download_podcast(body.url, output_dir=body.output_dir)
        elif job_type == "single":
            job_id = await downloader.download_single(body.url, body.genre, body.format, body.bitrate, output_dir=body.output_dir)
        elif job_type == "mix":
            job_id = await downloader.download_playlist(body.url, body.genre, body.format, body.bitrate, output_dir=body.output_dir)
        else:
            job_id = await downloader.download_playlist(body.url, body.genre, body.format, body.bitrate, output_dir=body.output_dir)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc

    return {"job_id": job_id, "status": "queued"}


@router.get("/jobs")
async def list_jobs(request: Request, _user: str = Depends(get_current_user)) -> dict:
    jobs = [j.to_dict() for j in request.app.state.downloader.list_jobs()]
    return {"items": jobs}


@router.get("/jobs/{job_id}")
async def job_status(job_id: str, request: Request, _user: str = Depends(get_current_user)) -> dict:
    job = request.app.state.downloader.get_job_status(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.to_dict()


@router.delete("/jobs/{job_id}")
async def cancel_job(job_id: str, request: Request, _user: str = Depends(get_current_user)) -> dict:
    done = await request.app.state.downloader.cancel_job(job_id)
    if not done:
        raise HTTPException(status_code=404, detail="Job not running")
    return {"status": "cancelled", "job_id": job_id}


@router.get("/progress/{job_id}")
async def progress(job_id: str, request: Request, token: str | None = None):
    await get_current_user_from_request(request, token_query=token)
    downloader = request.app.state.downloader

    async def stream():
        sent = 0
        while True:
            job = downloader.get_job_status(job_id)
            if not job:
                yield "event: error\ndata: {\"detail\":\"job not found\"}\n\n"
                break

            while sent < len(job.log_lines):
                payload = {"job_id": job.job_id, "status": job.status, "log": job.log_lines[sent]}
                yield f"data: {json.dumps(payload)}\n\n"
                sent += 1

            if job.status in {"done", "failed"}:
                payload = {"job_id": job.job_id, "status": job.status, "error": job.error}
                yield f"data: {json.dumps(payload)}\n\n"
                break

            await asyncio.sleep(0.5)

    return StreamingResponse(stream(), media_type="text/event-stream")


@router.get("/history")
async def download_history(_user: str = Depends(get_current_user)) -> dict:
    """Return the permanent on-device download history log (newest first)."""
    return {"items": read_history(limit=200)}
