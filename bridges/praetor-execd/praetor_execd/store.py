from __future__ import annotations

from datetime import datetime, timezone
import json
import threading
import uuid
from pathlib import Path
from typing import Any

from .models import CreateRunRequest, RunEvent, RunRecord


class RunStore:
    def __init__(
        self,
        max_event_buffer: int,
        persist_run_logs: bool = False,
        log_dir: str | None = None,
    ) -> None:
        self._lock = threading.RLock()
        self._runs: dict[str, RunRecord] = {}
        self._events: dict[str, list[RunEvent]] = {}
        self._max_event_buffer = max_event_buffer
        self._persist_run_logs = persist_run_logs
        self._log_dir = Path(log_dir).expanduser() if log_dir else None
        if self._persist_run_logs and self._log_dir is not None:
            self._log_dir.mkdir(parents=True, exist_ok=True)

    def create_run(self, request: CreateRunRequest, host_workdir: str) -> RunRecord:
        with self._lock:
            run_id = f"run_{uuid.uuid4().hex[:12]}"
            record = RunRecord(
                run_id=run_id,
                request_id=request.request_id,
                mission_id=request.mission_id,
                task_id=request.task_id,
                executor=request.executor,
                status="accepted",
                host_workdir=host_workdir,
            )
            self._runs[run_id] = record
            self._events[run_id] = []
            self.append_event(run_id, "run_accepted", {"status": "accepted"})
            record.status = "queued"
            self.append_event(run_id, "normalized_status", {"status": "queued"})
            self._persist_run_record_unlocked(record)
            return record

    def get_run(self, run_id: str) -> RunRecord | None:
        with self._lock:
            return self._runs.get(run_id)

    def list_events(self, run_id: str, after_seq: int = 0) -> list[RunEvent]:
        with self._lock:
            return [event for event in self._events.get(run_id, []) if event.seq > after_seq]

    def append_event(self, run_id: str, event_type: str, data: dict[str, Any]) -> None:
        with self._lock:
            events = self._events.setdefault(run_id, [])
            seq = len(events) + 1
            event = RunEvent(seq=seq, type=event_type, run_id=run_id, data=data)
            events.append(event)
            if len(events) > self._max_event_buffer:
                self._events[run_id] = events[-self._max_event_buffer :]
            self._persist_event(run_id, event)

    def transition_run(self, run_id: str, **fields: Any) -> RunRecord | None:
        with self._lock:
            record = self._runs.get(run_id)
            if record is None:
                return None
            updated = record.model_copy(update=fields)
            self._runs[run_id] = updated
            self._persist_run_record_unlocked(updated)
            return updated

    def complete_run(
        self,
        run_id: str,
        *,
        status: str,
        normalized_status: str,
        requires_owner_action: bool,
        pause_reason: str | None,
        exit_code: int | None,
        changed_files: list[str],
        duration_ms: int,
        stdout_tail: str | None,
        stderr_tail: str | None,
        usage_update: dict[str, Any] | None = None,
    ) -> RunRecord | None:
        with self._lock:
            record = self._runs.get(run_id)
            if record is None:
                return None
            usage = record.usage.model_copy(
                update={"duration_ms": duration_ms, **(usage_update or {})}
            )
            updated = record.model_copy(
                update={
                    "status": status,
                    "normalized_status": normalized_status,
                    "requires_owner_action": requires_owner_action,
                    "pause_reason": pause_reason,
                    "exit_code": exit_code,
                    "finished_at": record.finished_at or datetime.now(timezone.utc),
                    "changed_files": changed_files,
                    "usage": usage,
                    "stdout_tail": stdout_tail,
                    "stderr_tail": stderr_tail,
                }
            )
            self._runs[run_id] = updated
            self._persist_run_record_unlocked(updated)
            return updated

    def cancel_run(self, run_id: str) -> RunRecord | None:
        with self._lock:
            record = self._runs.get(run_id)
            if record is None:
                return None
            if record.status in {"completed", "cancelled", "failed_transient", "failed_permanent"}:
                return record
            record.status = "cancelled"
            record.normalized_status = "cancelled"
            record.requires_owner_action = False
            record.finished_at = record.finished_at or datetime.now(timezone.utc)
            self.append_event(run_id, "run_cancelled", {"status": "cancelled"})
            self._persist_run_record_unlocked(record)
            return record

    def _persist_run_record_unlocked(self, record: RunRecord) -> None:
        if not self._persist_run_logs or self._log_dir is None:
            return
        path = self._log_dir / f"{record.run_id}.json"
        path.write_text(record.model_dump_json(indent=2), encoding="utf-8")

    def _persist_event(self, run_id: str, event: RunEvent) -> None:
        if not self._persist_run_logs or self._log_dir is None:
            return
        path = self._log_dir / f"{run_id}.events.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event.model_dump(mode="json"), ensure_ascii=True))
            f.write("\n")
