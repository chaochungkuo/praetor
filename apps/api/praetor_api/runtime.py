from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
import sys

from .config import (
    get_anthropic_api_key,
    get_bridge_base_url,
    get_bridge_token,
    get_openai_api_key,
)
from .models import MissionDefinition, RunRecord, RuntimeSelection, TaskDefinition, WorkspacePermissions, generate_id
from .providers import ApiProviderError, run_api_mission
from .safety_policy import append_safety_policy


ROOT = Path(__file__).resolve().parents[3]
WORKER_RUNTIME_PATH = ROOT / "workers" / "runtime"
if str(WORKER_RUNTIME_PATH) not in sys.path:
    sys.path.insert(0, str(WORKER_RUNTIME_PATH))

from praetor_runtime import BridgeClient  # noqa: E402


@dataclass
class MissionRuntimeResult:
    task: TaskDefinition
    run_record: RunRecord


class MissionRuntime:
    def __init__(self) -> None:
        self.base_url = get_bridge_base_url()
        self.token = get_bridge_token()

    def probe(self, runtime: RuntimeSelection | None = None) -> dict:
        runtime = runtime or RuntimeSelection()
        payload = {
            "mode": runtime.mode,
            "configured": False,
            "healthy": False,
            "bridge_url": self.base_url,
            "executors": [],
            "error": None,
        }
        if runtime.mode == "subscription_executor":
            if not (self.base_url and self.token):
                payload["error"] = "Bridge runtime is not configured."
                return payload
            client = BridgeClient(base_url=self.base_url or "", token=self.token or "")
            try:
                health = client.health()
                executors = client.executors().get("executors", [])
                payload.update(
                    {
                        "configured": True,
                        "healthy": True,
                        "health": health,
                        "executors": executors,
                    }
                )
                return payload
            except Exception as exc:
                payload.update({"configured": True, "error": str(exc)})
                return payload
        if runtime.mode == "api":
            provider = runtime.provider or "openai"
            key_present = bool(get_openai_api_key()) if provider in {"openai", "openai_compatible"} else bool(get_anthropic_api_key())
            payload.update(
                {
                    "configured": key_present,
                    "healthy": key_present,
                    "executors": [
                        {
                            "id": provider,
                            "model": runtime.model,
                            "enabled": key_present,
                            "binary_found": key_present,
                            "login_state": "authenticated" if key_present else "not_detected",
                            "supports_noninteractive_batch": True,
                            "supports_cancel": False,
                        }
                    ],
                    "error": None if key_present else f"{provider} API key is not configured.",
                }
            )
            return payload
        payload["error"] = f"Unsupported runtime mode: {runtime.mode}"
        return payload

    def run_mission(
        self,
        *,
        workspace_root: Path,
        mission: MissionDefinition,
        runtime: RuntimeSelection,
        permissions: WorkspacePermissions,
        safety_policy: str | None = None,
        target_workdir: Path | None = None,
    ) -> MissionRuntimeResult:
        if runtime.mode == "subscription_executor":
            return self._run_subscription_executor(
                workspace_root=workspace_root,
                mission=mission,
                executor=runtime.executor or "codex",
                safety_policy=safety_policy,
                target_workdir=target_workdir,
            )
        if runtime.mode == "api":
            return self._run_api_mode(
                workspace_root=workspace_root,
                mission=mission,
                runtime=runtime,
                permissions=permissions,
                safety_policy=safety_policy,
                target_workdir=target_workdir,
            )
        raise RuntimeError(f"Unsupported runtime mode: {runtime.mode}")

    def _run_subscription_executor(
        self,
        *,
        workspace_root: Path,
        mission: MissionDefinition,
        executor: str,
        safety_policy: str | None = None,
        target_workdir: Path | None = None,
    ) -> MissionRuntimeResult:
        if not (self.base_url and self.token):
            raise RuntimeError("Bridge runtime is not configured.")

        task = TaskDefinition(
            id=generate_id("task"),
            mission_id=mission.id,
            title=mission.title,
            role_owner="role_project_execution",
            current_executor=executor,
            status="running",
            outputs=mission.requested_outputs,
        )
        client = BridgeClient(base_url=self.base_url or "", token=self.token or "")
        target_workdir = target_workdir or self._target_workdir(mission, workspace_root)
        target_workdir.mkdir(parents=True, exist_ok=True)
        payload = {
            "request_id": generate_id("req"),
            "mission_id": mission.id,
            "task_id": task.id,
            "executor": executor,
            "timeout_seconds": mission.run_budget.max_time_minutes * 60,
            "path_mapping": {
                "container_workspace_root": "/app/workspace",
                "host_workspace_root": str(workspace_root),
                "target_workdir": self._container_target_workdir(target_workdir, workspace_root),
            },
            "task_spec": {
                "title": task.title,
                "instructions": append_safety_policy(
                    mission.summary or f"Complete mission: {mission.title}",
                    safety_policy,
                ),
                "input_files": [],
                "expected_outputs": mission.requested_outputs,
                "approval_policy": {
                    "allow_destructive_write": False,
                    "allow_shell": False,
                },
            },
        }
        created = client.create_run(payload)
        final_run = client.wait_for_terminal(
            created["run_id"],
            poll_interval_seconds=1.0,
            timeout_seconds=mission.run_budget.max_time_minutes * 60,
        )
        task.status = self._task_status_from_bridge(final_run.get("normalized_status"))
        run_record = RunRecord.model_validate(final_run)
        return MissionRuntimeResult(task=task, run_record=run_record)

    def _run_api_mode(
        self,
        *,
        workspace_root: Path,
        mission: MissionDefinition,
        runtime: RuntimeSelection,
        permissions: WorkspacePermissions,
        safety_policy: str | None = None,
        target_workdir: Path | None = None,
    ) -> MissionRuntimeResult:
        provider = runtime.provider or "openai"
        model = runtime.model or ("gpt-4.1-mini" if provider == "openai" else "claude-3-5-sonnet-latest")
        task = TaskDefinition(
            id=generate_id("task"),
            mission_id=mission.id,
            title=mission.title,
            role_owner="role_project_execution",
            current_executor=f"{provider}:{model}",
            status="running",
            outputs=mission.requested_outputs,
        )
        try:
            payload, result = run_api_mission(
                mission=mission,
                workspace_root=target_workdir or workspace_root,
                provider=provider,
                model=model,
                base_url=runtime.base_url,
                safety_policy=safety_policy,
            )
        except ApiProviderError as exc:
            failed = RunRecord(
                run_id=generate_id("run"),
                request_id=generate_id("req"),
                mission_id=mission.id,
                task_id=task.id,
                executor=f"{provider}:{model}",
                status="failed_permanent",
                normalized_status="failed_permanent",
                requires_owner_action=True,
                pause_reason=str(exc),
                host_workdir=str(workspace_root),
                stderr_tail=str(exc),
            )
            task.status = "failed"
            return MissionRuntimeResult(task=task, run_record=failed)

        files = payload.get("files") or []
        changed_files: list[str] = []
        decision_notes = payload.get("decisions") or []
        for item in files:
            rel, host_path = self._resolve_write_target(
                raw_path=item.get("path", ""),
                workspace_root=workspace_root,
                permissions=permissions,
            )
            host_path.parent.mkdir(parents=True, exist_ok=True)
            _write_private_workspace_file(host_path, str(item.get("content", "")))
            changed_files.append(rel)

        if decision_notes:
            decisions_path = workspace_root / "Missions" / mission.id / "DECISIONS.md"
            existing = decisions_path.read_text(encoding="utf-8") if decisions_path.exists() else "# Decisions\n\n"
            appended = "\n".join(f"- {note}" for note in decision_notes)
            _write_private_workspace_file(decisions_path, existing.rstrip() + "\n\n" + appended + "\n")
            changed_files.append(str(decisions_path.relative_to(workspace_root)))

        result.run_record.changed_files = changed_files
        result.run_record.task_id = task.id
        task.status = "done" if result.run_record.normalized_status == "completed" else "failed"
        return MissionRuntimeResult(task=task, run_record=result.run_record)

    @staticmethod
    def _target_workdir(mission: MissionDefinition, workspace_root: Path) -> Path:
        slug = re.sub(r"[^A-Za-z0-9._-]+", "_", mission.title.strip()).strip("._-")
        if not slug:
            slug = mission.id
        return workspace_root / "Projects" / slug

    @staticmethod
    def _container_target_workdir(host_workdir: Path, workspace_root: Path) -> str:
        rel = host_workdir.resolve().relative_to(workspace_root.resolve())
        return f"/app/workspace/{rel.as_posix()}"

    @staticmethod
    def _task_status_from_bridge(normalized_status: str | None) -> str:
        if normalized_status == "completed":
            return "done"
        if normalized_status in {"paused_budget", "paused_decision", "paused_risk", "interactive_approval_required"}:
            return "waiting_approval"
        return "failed"

    @staticmethod
    def _resolve_write_target(
        *,
        raw_path: str,
        workspace_root: Path,
        permissions: WorkspacePermissions,
    ) -> tuple[str, Path]:
        if raw_path.startswith("/workspace/"):
            relative = raw_path[len("/workspace/") :]
        elif raw_path.startswith("/app/workspace/"):
            relative = raw_path[len("/app/workspace/") :]
        else:
            relative = raw_path.lstrip("/")
        host_path = (workspace_root / relative).resolve()
        MissionRuntime._ensure_writable(host_path, permissions)
        return relative, host_path

    @staticmethod
    def _ensure_writable(path: Path, permissions: WorkspacePermissions) -> None:
        allow_roots = [Path(item).expanduser().resolve() for item in permissions.allow_write]
        deny_roots = [Path(item).expanduser().resolve() for item in permissions.deny_write]
        resolved = path.resolve()
        if allow_roots and not any(_is_relative_to(resolved, root) for root in allow_roots):
            raise RuntimeError(f"Write blocked outside allowlist: {resolved}")
        if any(_is_relative_to(resolved, root) for root in deny_roots):
            raise RuntimeError(f"Write blocked by denylist: {resolved}")


def _is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False


def _write_private_workspace_file(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
