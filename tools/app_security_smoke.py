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
sys.path.insert(0, str(ROOT / "apps" / "api"))
STATE_DIR = pathlib.Path("/tmp/praetor-app-security-smoke-state")
PORT = 9746
BASE_URL = f"http://127.0.0.1:{PORT}"
SETUP_TOKEN = "setup-token-for-local-security-smoke"
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
    req = urllib.request.Request(BASE_URL + path, data=data, headers=headers, method=method)
    try:
        with OPENER.open(req, timeout=30) as resp:
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


def onboarding_payload() -> dict:
    return {
        "owner_name": "Jove",
        "owner_email": "jove@example.com",
        "owner_password": "praetor-security-password",
        "language": "en",
        "leadership_style": "strategic",
        "decision_style": "balanced",
        "organization_style": "lean",
        "autonomy_mode": "hybrid",
        "risk_priority": "avoid_wrong_decisions",
        "workspace_root": "/tmp/praetor-security-workspace",
        "runtime": {"mode": "subscription_executor", "executor": "codex"},
        "require_approval": ["delete_files", "shell_commands"],
    }


def main() -> int:
    global CSRF_TOKEN
    from praetor_api.security import validate_runtime_security
    from praetor_api.storage import FilesystemStore

    old_env = {key: os.environ.get(key) for key in ["PRAETOR_ENV", "PRAETOR_SESSION_SECRET", "PRAETOR_SETUP_TOKEN"]}
    os.environ["PRAETOR_ENV"] = "production"
    os.environ["PRAETOR_SESSION_SECRET"] = "change-me"
    os.environ["PRAETOR_SETUP_TOKEN"] = "change-me"
    try:
        try:
            validate_runtime_security()
            raise AssertionError("weak production secrets were accepted")
        except RuntimeError:
            pass
    finally:
        for key, value in old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    try:
        FilesystemStore(pathlib.Path("/tmp/praetor-storage-security-state")).mission_dir(
            pathlib.Path("/tmp/praetor-security-workspace"),
            "../escape",
        )
        raise AssertionError("unsafe mission_id was accepted")
    except ValueError:
        pass

    if STATE_DIR.exists():
        subprocess.run(["rm", "-rf", str(STATE_DIR)], check=True)

    env = os.environ.copy()
    env["PRAETOR_STATE_DIR"] = str(STATE_DIR)
    env["PRAETOR_SETUP_TOKEN"] = SETUP_TOKEN
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
        missing_setup_status, missing_setup = request("POST", "/onboarding/complete", onboarding_payload())
        ok_setup_status, ok_setup = request("POST", "/onboarding/complete", onboarding_payload(), setup=True)
        _, session = request("GET", "/auth/session")
        CSRF_TOKEN = session["data"]["csrf_token"]
        missing_csrf_status, missing_csrf = request(
            "POST",
            "/missions",
            {
                "title": "Missing CSRF",
                "summary": "Should fail.",
                "domains": ["operations"],
                "requested_outputs": [],
            },
            csrf=False,
        )
        ok_csrf_status, ok_csrf = request(
            "POST",
            "/missions",
            {
                "title": "With CSRF",
                "summary": "Should succeed.",
                "domains": ["operations"],
                "requested_outputs": [],
            },
        )
        print(
            json.dumps(
                {
                    "missing_setup_status": missing_setup_status,
                    "missing_setup_code": missing_setup.get("detail", {}).get("code") or missing_setup.get("error", {}).get("code"),
                    "ok_setup_status": ok_setup_status,
                    "ok_setup_ok": ok_setup["ok"],
                    "missing_csrf_status": missing_csrf_status,
                    "missing_csrf_code": missing_csrf.get("detail", {}).get("code") or missing_csrf.get("error", {}).get("code"),
                    "ok_csrf_status": ok_csrf_status,
                    "ok_csrf_mission_id": bool(ok_csrf.get("data", {}).get("id")),
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
