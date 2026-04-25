import json
import os
import pathlib
import signal
import subprocess
import sys
import time
import http.cookiejar
import urllib.request


ROOT = pathlib.Path(__file__).resolve().parents[1]
STATE_DIR = pathlib.Path("/tmp/praetor-app-fallback-state")
TEST_ROOT = pathlib.Path("/tmp/praetor-app-fallback-runtime")
PORT = 9744
BASE_URL = f"http://127.0.0.1:{PORT}"
BRIDGE_PORT = 9419
BRIDGE_URL = f"http://127.0.0.1:{BRIDGE_PORT}"
BRIDGE_TOKEN = "fallback-token-for-local-security-tests"
COOKIE_JAR = http.cookiejar.CookieJar()
OPENER = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(COOKIE_JAR))
CSRF_TOKEN = None


def request(method: str, path: str, payload: dict | None = None) -> dict:
    global CSRF_TOKEN
    headers = {"Content-Type": "application/json"}
    if CSRF_TOKEN and method.upper() not in {"GET", "HEAD", "OPTIONS"}:
        headers["X-CSRF-Token"] = CSRF_TOKEN
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(BASE_URL + path, data=data, headers=headers, method=method)
    with OPENER.open(req, timeout=30) as resp:
        return json.load(resp)


def wait_for(url: str, headers: dict | None = None) -> None:
    headers = headers or {}
    for _ in range(50):
        try:
            req = urllib.request.Request(url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=10):
                return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError(f"server did not become ready: {url}")


def write_bridge_config(workspace_root: pathlib.Path) -> pathlib.Path:
    config_dir = TEST_ROOT / "bridge"
    log_dir = TEST_ROOT / "logs"
    config_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "config.yaml"
    config_path.write_text(
        "\n".join(
            [
                "server:",
                "  host: 127.0.0.1",
                f"  port: {BRIDGE_PORT}",
                "  auth_token: env:PRAETOR_EXECUTOR_BRIDGE_TOKEN",
                "paths:",
                f"  host_workspace_root: {workspace_root}",
                "  allowed_roots:",
                f"    - {workspace_root}",
                "  deny_roots:",
                f"    - {workspace_root / 'Archive'}",
                "executors:",
                "  codex:",
                "    enabled: true",
                f"    command: {sys.executable}",
                "    args:",
                f"      - {ROOT / 'bridges' / 'praetor-execd' / 'dev' / 'mock_executor.py'}",
                "    healthcheck: []",
                "    requires_login: false",
                "    supports_noninteractive_batch: true",
                "    supports_cancel: true",
                "runtime:",
                "  max_concurrent_runs: 2",
                "  default_timeout_seconds: 30",
                "  max_event_buffer: 5000",
                "  persist_run_logs: true",
                f"  log_dir: {log_dir}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return config_path


def main() -> int:
    global CSRF_TOKEN
    for path in [STATE_DIR, TEST_ROOT]:
        if path.exists():
            subprocess.run(["rm", "-rf", str(path)], check=True)
    workspace_root = TEST_ROOT / "workspace"
    bridge_config = write_bridge_config(workspace_root)

    bridge_env = os.environ.copy()
    bridge_env["PRAETOR_EXECD_CONFIG"] = str(bridge_config)
    bridge_env["PRAETOR_EXECUTOR_BRIDGE_TOKEN"] = BRIDGE_TOKEN
    bridge_proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "--app-dir",
            str(ROOT / "bridges" / "praetor-execd"),
            "praetor_execd.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(BRIDGE_PORT),
        ],
        env=bridge_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    app_env = os.environ.copy()
    app_env["PRAETOR_STATE_DIR"] = str(STATE_DIR)
    app_env["PRAETOR_BRIDGE_BASE_URL"] = BRIDGE_URL
    app_env["PRAETOR_BRIDGE_TOKEN"] = BRIDGE_TOKEN
    app_env.pop("OPENAI_API_KEY", None)
    app_proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "--app-dir",
            str(ROOT / "apps" / "api"),
            "praetor_api.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(PORT),
        ],
        env=app_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    try:
        wait_for(f"{BRIDGE_URL}/health", headers={"Authorization": f"Bearer {BRIDGE_TOKEN}"})
        wait_for(f"{BASE_URL}/health")
        onboarding = request(
            "POST",
            "/onboarding/complete",
            {
                "owner_name": "Jove",
                "owner_email": "jove@example.com",
                "owner_password": "praetor-fallback-password",
                "language": "en",
                "leadership_style": "strategic",
                "decision_style": "balanced",
                "organization_style": "lean",
                "autonomy_mode": "hybrid",
                "risk_priority": "avoid_wrong_decisions",
                "workspace_root": str(workspace_root),
                "runtime": {
                    "mode": "api",
                    "provider": "openai",
                    "model": "missing-key-model",
                    "executor": "codex",
                },
                "require_approval": ["delete_files", "shell_commands"],
            },
        )
        CSRF_TOKEN = request("GET", "/auth/session")["data"]["csrf_token"]
        mission = request(
            "POST",
            "/missions",
            {
                "title": "Fallback Mission",
                "summary": "Fallback to subscription executor when API mode fails.",
                "domains": ["operations"],
                "priority": "high",
                "requested_outputs": ["/workspace/Projects/Fallback_Mission/PROJECT.md"],
            },
        )
        mission_id = mission["data"]["id"]
        run_result = request("POST", f"/missions/{mission_id}/run")
        runs = request("GET", f"/missions/{mission_id}")["data"]
        output_path = workspace_root / "Projects" / "Fallback_Mission" / "mock-executor-output.txt"
        print(
            json.dumps(
                {
                    "onboarding_ok": onboarding["ok"],
                    "mission_status": runs["status"],
                    "task_status": run_result["data"]["task"]["status"],
                    "run_executor": run_result["data"]["bridge_run"]["executor"],
                    "output_exists": output_path.exists(),
                },
                ensure_ascii=True,
            )
        )
        return 0
    finally:
        for proc in [app_proc, bridge_proc]:
            if proc.poll() is None:
                proc.send_signal(signal.SIGINT)
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
