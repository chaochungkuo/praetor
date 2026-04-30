import json
import os
import pathlib
import signal
import socket
import subprocess
import sys
import time
import http.cookiejar
import urllib.error
import urllib.request


ROOT = pathlib.Path(__file__).resolve().parents[1]
STATE_DIR = pathlib.Path("/tmp/praetor-app-smoke-state")
TEST_ROOT = pathlib.Path("/tmp/praetor-app-smoke-runtime")

def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


PORT = find_free_port()
BASE_URL = f"http://127.0.0.1:{PORT}"
BRIDGE_PORT = find_free_port()
BRIDGE_URL = f"http://127.0.0.1:{BRIDGE_PORT}"
BRIDGE_TOKEN = "app-smoke-token-for-local-security-tests"
SETUP_TOKEN = "setup-token-for-app-smoke"
COOKIE_JAR = http.cookiejar.CookieJar()
OPENER = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(COOKIE_JAR))
CSRF_TOKEN = None


def request(method: str, path: str, payload: dict | None = None, *, setup: bool = False) -> dict:
    global CSRF_TOKEN
    headers = {"Content-Type": "application/json"}
    if CSRF_TOKEN and method.upper() not in {"GET", "HEAD", "OPTIONS"}:
        headers["X-CSRF-Token"] = CSRF_TOKEN
    if setup:
        headers["X-Praetor-Setup-Token"] = SETUP_TOKEN
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(BASE_URL + path, data=data, headers=headers, method=method)
    try:
        with OPENER.open(req, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {path} failed with HTTP {exc.code}: {body}") from exc


def wait_for_server() -> None:
    for _ in range(50):
        try:
            request("GET", "/health")
            return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError("praetor api did not become ready")


def wait_for_bridge() -> None:
    headers = {"Authorization": f"Bearer {BRIDGE_TOKEN}"}
    req = urllib.request.Request(
        BRIDGE_URL + "/health",
        headers=headers,
        method="GET",
    )
    for _ in range(50):
        try:
            with urllib.request.urlopen(req, timeout=10):
                return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError("praetor-execd did not become ready")


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
    if STATE_DIR.exists():
        subprocess.run(["rm", "-rf", str(STATE_DIR)], check=True)
    if TEST_ROOT.exists():
        subprocess.run(["rm", "-rf", str(TEST_ROOT)], check=True)
    env = os.environ.copy()
    env["PRAETOR_STATE_DIR"] = str(STATE_DIR)
    workspace_root = TEST_ROOT / "workspace"
    bridge_config = write_bridge_config(workspace_root)
    bridge_env = env.copy()
    bridge_env["PRAETOR_EXECD_CONFIG"] = str(bridge_config)
    bridge_env["PRAETOR_EXECUTOR_BRIDGE_TOKEN"] = BRIDGE_TOKEN
    app_env = env.copy()
    app_env["PRAETOR_BRIDGE_BASE_URL"] = BRIDGE_URL
    app_env["PRAETOR_BRIDGE_TOKEN"] = BRIDGE_TOKEN
    app_env["PRAETOR_SETUP_TOKEN"] = SETUP_TOKEN

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
        env=app_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        wait_for_bridge()
        wait_for_server()
        workspace_root_text = str(workspace_root)
        preview = request(
            "POST",
            "/onboarding/preview",
            {
                "owner_name": "Jove",
                "owner_email": "jove@example.com",
                "owner_password": "praetor-smoke-password",
                "language": "en",
                "leadership_style": "strategic",
                "decision_style": "balanced",
                "organization_style": "lean",
                "autonomy_mode": "hybrid",
                "risk_priority": "avoid_wrong_decisions",
                "workspace_root": workspace_root_text,
                "runtime": {"mode": "subscription_executor", "executor": "codex"},
                "require_approval": [
                    "delete_files",
                    "overwrite_important_files",
                    "shell_commands",
                ],
            },
            setup=True,
        )
        complete = request(
            "POST",
            "/onboarding/complete",
            {
                "owner_name": "Jove",
                "owner_email": "jove@example.com",
                "owner_password": "praetor-smoke-password",
                "language": "en",
                "leadership_style": "strategic",
                "decision_style": "balanced",
                "organization_style": "lean",
                "autonomy_mode": "hybrid",
                "risk_priority": "avoid_wrong_decisions",
                "workspace_root": workspace_root_text,
                "runtime": {"mode": "subscription_executor", "executor": "codex"},
                "require_approval": [
                    "delete_files",
                    "overwrite_important_files",
                    "shell_commands",
                ],
            },
            setup=True,
        )
        CSRF_TOKEN = request("GET", "/auth/session")["data"]["csrf_token"]
        mission = request(
            "POST",
            "/missions",
            {
                "title": "Create first project",
                "summary": "Bootstrap a first mission path",
                "domains": ["operations"],
                "priority": "high",
                "requested_outputs": ["/workspace/Projects/Alpha/PROJECT.md"],
            },
        )
        mission_id = mission["data"]["id"]
        mission_knowledge = request("GET", f"/api/missions/{mission_id}/knowledge")
        mission_scope = request("GET", f"/api/missions/{mission_id}/workspace-scope")
        workflow = request("GET", "/api/workflow")
        governance_review = request("GET", "/api/governance/review")
        governance_review_run = request("POST", "/api/governance/review")
        run_result = request("POST", f"/missions/{mission_id}/run")
        run_attempts = request("GET", f"/api/missions/{mission_id}/run-attempts")
        work_sessions = request("GET", f"/api/missions/{mission_id}/work-sessions")
        completion = request("GET", f"/api/missions/{mission_id}/completion-contract")
        meeting = request("POST", f"/missions/{mission_id}/meeting")
        approval = request(
            "POST",
            "/approvals",
            {
                "mission_id": mission_id,
                "category": "change_strategy",
                "reason": "Smoke test approval request.",
            },
        )
        approval_id = approval["data"]["id"]
        approval_resolved = request("POST", f"/approvals/{approval_id}/approved")
        mission_detail = request("GET", f"/missions/{mission_id}")
        stopped = request(
            "POST",
            "/missions",
            {
                "title": "Stop me",
                "summary": "Validate mission stop control",
                "domains": ["operations"],
                "priority": "normal",
                "requested_outputs": [],
            },
        )
        stopped_id = stopped["data"]["id"]
        stopped_result = request(
            "POST",
            f"/missions/{stopped_id}/stop",
            {"reason": "smoke_test"},
        )
        complex_mission = request(
            "POST",
            "/missions",
            {
                "title": "Complex mission",
                "summary": "This mission spans finance, development, and operations and requests multiple outputs for validation.",
                "domains": ["finance", "development", "operations"],
                "priority": "critical",
                "requested_outputs": [
                    "/workspace/Projects/Complex/PROJECT.md",
                    "/workspace/Projects/Complex/TASKS.md",
                    "/workspace/Projects/Complex/STATUS.md",
                ],
            },
        )
        contract_mission = request(
            "POST",
            "/missions",
            {
                "title": "Draft contract for Client Acme",
                "summary": "Prepare a first contract draft and track lawyer feedback.",
                "domains": ["legal"],
                "priority": "high",
                "requested_outputs": [],
            },
        )
        contract_knowledge = request("GET", f"/api/missions/{contract_mission['data']['id']}/knowledge")
        briefing = request("GET", "/praetor/briefing")
        exported = request("POST", "/schemas/export")
        report_path = workspace_root / "Missions" / mission_id / "REPORT.md"
        pm_report_path = workspace_root / "Missions" / mission_id / "PM_REPORT.md"
        print(
            json.dumps(
                {
                    "preview_ok": preview["ok"],
                    "onboarding_ok": complete["ok"],
                    "mission_id": mission_id,
                    "mission_status": mission_detail["data"]["status"],
                    "knowledge_clients": len(mission_knowledge["data"]["clients"]),
                    "knowledge_matters": len(mission_knowledge["data"]["matters"]),
                    "knowledge_open_questions": len(mission_knowledge["data"]["open_questions"]),
                    "workspace_scope_root": mission_scope["data"]["root"],
                    "workflow_has_contract": "Completion Contract" in workflow["data"]["body"],
                    "governance_review_ok": governance_review["ok"],
                    "governance_review_items": len(governance_review_run["data"]["items"]),
                    "run_attempt_status": run_attempts["data"]["attempts"][0]["status"],
                    "completion_has_workspace_scope": completion["data"]["workspace_scope_defined"],
                    "task_status": run_result["data"]["task"]["status"],
                    "bridge_status": run_result["data"]["bridge_run"]["normalized_status"],
                    "work_session_status": run_result["data"]["work_session"]["status"],
                    "work_session_turns": len(work_sessions["data"]["sessions"][0]["turns"]),
                    "meeting_id": meeting["data"]["id"],
                    "approval_status": approval_resolved["data"]["status"],
                    "stopped_status": stopped_result["data"]["status"],
                    "complex_pm_required": complex_mission["data"]["pm_required"],
                    "complex_manager_layer": complex_mission["data"]["manager_layer"],
                    "contract_client": contract_knowledge["data"]["clients"][0]["name"],
                    "contract_documents": len(contract_knowledge["data"]["documents"]),
                    "report_exists": report_path.exists(),
                    "pm_report_exists": pm_report_path.exists(),
                    "briefing": briefing["data"],
                    "schema_count": len(exported["data"]["paths"]),
                },
                ensure_ascii=True,
            )
        )
        return 0
    finally:
        if bridge_proc.poll() is None:
            bridge_proc.send_signal(signal.SIGINT)
            try:
                bridge_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                bridge_proc.kill()
                bridge_proc.wait(timeout=5)
        if proc.poll() is None:
            proc.send_signal(signal.SIGINT)
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
