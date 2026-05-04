from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import AsyncIterator


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


@dataclass
class RunSession:
    mission_id: str
    run_id: str
    status: str = "running"
    started_at: str = field(default_factory=_now_iso)
    finished_at: str | None = None
    message: str | None = None
    log_count: int = 0


class RunRegistry:
    """In-memory tracker of live mission runs with pub/sub for SSE streaming.

    Keyed by mission_id. Each mission has at most one active session; starting
    a new run replaces any previous terminal session. Listeners receive events
    via asyncio.Queue scheduled onto the bound event loop.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._sessions: dict[str, RunSession] = {}
        self._listeners: dict[str, list[asyncio.Queue]] = {}
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def snapshot(self, mission_id: str) -> RunSession | None:
        with self._lock:
            return self._sessions.get(mission_id)

    def is_running(self, mission_id: str) -> bool:
        session = self.snapshot(mission_id)
        return bool(session and session.status == "running")

    def start(self, mission_id: str, run_id: str) -> RunSession:
        with self._lock:
            session = RunSession(mission_id=mission_id, run_id=run_id)
            self._sessions[mission_id] = session
        self._broadcast(mission_id, {
            "type": "started",
            "timestamp": session.started_at,
            "run_id": run_id,
        })
        return session

    def log(self, mission_id: str, message: str) -> None:
        with self._lock:
            session = self._sessions.get(mission_id)
            if session is None:
                return
            session.log_count += 1
        self._broadcast(mission_id, {
            "type": "log",
            "timestamp": _now_iso(),
            "message": message,
        })

    def finish(self, mission_id: str, status: str, message: str | None = None) -> None:
        with self._lock:
            session = self._sessions.get(mission_id)
            if session is None:
                return
            session.status = status
            session.finished_at = _now_iso()
            session.message = message
        self._broadcast(mission_id, {
            "type": "finished",
            "timestamp": session.finished_at,
            "status": status,
            "message": message,
        })

    def _broadcast(self, mission_id: str, event: dict) -> None:
        with self._lock:
            queues = list(self._listeners.get(mission_id, []))
            loop = self._loop
        if not queues or loop is None:
            return
        for queue in queues:
            try:
                loop.call_soon_threadsafe(queue.put_nowait, event)
            except Exception:
                pass

    async def subscribe(self, mission_id: str) -> AsyncIterator[dict]:
        queue: asyncio.Queue = asyncio.Queue(maxsize=128)
        with self._lock:
            self._listeners.setdefault(mission_id, []).append(queue)
            session = self._sessions.get(mission_id)
        try:
            if session is None:
                yield {
                    "type": "idle",
                    "timestamp": _now_iso(),
                }
            else:
                yield {
                    "type": "snapshot",
                    "timestamp": _now_iso(),
                    "status": session.status,
                    "started_at": session.started_at,
                    "finished_at": session.finished_at,
                    "message": session.message,
                    "run_id": session.run_id,
                    "log_count": session.log_count,
                }
                if session.status != "running":
                    yield {
                        "type": "finished",
                        "timestamp": session.finished_at or _now_iso(),
                        "status": session.status,
                        "message": session.message,
                    }
                    return
            while True:
                event = await queue.get()
                yield event
                if event.get("type") == "finished":
                    return
        finally:
            self._unsubscribe(mission_id, queue)

    def _unsubscribe(self, mission_id: str, queue: asyncio.Queue) -> None:
        with self._lock:
            listeners = self._listeners.get(mission_id, [])
            if queue in listeners:
                listeners.remove(queue)
            if not listeners:
                self._listeners.pop(mission_id, None)
