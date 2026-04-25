from __future__ import annotations

import os
import subprocess
import threading
import time
from pathlib import Path

from .config import AppConfig
from .models import CreateRunRequest
from .service import BridgeService
from .store import RunStore


def _snapshot_tree(root: Path) -> dict[str, float]:
    snapshot: dict[str, float] = {}
    if not root.exists():
        return snapshot
    for path in root.rglob("*"):
        if path.is_file():
            try:
                snapshot[str(path)] = path.stat().st_mtime
            except OSError:
                continue
    return snapshot


def _changed_files(before: dict[str, float], after: dict[str, float]) -> list[str]:
    changed = []
    keys = set(before) | set(after)
    for key in sorted(keys):
        if before.get(key) != after.get(key):
            changed.append(key)
    return changed


class RunManager:
    def __init__(self, config: AppConfig, service: BridgeService, store: RunStore) -> None:
        self._config = config
        self._service = service
        self._store = store
        self._lock = threading.Lock()
        self._slots = threading.BoundedSemaphore(max(1, config.runtime.max_concurrent_runs))
        self._processes: dict[str, subprocess.Popen[str]] = {}

    def enqueue(self, request: CreateRunRequest, run_id: str, host_workdir: str) -> None:
        thread = threading.Thread(
            target=self._execute_run,
            args=(request, run_id, host_workdir),
            daemon=True,
        )
        thread.start()

    def cancel(self, run_id: str) -> bool:
        with self._lock:
            process = self._processes.get(run_id)
        if process is None:
            return False
        try:
            process.terminate()
            return True
        except OSError:
            return False

    def _execute_run(self, request: CreateRunRequest, run_id: str, host_workdir: str) -> None:
        with self._slots:
            self._execute_run_locked(request, run_id, host_workdir)

    def _execute_run_locked(self, request: CreateRunRequest, run_id: str, host_workdir: str) -> None:
        prepared = self._service.prepare_execution(request, host_workdir)
        self._store.transition_run(run_id, status="starting")
        self._store.append_event(
            run_id,
            "run_started",
            {"executor": request.executor, "command": prepared.command[:8]},
        )
        before = _snapshot_tree(Path(host_workdir))
        start = time.monotonic()

        env = self._build_env(run_id, request, host_workdir)
        process: subprocess.Popen[str] | None = None
        stdout = ""
        stderr = ""
        exit_code = None
        timed_out = False

        try:
            process = subprocess.Popen(
                prepared.command,
                cwd=host_workdir,
                stdin=subprocess.PIPE if prepared.stdin_text is not None else subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
            )
            with self._lock:
                self._processes[run_id] = process
            self._store.transition_run(run_id, status="running")
            stdout, stderr = process.communicate(
                input=prepared.stdin_text,
                timeout=request.timeout_seconds or self._config.runtime.default_timeout_seconds,
            )
            exit_code = process.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
            if process is not None:
                process.terminate()
                try:
                    stdout, stderr = process.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    stdout, stderr = process.communicate()
                exit_code = process.returncode
        except Exception as exc:
            stderr = f"{type(exc).__name__}: {exc}"
        finally:
            with self._lock:
                self._processes.pop(run_id, None)

        after = _snapshot_tree(Path(host_workdir))
        changed = _changed_files(before, after)
        outcome = self._service.parse_execution_result(
            request.executor,
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            timed_out=timed_out,
        )
        duration_ms = int((time.monotonic() - start) * 1000)
        final_status = outcome.normalized_status

        self._store.append_event(
            run_id,
            "normalized_status",
            {"status": outcome.normalized_status, "pause_reason": outcome.pause_reason},
        )
        self._store.append_event(
            run_id,
            "run_finished",
            {"exit_code": exit_code, "changed_files": changed, "duration_ms": duration_ms},
        )
        self._store.complete_run(
            run_id,
            status=final_status,
            normalized_status=outcome.normalized_status,
            requires_owner_action=outcome.requires_owner_action,
            pause_reason=outcome.pause_reason,
            exit_code=exit_code,
            changed_files=changed,
            duration_ms=duration_ms,
            stdout_tail=outcome.stdout_tail,
            stderr_tail=outcome.stderr_tail,
            usage_update=outcome.usage_update,
        )

    def _build_env(
        self,
        run_id: str,
        request: CreateRunRequest,
        host_workdir: str,
    ) -> dict[str, str]:
        env = {
            key: value
            for key, value in os.environ.items()
            if key in {"HOME", "PATH", "LANG", "LC_ALL", "SHELL", "TMPDIR"}
        }
        env.update(
            {
                "PRAETOR_RUN_ID": run_id,
                "PRAETOR_MISSION_ID": request.mission_id,
                "PRAETOR_TASK_ID": request.task_id,
                "PRAETOR_EXECUTOR": request.executor,
                "PRAETOR_HOST_WORKDIR": host_workdir,
            }
        )
        return env
