import json
import os
import pathlib
import signal
import subprocess
import sys
import time
import http.cookiejar
import urllib.error
import urllib.parse
import urllib.request


ROOT = pathlib.Path(__file__).resolve().parents[1]
STATE_DIR = pathlib.Path("/tmp/praetor-app-api-smoke-state")
PORT = 9743
BASE_URL = f"http://127.0.0.1:{PORT}"
FAKE_OPENAI_URL = "http://127.0.0.1:9760/v1"
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


def post_form(path: str, payload: dict) -> tuple[int, str]:
    data = urllib.parse.urlencode(payload).encode()
    req = urllib.request.Request(
        BASE_URL + path,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with OPENER.open(req, timeout=30) as resp:
            return resp.status, resp.geturl()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.geturl()


def wait_for(url: str) -> None:
    for _ in range(50):
        try:
            with urllib.request.urlopen(url, timeout=5):
                return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError(f"server did not become ready: {url}")


def main() -> int:
    global CSRF_TOKEN
    if STATE_DIR.exists():
        subprocess.run(["rm", "-rf", str(STATE_DIR)], check=True)
    fake_proc = subprocess.Popen(
        [sys.executable, str(ROOT / "tools" / "fake_openai_server.py")],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    env = os.environ.copy()
    env["PRAETOR_STATE_DIR"] = str(STATE_DIR)
    env["OPENAI_API_KEY"] = "fake-key"
    env["PRAETOR_OPENAI_BASE_URL"] = FAKE_OPENAI_URL
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
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        wait_for("http://127.0.0.1:9760")
        wait_for(f"{BASE_URL}/health")
        workspace_root = "/tmp/praetor-api-mode-workspace"
        onboarding = request(
            "POST",
            "/onboarding/complete",
            {
                "owner_name": "Jove",
                "owner_email": "jove@example.com",
                "owner_password": "praetor-api-password",
                "language": "en",
                "leadership_style": "strategic",
                "decision_style": "balanced",
                "organization_style": "lean",
                "autonomy_mode": "hybrid",
                "risk_priority": "avoid_wrong_decisions",
                "workspace_root": workspace_root,
                "runtime": {
                    "mode": "api",
                    "provider": "openai",
                    "model": "fake-gpt",
                },
                "require_approval": ["delete_files", "shell_commands"],
            },
        )
        CSRF_TOKEN = request("GET", "/auth/session")["data"]["csrf_token"]
        test_status, test_url = post_form(
            "/app/settings/runtime/test",
            {
                "csrf_token": CSRF_TOKEN,
                "next_path": "/app/models",
                "runtime_mode": "api",
                "runtime_provider": "openai",
                "runtime_model": "fake-gpt",
                "runtime_base_url": FAKE_OPENAI_URL,
                "runtime_executor": "codex",
                "api_key": "fake-key",
            },
        )
        mission = request(
            "POST",
            "/missions",
            {
                "title": "API Mode Project",
                "summary": "Generate a project file through API mode.",
                "domains": ["operations"],
                "priority": "high",
                "requested_outputs": ["/workspace/Projects/API_Mode_Project/PROJECT.md"],
            },
        )
        mission_id = mission["data"]["id"]
        run_result = request("POST", f"/missions/{mission_id}/run")
        mission_detail = request("GET", f"/missions/{mission_id}")
        output_path = pathlib.Path(workspace_root) / "Projects" / "API_Mode_Project" / "PROJECT.md"
        decisions_path = pathlib.Path(workspace_root) / "Missions" / mission_id / "DECISIONS.md"
        print(
            json.dumps(
                {
                    "onboarding_ok": onboarding["ok"],
                    "connection_test_redirected": test_status == 200 and "flash=Connection" in test_url,
                    "mission_status": mission_detail["data"]["status"],
                    "task_status": run_result["data"]["task"]["status"],
                    "run_executor": run_result["data"]["bridge_run"]["executor"],
                    "input_tokens": run_result["data"]["bridge_run"]["usage"]["input_tokens"],
                    "output_exists": output_path.exists(),
                    "decisions_exists": decisions_path.exists(),
                },
                ensure_ascii=True,
            )
        )
        return 0
    finally:
        for proc in [app_proc, fake_proc]:
            if proc.poll() is None:
                proc.send_signal(signal.SIGINT)
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
