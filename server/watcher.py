from __future__ import annotations

import asyncio
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class DebouncedHandler(FileSystemEventHandler):
    def __init__(self, loop: asyncio.AbstractEventLoop, callback, debounce_seconds: float = 0.5) -> None:
        self.loop = loop
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        self._last = 0.0

    def on_any_event(self, event):
        now = time.monotonic()
        if now - self._last < self.debounce_seconds:
            return
        self._last = now
        self.loop.call_soon_threadsafe(asyncio.create_task, self.callback(event))


class LibraryWatcher:
    def __init__(self, root: Path, loop: asyncio.AbstractEventLoop, callback) -> None:
        self.root = root
        self.loop = loop
        self.callback = callback
        self.observer = Observer()

    def start(self) -> None:
        handler = DebouncedHandler(self.loop, self.callback, 0.5)
        self.observer.schedule(handler, str(self.root), recursive=True)
        self.observer.start()

    def stop(self) -> None:
        self.observer.stop()
        self.observer.join(timeout=3)
