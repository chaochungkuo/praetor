from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .service import PraetorService


logger = logging.getLogger(__name__)


class MissionWorker:
    """Background thread that drains the mission_jobs queue.

    The worker claims jobs atomically (SQLite UPDATE WHERE status='queued'),
    runs each through PraetorService._execute_mission, and writes the result
    or error back to the job row. The /missions/{id}/run endpoint enqueues a
    job and then blocks on it via service.run_mission - the worker doing the
    work in a separate thread means the API process can survive a stuck
    executor without taking down the request loop.

    On API startup, service.recover_interrupted_jobs() marks any rows still
    in 'running' as 'interrupted', so a restart no longer silently drops
    in-flight work.
    """

    def __init__(self, service: "PraetorService", poll_interval: float = 0.25) -> None:
        self._service = service
        self._poll_interval = poll_interval
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop, name="praetor-mission-worker", daemon=True
        )
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
            self._thread = None

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                job = self._service.claim_next_mission_job()
            except Exception:
                logger.exception("mission worker: claim failed")
                if self._stop.wait(timeout=self._poll_interval):
                    return
                continue
            if job is None:
                if self._stop.wait(timeout=self._poll_interval):
                    return
                continue
            try:
                result = self._service.execute_mission_job(job.id)
                self._service.complete_mission_job(job.id, result)
            except Exception as exc:
                logger.exception("mission worker: job %s failed", job.id)
                self._service.fail_mission_job(job.id, str(exc))
