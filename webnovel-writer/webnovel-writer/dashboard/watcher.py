"""
Watchdog 파일 변경 감시기 + SSE 푸시

PROJECT_ROOT/.webnovel/ 디렉토리 하위의 state.json / index.db 등 파일의 쓰기 이벤트를 감시하여,
SSE를 통해 연결된 모든 프론트엔드 클라이언트에 데이터 새로고침을 알립니다.
"""

import asyncio
import json
import time
from pathlib import Path
from typing import AsyncGenerator

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent


class _WebnovelFileHandler(FileSystemEventHandler):
    """.webnovel/ 디렉토리 하위 핵심 파일의 수정/생성 이벤트만 감시합니다."""

    WATCH_NAMES = {"state.json", "index.db", "workflow_state.json"}

    def __init__(self, notify_callback):
        super().__init__()
        self._notify = notify_callback

    def on_modified(self, event):
        if event.is_directory:
            return
        if Path(event.src_path).name in self.WATCH_NAMES:
            self._notify(event.src_path, "modified")

    def on_created(self, event):
        if event.is_directory:
            return
        if Path(event.src_path).name in self.WATCH_NAMES:
            self._notify(event.src_path, "created")


class FileWatcher:
    """watchdog Observer와 SSE 클라이언트 구독을 관리합니다."""

    def __init__(self):
        self._observer: Observer | None = None
        self._subscribers: list[asyncio.Queue] = []
        self._loop: asyncio.AbstractEventLoop | None = None

    # --- 구독 관리 ---

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=64)
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        try:
            self._subscribers.remove(q)
        except ValueError:
            pass

    # --- 푸시 ---

    def _on_change(self, path: str, kind: str):
        """watchdog 스레드에서 호출되어, 메인 이벤트 루프로 알림을 전달합니다."""
        msg = json.dumps({"file": Path(path).name, "kind": kind, "ts": time.time()})
        if self._loop and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(self._dispatch, msg)

    def _dispatch(self, msg: str):
        dead: list[asyncio.Queue] = []
        for q in self._subscribers:
            try:
                q.put_nowait(msg)
            except asyncio.QueueFull:
                dead.append(q)
        for dq in dead:
            self.unsubscribe(dq)

    # --- 생명주기 ---

    def start(self, watch_dir: Path, loop: asyncio.AbstractEventLoop):
        """watchdog observer를 시작하여 watch_dir을 감시합니다."""
        self._loop = loop
        handler = _WebnovelFileHandler(self._on_change)
        self._observer = Observer()
        self._observer.schedule(handler, str(watch_dir), recursive=False)
        self._observer.daemon = True
        self._observer.start()

    def stop(self):
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=3)
            self._observer = None
