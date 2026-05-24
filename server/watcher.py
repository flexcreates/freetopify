from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

log = logging.getLogger(__name__)

# Extensions that are definitely not final audio files.
# yt-dlp creates these during download — ignore them to avoid triggering
# a full library scan on every partial write.
_IGNORE_SUFFIXES = {
    ".part",   # yt-dlp in-progress download
    ".ytdl",   # yt-dlp temp marker
    ".tmp",    # generic temp
    ".webp",   # thumbnail (not audio)
    ".jpg",    # thumbnail
    ".png",    # thumbnail
    ".webm",   # raw video before audio extraction
    ".m4a",    # raw audio before extraction (kept only if format is m4a)
}


class DebouncedHandler(FileSystemEventHandler):
    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        callback,
        debounce_seconds: float = 2.5,  # raised from 0.5 — prevents per-chunk scan during download
    ) -> None:
        self.loop = loop
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        self._last = 0.0

    def on_any_event(self, event):
        # Ignore directory events and known temp/non-audio suffixes
        if event.is_directory:
            return
        src = getattr(event, "src_path", "") or ""
        if Path(src).suffix.lower() in _IGNORE_SUFFIXES:
            return

        now = time.monotonic()
        if now - self._last < self.debounce_seconds:
            return
        self._last = now
        log.debug("Library watcher: scheduling scan after event on %s", src)
        self.loop.call_soon_threadsafe(asyncio.create_task, self.callback(event))


class LibraryWatcher:
    def __init__(self, root: Path, loop: asyncio.AbstractEventLoop, callback) -> None:
        self.root = root
        self.loop = loop
        self.callback = callback
        self.observer = Observer()

    def start(self) -> None:
        handler = DebouncedHandler(self.loop, self.callback, 2.5)
        self.observer.schedule(handler, str(self.root), recursive=True)
        self.observer.start()

    def stop(self) -> None:
        self.observer.stop()
        self.observer.join(timeout=3)
