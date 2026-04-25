import http.cookiejar
import json
import os
import pathlib
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request


ROOT = pathlib.Path(__file__).resolve().parents[1]
STATE_DIR = pathlib.Path("/tmp/praetor-office-smoke-state")
WORKSPACE_DIR = pathlib.Path("/tmp/praetor-office-smoke-workspace")
API_PORT = 9751
WEB_PORT = 9752
API_BASE = f"http://127.0.0.1:{API_PORT}"
WEB_BASE = f"http://127.0.0.1:{WEB_PORT}"
SETUP_TOKEN = "setup-token-for-office-smoke"
COOKIE_JAR = http.cookiejar.CookieJar()
OPENER = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(COOKIE_JAR))
CSRF_TOKEN = None


def request(method: str, path: str, payload: dict | None = None, *, csrf: bool = True, setup: bool = False) -> tuple[int, dict]:
    headers = {"Content-Type": "application/json"}
    if csrf and CSRF_TOKEN and method.upper() not in {"GET", "HEAD", "OPTIONS"}:
        headers["X-CSRF-Token"] = CSRF_TOKEN
    if setup:
        headers["X-Praetor-Setup-Token"] = SETUP_TOKEN
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(API_BASE + path, data=data, headers=headers, method=method)
    try:
        with OPENER.open(req, timeout=30) as resp:
            return resp.status, json.load(resp)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        return exc.code, json.loads(body)


def wait_for(url: str) -> None:
    for _ in range(60):
        try:
            with urllib.request.urlopen(url, timeout=5):
                return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError(f"server did not become ready: {url}")


def onboarding_payload() -> dict:
    return {
        "owner_name": "Jove",
        "owner_email": "jove@example.com",
        "owner_password": "praetor-office-password",
        "language": "zh-TW",
        "leadership_style": "strategic",
        "decision_style": "balanced",
        "organization_style": "lean",
        "autonomy_mode": "hybrid",
        "risk_priority": "avoid_wrong_decisions",
        "workspace_root": str(WORKSPACE_DIR),
        "runtime": {"mode": "api", "provider": "openai", "model": "fake-gpt"},
        "require_approval": ["delete_files", "shell_commands"],
    }


def start_api() -> subprocess.Popen[str]:
    env = os.environ.copy()
    env["PRAETOR_STATE_DIR"] = str(STATE_DIR)
    env["PRAETOR_SETUP_TOKEN"] = SETUP_TOKEN
    env["OPENAI_API_KEY"] = "fake-key"
    return subprocess.Popen(
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


def start_web() -> subprocess.Popen[str]:
    env = os.environ.copy()
    env["PRAETOR_WEB_UPSTREAM"] = API_BASE
    return subprocess.Popen(
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
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def stop(proc: subprocess.Popen[str]) -> None:
    if proc.poll() is None:
        proc.send_signal(signal.SIGINT)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


def main() -> int:
    global CSRF_TOKEN
    subprocess.run(["rm", "-rf", str(STATE_DIR), str(WORKSPACE_DIR)], check=True)
    api_proc = start_api()
    web_proc = start_web()
    try:
        wait_for(f"{API_BASE}/health")
        wait_for(f"{WEB_BASE}/health")
        onboarding_status, onboarding = request("POST", "/onboarding/complete", onboarding_payload(), setup=True)
        _, session = request("GET", "/auth/session")
        CSRF_TOKEN = session["data"]["csrf_token"]
        mission_status, mission_payload = request(
            "POST",
            "/missions",
            {
                "title": "Office smoke mission",
                "summary": "Validate CEO office and mission timeline.",
                "domains": ["operations"],
                "priority": "high",
                "requested_outputs": [],
            },
        )
        mission_id = mission_payload["data"]["id"]
        snapshot_status, snapshot = request("GET", "/api/office/snapshot")
        chat_status, chat = request(
            "POST",
            "/api/office/conversation",
            {"body": "建立任務：檢查 Office v2 的 AI 內部對話是否清楚。"},
        )
        created_mission_id = chat["data"]["created_mission"]["id"]
        timeline_status, timeline = request("GET", f"/api/missions/{mission_id}/timeline")
        created_timeline_status, created_timeline = request("GET", f"/api/missions/{created_mission_id}/timeline")
        agent_status, agent_messages = request("GET", f"/api/missions/{created_mission_id}/agent-messages")
        with urllib.request.urlopen(f"{WEB_BASE}/office", timeout=10) as resp:
            office_html = resp.read().decode("utf-8")
        print(
            json.dumps(
                {
                    "onboarding_status": onboarding_status,
                    "onboarding_ok": onboarding["ok"],
                    "mission_status": mission_status,
                    "mission_id": mission_id,
                    "snapshot_status": snapshot_status,
                    "snapshot_missions": len(snapshot["data"]["missions"]),
                    "chat_status": chat_status,
                    "chat_messages": len(chat["data"]["messages"]),
                    "chat_intent": chat["data"]["intent"],
                    "chat_created_mission": bool(chat["data"]["created_mission"]),
                    "chat_agent_messages": len(chat["data"]["agent_messages"]),
                    "timeline_status": timeline_status,
                    "timeline_events": len(timeline["data"]["events"]),
                    "created_timeline_status": created_timeline_status,
                    "created_timeline_events": len(created_timeline["data"]["events"]),
                    "agent_status": agent_status,
                    "agent_messages": len(agent_messages["data"]["messages"]),
                    "office_html": "Praetor Office" in office_html,
                },
                ensure_ascii=True,
            )
        )
        return 0
    finally:
        stop(web_proc)
        stop(api_proc)


if __name__ == "__main__":
    raise SystemExit(main())
