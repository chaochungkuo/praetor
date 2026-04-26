from __future__ import annotations

import os
from pathlib import Path


DEFAULT_STATE_DIR_ENV = "PRAETOR_STATE_DIR"
DEFAULT_APP_ROOT = Path("/tmp/praetor-app-state")
BRIDGE_BASE_URL_ENV = "PRAETOR_BRIDGE_BASE_URL"
BRIDGE_TOKEN_ENV = "PRAETOR_BRIDGE_TOKEN"
OPENAI_API_KEY_ENV = "OPENAI_API_KEY"
ANTHROPIC_API_KEY_ENV = "ANTHROPIC_API_KEY"
OPENAI_BASE_URL_ENV = "PRAETOR_OPENAI_BASE_URL"
ANTHROPIC_BASE_URL_ENV = "PRAETOR_ANTHROPIC_BASE_URL"
SESSION_SECRET_ENV = "PRAETOR_SESSION_SECRET"
SESSION_MAX_AGE_ENV = "PRAETOR_SESSION_MAX_AGE_SECONDS"
SECURE_COOKIE_ENV = "PRAETOR_SECURE_COOKIE"
REQUIRE_LOGIN_ENV = "PRAETOR_REQUIRE_LOGIN"
ENV_ENV = "PRAETOR_ENV"
SETUP_TOKEN_ENV = "PRAETOR_SETUP_TOKEN"
DEBUG_ROUTES_ENV = "PRAETOR_DEBUG_ROUTES"
RATE_LIMIT_ENABLED_ENV = "PRAETOR_RATE_LIMIT_ENABLED"
LOGIN_MAX_ATTEMPTS_ENV = "PRAETOR_LOGIN_MAX_ATTEMPTS"
LOGIN_WINDOW_SECONDS_ENV = "PRAETOR_LOGIN_WINDOW_SECONDS"
CEO_PLANNER_MODE_ENV = "PRAETOR_CEO_PLANNER_MODE"
CEO_PLANNER_PROVIDER_ENV = "PRAETOR_CEO_PLANNER_PROVIDER"
CEO_PLANNER_MODEL_ENV = "PRAETOR_CEO_PLANNER_MODEL"
OPENAI_STATE_SECRET = "openai_api_key.txt"
ANTHROPIC_STATE_SECRET = "anthropic_api_key.txt"


def get_state_dir() -> Path:
    value = os.getenv(DEFAULT_STATE_DIR_ENV)
    path = Path(value).expanduser() if value else DEFAULT_APP_ROOT
    path.mkdir(parents=True, exist_ok=True)
    return path


def _get_env_or_file(name: str, default: str | None = None) -> str | None:
    direct = os.getenv(name)
    if direct:
        return direct
    file_path = os.getenv(f"{name}_FILE")
    if file_path:
        path = Path(file_path).expanduser()
        if path.exists():
            return path.read_text(encoding="utf-8").strip()
    return default


def _get_state_secret(filename: str) -> str | None:
    path = get_state_dir() / "secrets" / filename
    if not path.exists():
        return None
    value = path.read_text(encoding="utf-8").strip()
    return value or None


def get_bridge_base_url() -> str | None:
    return os.getenv(BRIDGE_BASE_URL_ENV)


def get_bridge_token() -> str | None:
    return _get_env_or_file(BRIDGE_TOKEN_ENV)


def get_openai_api_key() -> str | None:
    return _get_env_or_file(OPENAI_API_KEY_ENV) or _get_state_secret(OPENAI_STATE_SECRET)


def get_anthropic_api_key() -> str | None:
    return _get_env_or_file(ANTHROPIC_API_KEY_ENV) or _get_state_secret(ANTHROPIC_STATE_SECRET)


def get_openai_base_url() -> str:
    return os.getenv(OPENAI_BASE_URL_ENV, "https://api.openai.com/v1")


def get_anthropic_base_url() -> str:
    return os.getenv(ANTHROPIC_BASE_URL_ENV, "https://api.anthropic.com/v1")


def get_session_secret() -> str:
    return _get_env_or_file(SESSION_SECRET_ENV, "praetor-dev-session-secret") or "praetor-dev-session-secret"


def get_session_max_age_seconds() -> int:
    value = os.getenv(SESSION_MAX_AGE_ENV, "43200")
    return int(value)


def get_secure_cookie() -> bool:
    return os.getenv(SECURE_COOKIE_ENV, "false").lower() in {"1", "true", "yes", "on"}


def get_require_login() -> bool:
    return os.getenv(REQUIRE_LOGIN_ENV, "true").lower() in {"1", "true", "yes", "on"}


def get_env_name() -> str:
    return os.getenv(ENV_ENV, "local").lower()


def is_production() -> bool:
    return get_env_name() in {"prod", "production"}


def get_setup_token() -> str | None:
    return _get_env_or_file(SETUP_TOKEN_ENV)


def get_debug_routes_enabled() -> bool:
    default = "false" if is_production() else "true"
    return os.getenv(DEBUG_ROUTES_ENV, default).lower() in {"1", "true", "yes", "on"}


def get_rate_limit_enabled() -> bool:
    default = "true" if is_production() else "false"
    return os.getenv(RATE_LIMIT_ENABLED_ENV, default).lower() in {"1", "true", "yes", "on"}


def get_login_max_attempts() -> int:
    return int(os.getenv(LOGIN_MAX_ATTEMPTS_ENV, "5"))


def get_login_window_seconds() -> int:
    return int(os.getenv(LOGIN_WINDOW_SECONDS_ENV, "300"))


def get_ceo_planner_mode() -> str:
    return os.getenv(CEO_PLANNER_MODE_ENV, "auto").lower()


def get_ceo_planner_provider() -> str:
    return os.getenv(CEO_PLANNER_PROVIDER_ENV, "openai").lower()


def get_ceo_planner_model() -> str:
    return os.getenv(CEO_PLANNER_MODEL_ENV, "gpt-4.1-mini")
