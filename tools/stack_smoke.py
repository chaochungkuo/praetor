import http.cookiejar
import json
import os
import pathlib
import signal
import subprocess
import sys
import time
import urllib.request


ROOT = pathlib.Path(__file__).resolve().parents[1]
STATE_DIR = pathlib.Path("/tmp/praetor-stack-state")
API_PORT = 9751
WEB_PORT = 9752
WORKER_PORT = 9753
API_BASE_URL = f"http://127.0.0.1:{API_PORT}"
WEB_BASE_URL = f"http://127.0.0.1:{WEB_PORT}"
WORKER_BASE_URL = f"http://127.0.0.1:{WORKER_PORT}"

COOKIE_JAR = http.cookiejar.CookieJar()
OPENER = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(COOKIE_JAR))
CSRF_TOKEN = None


def get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.load(resp)


def request_web(method: str, path: str, payload: dict | None = None) -> tuple[int, dict]:
    global CSRF_TOKEN
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if CSRF_TOKEN and method.upper() not in {"GET", "HEAD", "OPTIONS"}:
        headers["X-CSRF-Token"] = CSRF_TOKEN
    req = urllib.request.Request(
        WEB_BASE_URL + path,
        data=data,
        headers=headers,
        method=method,
    )
    with OPENER.open(req, timeout=30) as resp:
        return resp.status, json.load(resp)


def wait_for(url: str) -> None:
    for _ in range(60):
        try:
            with urllib.request.urlopen(url, timeout=5):
                return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError(f"service did not become ready: {url}")


def main() -> int:
    global CSRF_TOKEN
    if STATE_DIR.exists():
        subprocess.run(["rm", "-rf", str(STATE_DIR)], check=True)
    env = os.environ.copy()
    env["PRAETOR_STATE_DIR"] = str(STATE_DIR)

    api_proc = subprocess.Popen(
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
            str(API_PORT),
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    worker_env = env.copy()
    worker_env["PRAETOR_API_BASE_URL"] = API_BASE_URL
    worker_proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "--app-dir",
            str(ROOT / "apps" / "worker"),
            "praetor_worker.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(WORKER_PORT),
        ],
        env=worker_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    web_env = env.copy()
    web_env["PRAETOR_WEB_UPSTREAM"] = API_BASE_URL
    web_proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "--app-dir",
            str(ROOT / "apps" / "web"),
            "praetor_web.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(WEB_PORT),
        ],
        env=web_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    try:
        wait_for(f"{API_BASE_URL}/health")
        wait_for(f"{WORKER_BASE_URL}/health")
        wait_for(f"{WEB_BASE_URL}/health")
        request_web(
            "POST",
            "/onboarding/complete",
            {
                "owner_name": "Jove",
                "owner_email": "jove@example.com",
                "owner_password": "praetor-stack-password",
                "language": "en",
                "leadership_style": "strategic",
                "decision_style": "balanced",
                "organization_style": "lean",
                "autonomy_mode": "hybrid",
                "risk_priority": "avoid_wrong_decisions",
                "workspace_root": "/tmp/praetor-stack-workspace",
                "runtime": {"mode": "subscription_executor", "executor": "codex"},
                "require_approval": ["delete_files", "shell_commands"],
            },
        )
        _, session = request_web("GET", "/auth/session")
        CSRF_TOKEN = session["data"]["csrf_token"]
        mission_status, mission = request_web(
            "POST",
            "/missions",
            {
                "title": "Stack Smoke Mission",
                "summary": "Verify web -> api -> worker stack shape.",
                "domains": ["operations"],
                "priority": "high",
                "requested_outputs": ["/workspace/Projects/Stack/PROJECT.md"],
            },
        )
        web_health = get_json(f"{WEB_BASE_URL}/health")
        worker_health = get_json(f"{WORKER_BASE_URL}/health")
        print(
            json.dumps(
                {
                    "web_status": web_health["status"],
                    "web_upstream_health": web_health["upstream_health"],
                    "worker_status": worker_health["status"],
                    "worker_api_health": worker_health["api_health"],
                    "mission_create_status": mission_status,
                    "mission_id_present": bool(mission.get("data", {}).get("id")),
                },
                ensure_ascii=True,
            )
        )
        return 0
    finally:
        for proc in [web_proc, worker_proc, api_proc]:
            if proc.poll() is None:
                proc.send_signal(signal.SIGINT)
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
