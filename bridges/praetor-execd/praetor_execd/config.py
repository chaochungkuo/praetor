from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, model_validator


def _resolve_env_value(value: str) -> str:
    if value.startswith("env:"):
        env_name = value.split(":", 1)[1]
        resolved = os.getenv(env_name)
        if not resolved:
            raise ValueError(f"Missing environment variable: {env_name}")
        return resolved
    return value


class ServerConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 9417
    auth_token: str

    @model_validator(mode="after")
    def resolve_auth_token(self) -> "ServerConfig":
        self.auth_token = _resolve_env_value(self.auth_token)
        if self.auth_token in {"", "change-me", "change-this", "test-token"} or len(self.auth_token) < 16:
            raise ValueError("Executor bridge auth_token must be a strong random value.")
        return self


class PathsConfig(BaseModel):
    host_workspace_root: str
    allowed_roots: list[str] = Field(default_factory=list)
    deny_roots: list[str] = Field(default_factory=list)


class ExecutorConfig(BaseModel):
    enabled: bool = True
    command: str
    args: list[str] = Field(default_factory=list)
    healthcheck: list[str] = Field(default_factory=list)
    requires_login: bool = True
    supports_noninteractive_batch: bool = True
    supports_cancel: bool = True


class RuntimeConfig(BaseModel):
    max_concurrent_runs: int = 2
    default_timeout_seconds: int = 1800
    max_event_buffer: int = 5000
    persist_run_logs: bool = True
    log_dir: str


class AppConfig(BaseModel):
    server: ServerConfig
    paths: PathsConfig
    executors: dict[str, ExecutorConfig]
    runtime: RuntimeConfig


DEFAULT_CONFIG_ENV = "PRAETOR_EXECD_CONFIG"


def load_config(config_path: str | None = None) -> AppConfig:
    candidate = config_path or os.getenv(DEFAULT_CONFIG_ENV)
    if not candidate:
        raise RuntimeError(
            "No config path provided. Set PRAETOR_EXECD_CONFIG or pass config_path."
        )
    path = Path(candidate).expanduser()
    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return AppConfig.model_validate(raw)
