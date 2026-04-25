from __future__ import annotations

import os
import subprocess
import shutil
from pathlib import Path

from .config import AppConfig, ExecutorConfig
from .executor_plugins import PreparedExecution, get_runner
from .models import CreateRunRequest, ExecutorSummary


class BridgeService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def executor_summaries(self) -> list[ExecutorSummary]:
        items: list[ExecutorSummary] = []
        for name, cfg in self.config.executors.items():
            binary_found = shutil.which(cfg.command) is not None
            health_ok, _ = self.probe_executor(name, cfg)
            login_state = "authenticated" if binary_found and health_ok and cfg.requires_login else "unknown"
            if not binary_found:
                login_state = "not_detected"
            items.append(
                ExecutorSummary(
                    name=name,  # type: ignore[arg-type]
                    enabled=cfg.enabled,
                    binary_found=binary_found,
                    login_state=login_state,  # type: ignore[arg-type]
                    supports_noninteractive_batch=cfg.supports_noninteractive_batch,
                    supports_cancel=cfg.supports_cancel,
                )
            )
        return items

    def validate_executor(self, executor_name: str) -> ExecutorConfig:
        cfg = self.config.executors.get(executor_name)
        if cfg is None or not cfg.enabled:
            raise ValueError(f"Executor not available: {executor_name}")
        if shutil.which(cfg.command) is None:
            raise ValueError(f"Executor binary not found: {cfg.command}")
        health_ok, health_message = self.probe_executor(executor_name, cfg)
        if not health_ok:
            raise ValueError(f"Executor healthcheck failed: {health_message}")
        return cfg

    def prepare_execution(
        self,
        request: CreateRunRequest,
        host_workdir: str,
    ) -> PreparedExecution:
        cfg = self.validate_executor(request.executor)
        return get_runner(request.executor).prepare(cfg, request, host_workdir)

    def parse_execution_result(
        self,
        executor_name: str,
        *,
        stdout: str,
        stderr: str,
        exit_code: int | None,
        timed_out: bool,
    ):
        return get_runner(executor_name).parse_result(
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            timed_out=timed_out,
        )

    def probe_executor(self, executor_name: str, cfg: ExecutorConfig) -> tuple[bool, str | None]:
        if cfg.healthcheck == []:
            return True, None
        command = cfg.healthcheck or get_runner(executor_name).default_healthcheck(cfg)
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=10,
                env={
                    "PATH": os.environ.get("PATH", ""),
                    "HOME": os.environ.get("HOME", ""),
                },
            )
        except Exception as exc:
            return False, f"{type(exc).__name__}: {exc}"
        if completed.returncode == 0:
            return True, None
        message = (completed.stderr or completed.stdout or f"exit code {completed.returncode}").strip()
        return False, message or f"exit code {completed.returncode}"

    def map_target_workdir(self, request: CreateRunRequest) -> str:
        mapping = request.path_mapping
        if mapping.host_workspace_root != self.config.paths.host_workspace_root:
            raise PermissionError("host_workspace_root mismatch.")
        if not mapping.target_workdir.startswith(mapping.container_workspace_root):
            raise PermissionError("target_workdir is outside container workspace root.")
        suffix = mapping.target_workdir[len(mapping.container_workspace_root) :].lstrip("/")
        host_path = Path(mapping.host_workspace_root).joinpath(suffix).resolve(strict=False)
        self._assert_allowed_path(host_path)
        return str(host_path)

    def _assert_allowed_path(self, host_path: Path) -> None:
        allowed = [Path(p).resolve(strict=False) for p in self.config.paths.allowed_roots]
        denied = [Path(p).resolve(strict=False) for p in self.config.paths.deny_roots]

        if not any(self._is_within(host_path, base) for base in allowed):
            raise PermissionError("Target path is outside allowed roots.")
        if any(self._is_within(host_path, base) for base in denied):
            raise PermissionError("Target path is inside denied roots.")

    @staticmethod
    def _is_within(candidate: Path, base: Path) -> bool:
        try:
            candidate.relative_to(base)
            return True
        except ValueError:
            return False
