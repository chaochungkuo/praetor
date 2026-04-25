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
STATE_DIR = pathlib.Path("/tmp/praetor-app-auth-smoke-state")
PORT = 9745
BASE_URL = f"http://127.0.0.1:{PORT}"
COOKIE_JAR = http.cookiejar.CookieJar()
OPENER = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(COOKIE_JAR))
CSRF_TOKEN = None


def request(method: str, path: str, payload: dict | None = None, use_cookies: bool = True) -> tuple[int, dict]:
    global CSRF_TOKEN
    headers = {"Content-Type": "application/json"}
    if CSRF_TOKEN and method.upper() not in {"GET", "HEAD", "OPTIONS"}:
        headers["X-CSRF-Token"] = CSRF_TOKEN
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(BASE_URL + path, data=data, headers=headers, method=method)
    opener = OPENER if use_cookies else urllib.request.build_opener()
    try:
        with opener.open(req, timeout=30) as resp:
            return resp.status, json.load(resp)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        return exc.code, json.loads(body)


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

    env = os.environ.copy()
    env["PRAETOR_STATE_DIR"] = str(STATE_DIR)
    proc = subprocess.Popen(
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
        wait_for(f"{BASE_URL}/health")
        onboarding_status, onboarding = request(
            "POST",
            "/onboarding/complete",
            {
                "owner_name": "Jove",
                "owner_email": "jove@example.com",
                "owner_password": "praetor-auth-password",
                "language": "en",
                "leadership_style": "strategic",
                "decision_style": "balanced",
                "organization_style": "lean",
                "autonomy_mode": "hybrid",
                "risk_priority": "avoid_wrong_decisions",
                "workspace_root": "/tmp/praetor-auth-workspace",
                "runtime": {"mode": "subscription_executor", "executor": "codex"},
                "require_approval": ["delete_files", "shell_commands"],
            },
        )
        _, first_session = request("GET", "/auth/session")
        CSRF_TOKEN = first_session["data"]["csrf_token"]
        request("POST", "/auth/logout")
        anon_status, anon_resp = request("GET", "/missions", use_cookies=False)
        bad_login_status, _ = request("POST", "/auth/login", {"password": "wrong-password"})
        login_status, login = request("POST", "/auth/login", {"password": "praetor-auth-password"})
        session_status, session = request("GET", "/auth/session")
        CSRF_TOKEN = session["data"]["csrf_token"]
        mission_status, mission = request(
            "POST",
            "/missions",
            {
                "title": "Auth Smoke Mission",
                "summary": "Verify authenticated mission creation.",
                "domains": ["operations"],
                "priority": "high",
                "requested_outputs": ["/workspace/Projects/Auth/PROJECT.md"],
            },
        )
        request("POST", "/auth/logout")
        post_logout_status, post_logout = request("GET", "/auth/session")
        print(
            json.dumps(
                {
                    "onboarding_status": onboarding_status,
                    "onboarding_ok": onboarding["ok"],
                    "anon_status": anon_status,
                    "anon_error": anon_resp["error"]["code"],
                    "bad_login_status": bad_login_status,
                    "login_status": login_status,
                    "login_authenticated": login["data"]["authenticated"],
                    "session_authenticated": session["data"]["authenticated"] if session_status == 200 else False,
                    "mission_create_status": mission_status,
                    "mission_id_present": bool(mission.get("data", {}).get("id")),
                    "post_logout_authenticated": post_logout["data"]["authenticated"] if post_logout_status == 200 else True,
                },
                ensure_ascii=True,
            )
        )
        return 0
    finally:
        if proc.poll() is None:
            proc.send_signal(signal.SIGINT)
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
