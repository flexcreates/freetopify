from __future__ import annotations

import asyncio
import time

import psutil
from fastapi import APIRouter, Depends, Request

from server.auth import get_current_user

router = APIRouter(prefix="/api/v1/system", tags=["system"])


@router.get("/health")
async def health(_user: str = Depends(get_current_user)) -> dict[str, str]:
    return {"status": "ok", "version": "1.0.0"}


@router.get("/stats")
async def stats(_user: str = Depends(get_current_user)) -> dict:
    vm = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "ram_total": vm.total,
        "ram_used": vm.used,
        "disk_total": disk.total,
        "disk_used": disk.used,
        "uptime_seconds": int(time.time() - psutil.boot_time()),
    }


@router.post("/rescan")
async def rescan(request: Request, _user: str = Depends(get_current_user)) -> dict:
    scanner = request.app.state.scanner
    settings = request.app.state.settings
    tracker = request.app.state.scan_tracker

    asyncio.create_task(scanner(settings.music_library_path, str(settings.database_path), tracker))
    return {"status": "started"}


@router.get("/scan-status")
async def scan_status(request: Request, _user: str = Depends(get_current_user)) -> dict:
    return request.app.state.scan_tracker.snapshot()
