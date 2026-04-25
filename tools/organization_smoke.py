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
STATE_DIR = pathlib.Path("/tmp/praetor-organization-smoke-state")
WORKSPACE_DIR = pathlib.Path("/tmp/praetor-organization-smoke-workspace")
PORT = 9757
BASE_URL = f"http://127.0.0.1:{PORT}"
SETUP_TOKEN = "setup-token-for-organization-smoke"
COOKIE_JAR = http.cookiejar.CookieJar()
OPENER = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(COOKIE_JAR))
CSRF_TOKEN = None


def request(method: str, path: str, payload: dict | None = None, *, setup: bool = False) -> dict:
    headers = {"Content-Type": "application/json"}
    if CSRF_TOKEN and method.upper() not in {"GET", "HEAD", "OPTIONS"}:
        headers["X-CSRF-Token"] = CSRF_TOKEN
    if setup:
        headers["X-Praetor-Setup-Token"] = SETUP_TOKEN
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(BASE_URL + path, data=data, headers=headers, method=method)
    with OPENER.open(req, timeout=30) as resp:
        return json.load(resp)


def wait_for(url: str) -> None:
    for _ in range(60):
        try:
            with urllib.request.urlopen(url, timeout=5):
                return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError(f"server did not become ready: {url}")


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
            str(PORT),
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


def onboarding_payload() -> dict:
    return {
        "owner_name": "Jove",
        "owner_email": "jove@example.com",
        "owner_password": "praetor-organization-password",
        "language": "zh-TW",
        "leadership_style": "strategic",
        "decision_style": "balanced",
        "organization_style": "structured",
        "autonomy_mode": "hybrid",
        "risk_priority": "avoid_acting_without_approval",
        "workspace_root": str(WORKSPACE_DIR),
        "runtime": {"mode": "api", "provider": "openai", "model": "fake-gpt"},
        "require_approval": ["delete_files", "shell_commands"],
    }


def main() -> int:
    global CSRF_TOKEN
    subprocess.run(["rm", "-rf", str(STATE_DIR), str(WORKSPACE_DIR)], check=True)
    api_proc = start_api()
    try:
        wait_for(f"{BASE_URL}/health")
        onboarding = request("POST", "/onboarding/complete", onboarding_payload(), setup=True)
        CSRF_TOKEN = request("GET", "/auth/session")["data"]["csrf_token"]
        mission = request(
            "POST",
            "/missions",
            {
                "title": "Security and legal beta launch",
                "summary": "Prepare beta launch with privacy, security, and legal review.",
                "domains": ["development", "operations"],
                "priority": "critical",
                "requested_outputs": [],
            },
        )["data"]
        chat = request(
            "POST",
            "/api/office/conversation",
            {
                "related_mission_id": mission["id"],
                "body": "請為這個任務建立 AI team，需要 Project Manager、Security Officer、Legal Counsel、Reviewer。以後安全和隱私都要升級給董事長裁示，並建立 decision escalation checkpoint。",
            },
        )["data"]
        organization = request("GET", f"/api/missions/{mission['id']}/organization")["data"]
        contract = request("GET", f"/api/missions/{mission['id']}/completion-contract")["data"]
        snapshot = request("GET", "/api/office/snapshot")["data"]

        action_types = [item["type"] for item in chat["actions"]]
        role_names = sorted({item["role_name"] for item in organization["agents"]})
        if "staffing_proposal" not in action_types:
            raise AssertionError(f"missing staffing_proposal action: {action_types}")
        if "delegation_create" not in action_types:
            raise AssertionError(f"missing delegation_create action: {action_types}")
        if "decision_escalation" not in action_types:
            raise AssertionError(f"missing decision_escalation action: {action_types}")
        if "standing_order_update" not in action_types:
            raise AssertionError(f"missing standing_order_update action: {action_types}")
        for expected_role in ["Project Manager", "Security Officer", "Legal Counsel", "Reviewer"]:
            if expected_role not in role_names:
                raise AssertionError(f"missing agent role {expected_role}: {role_names}")
        if not organization["teams"]:
            raise AssertionError("mission team was not created")
        if not organization["delegations"]:
            raise AssertionError("delegation was not created")
        if not organization["escalations"]:
            raise AssertionError("escalation was not created")
        if not snapshot["organization"]["standing_orders"]:
            raise AssertionError("standing orders are missing")

        print(
            json.dumps(
                {
                    "onboarding_ok": onboarding["ok"],
                    "mission_id": mission["id"],
                    "actions": action_types,
                    "roles": role_names,
                    "teams": len(organization["teams"]),
                    "delegations": len(organization["delegations"]),
                    "escalations": len(organization["escalations"]),
                    "standing_orders": len(snapshot["organization"]["standing_orders"]),
                    "completion_can_close": contract["can_close"],
                    "completion_blockers": contract["blockers"],
                },
                ensure_ascii=True,
            )
        )
        return 0
    finally:
        stop(api_proc)


if __name__ == "__main__":
    raise SystemExit(main())
