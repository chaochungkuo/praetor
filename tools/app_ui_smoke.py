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
STATE_DIR = pathlib.Path("/tmp/praetor-app-ui-smoke-state")
PORT = 9742
BASE_URL = f"http://127.0.0.1:{PORT}"
COOKIE_JAR = http.cookiejar.CookieJar()
OPENER = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(COOKIE_JAR))
CSRF_TOKEN = None


def get_text(path: str) -> str:
    req = urllib.request.Request(BASE_URL + path, method="GET")
    with OPENER.open(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def request_json(method: str, path: str, payload: dict | None = None) -> dict:
    global CSRF_TOKEN
    headers = {"Content-Type": "application/json"}
    if CSRF_TOKEN and method.upper() not in {"GET", "HEAD", "OPTIONS"}:
        headers["X-CSRF-Token"] = CSRF_TOKEN
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(BASE_URL + path, data=data, headers=headers, method=method)
    with OPENER.open(req, timeout=30) as resp:
        return json.load(resp)


def wait_for_server() -> None:
    for _ in range(50):
        try:
            get_text("/app/praetor")
            return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError("praetor ui did not become ready")


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
        wait_for_server()
        welcome = get_text("/app/welcome")
        before = get_text("/app/praetor")
        request_json(
            "POST",
            "/onboarding/complete",
            {
                "owner_name": "Jove",
                "owner_email": "jove@example.com",
                "owner_password": "praetor-ui-password",
                "language": "en",
                "leadership_style": "strategic",
                "decision_style": "balanced",
                "organization_style": "lean",
                "autonomy_mode": "hybrid",
                "risk_priority": "avoid_wrong_decisions",
                "workspace_root": "/tmp/praetor-ui-workspace",
                "runtime": {
                    "mode": "subscription_executor",
                    "executor": "codex",
                },
                "require_approval": [
                    "delete_files",
                    "overwrite_important_files",
                    "shell_commands",
                ],
            },
        )
        CSRF_TOKEN = request_json("GET", "/auth/session")["data"]["csrf_token"]
        request_json(
            "POST",
            "/missions",
            {
                "title": "UI Smoke Mission",
                "summary": "Create a mission through the web UI route.",
                "domains": ["operations"],
                "priority": "high",
                "requested_outputs": ["/workspace/Projects/UISmoke/PROJECT.md"],
            },
        )
        created = request_json("GET", "/missions")["data"]["missions"][0]
        anon_text = urllib.request.urlopen(f"{BASE_URL}/app/overview", timeout=30).read().decode("utf-8")
        praetor = get_text("/app/praetor")
        inbox = get_text("/app/inbox")
        overview = get_text("/app/overview")
        tasks = get_text("/app/tasks")
        mission_detail = get_text(f"/app/missions/{created['id']}")
        agents = get_text("/app/agents")
        activity = get_text("/app/activity")
        memory = get_text("/app/memory")
        decisions = get_text("/app/decisions")
        models = get_text("/app/models")
        meetings = get_text("/app/meetings")
        mobile = get_text("/m/briefing")
        settings = get_text("/app/settings")
        print(
            json.dumps(
                {
                    "welcome_has_language": "Welcome to Praetor" in welcome or "歡迎使用 Praetor" in welcome,
                    "before_has_conversation": "Praetor onboarding meeting" in before,
                    "before_has_wizard": "Founder to Praetor" in before,
                    "anon_redirects_to_login": "Owner login" in anon_text,
                    "praetor_has_briefing": "Praetor briefing" in praetor,
                    "praetor_has_ceo_hint": "mission draft, approval request, memory update" in praetor,
                    "praetor_has_starters": "Suggested first tasks" in praetor,
                    "inbox_has_chairman_inbox": "Chairman Inbox" in inbox,
                    "inbox_has_governance_review": "Governance review" in inbox,
                    "overview_has_total": "Total missions" in overview,
                    "tasks_has_board": "Mission board" in tasks,
                    "mission_detail_has_work_sessions": "AI work sessions" in mission_detail,
                    "mission_detail_has_stage": "Mission stage" in mission_detail,
                    "mission_detail_has_work_trace": "AI work trace" in mission_detail,
                    "mission_detail_has_executor_control": "Executor control" in mission_detail,
                    "mission_detail_has_knowledge_workspace": "Knowledge workspace" in mission_detail,
                    "mission_detail_has_workspace_scope": "Workspace scope" in mission_detail,
                    "mission_detail_has_workspace_steward": "Workspace Steward" in mission_detail,
                    "mission_detail_has_run_attempts": "Run attempts" in mission_detail,
                    "mission_detail_has_board_briefing": "Board briefing" in mission_detail,
                    "mission_detail_has_memory_promotion": "Memory promotion" in mission_detail,
                    "memory_has_client_record": "Client record" in memory,
                    "agents_has_directory": "Agent Directory" in agents,
                    "agents_has_command_center": "AI command center" in agents,
                    "agents_has_current_work": "Current work" in agents,
                    "agents_has_mission_teams": "Mission teams" in agents,
                    "agents_has_skill_sources": "Skill sources" in agents,
                    "agents_has_skill_registry": "Skill registry" in agents,
                    "agents_has_permission_profiles": "Permission profiles" in agents,
                    "agents_has_employment_contracts": "Employment contracts" in agents,
                    "agents_has_team_templates": "Team templates" in agents,
                    "activity_has_audit": "Audit stream" in activity,
                    "memory_has_wiki": "Company memory" in memory,
                    "decisions_has_audit": "Audit trail" in decisions,
                    "models_has_connection": "Model and API connection" in models,
                    "models_has_test_connection": "Test connection" in models,
                    "models_has_usage": "Usage by executor" in models,
                    "models_has_subscription_executor_setup": "ChatGPT subscription executor" in models,
                    "meetings_has_title": "Structured meetings" in meetings,
                    "mobile_has_briefing": "Mobile briefing" in mobile or "行動簡報" in mobile,
                    "settings_has_owner": "Owner" in settings,
                    "settings_has_telegram": "Telegram CEO access" in settings,
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
