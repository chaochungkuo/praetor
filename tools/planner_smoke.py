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
sys.path.insert(0, str(ROOT / "apps" / "api"))

from praetor_api.planner import CEOPlannerContext, DeterministicCEOPlanner  # noqa: E402


STATE_DIR = pathlib.Path("/tmp/praetor-planner-smoke-state")
WORKSPACE_DIR = pathlib.Path("/tmp/praetor-planner-smoke-workspace")
API_PORT = 9756
API_BASE = f"http://127.0.0.1:{API_PORT}"
FAKE_OPENAI_URL = "http://127.0.0.1:9760/v1"
COOKIE_JAR = http.cookiejar.CookieJar()
OPENER = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(COOKIE_JAR))
CSRF_TOKEN = None


def request(method: str, path: str, payload: dict | None = None) -> dict:
    headers = {"Content-Type": "application/json"}
    if CSRF_TOKEN and method.upper() not in {"GET", "HEAD", "OPTIONS"}:
        headers["X-CSRF-Token"] = CSRF_TOKEN
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(API_BASE + path, data=data, headers=headers, method=method)
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


def start_fake_openai() -> subprocess.Popen[str]:
    return subprocess.Popen(
        [sys.executable, str(ROOT / "tools" / "fake_openai_server.py")],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def start_api() -> subprocess.Popen[str]:
    env = os.environ.copy()
    env["PRAETOR_STATE_DIR"] = str(STATE_DIR)
    env["PRAETOR_CEO_PLANNER_MODE"] = "llm"
    env["PRAETOR_CEO_PLANNER_PROVIDER"] = "openai"
    env["PRAETOR_CEO_PLANNER_MODEL"] = "fake-gpt"
    env["PRAETOR_OPENAI_BASE_URL"] = FAKE_OPENAI_URL
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


def stop(proc: subprocess.Popen[str]) -> None:
    if proc.poll() is None:
        proc.send_signal(signal.SIGINT)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


def assert_deterministic_planner_contract() -> list[str]:
    plan = DeterministicCEOPlanner().plan(
        CEOPlannerContext(
            instruction="建立任務：改善 Office。請建立 approval checkpoint，記住這個原則，並讓團隊做規劃簡報。",
            related_mission_id="mission_existing",
            mission_count=2,
            pending_approvals=1,
        )
    )
    action_types = [item.type for item in plan.actions]
    expected = {"mission_draft", "approval_request", "memory_update", "board_briefing"}
    missing = sorted(expected.difference(action_types))
    if missing:
        raise AssertionError(f"deterministic planner missing actions: {missing}")
    return action_types


def onboarding_payload() -> dict:
    return {
        "owner_name": "Jove",
        "owner_email": "jove@example.com",
        "owner_password": "praetor-planner-password",
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


def assert_llm_planner_api_contract() -> dict:
    global CSRF_TOKEN
    subprocess.run(["rm", "-rf", str(STATE_DIR), str(WORKSPACE_DIR)], check=True)
    fake_proc = start_fake_openai()
    api_proc = start_api()
    try:
        wait_for("http://127.0.0.1:9760")
        wait_for(f"{API_BASE}/health")
        onboarding = request("POST", "/onboarding/complete", onboarding_payload())
        CSRF_TOKEN = request("GET", "/auth/session")["data"]["csrf_token"]
        chat = request(
            "POST",
            "/api/office/conversation",
            {"body": "Use the LLM CEO planner to create a mission draft and update memory."},
        )
        data = chat["data"]
        action_types = [item["type"] for item in data["actions"]]
        action_statuses = [item["status"] for item in data["actions"]]
        if data["intent"] != "mission_draft":
            raise AssertionError(f"unexpected planner intent: {data['intent']}")
        if "mission_draft" not in action_types or "memory_update" not in action_types:
            raise AssertionError(f"missing LLM planner actions: {action_types}")
        if not data["created_mission"]:
            raise AssertionError("LLM planner did not create a mission")
        memory_action = next(item for item in data["actions"] if item["type"] == "memory_update")
        if memory_action["status"] != "applied" or not memory_action["result_id"]:
            raise AssertionError(f"memory action was not applied: {memory_action}")
        return {
            "onboarding_ok": onboarding["ok"],
            "intent": data["intent"],
            "actions": action_types,
            "statuses": action_statuses,
            "created_mission_id": data["created_mission"]["id"],
            "memory_result": memory_action["result_id"],
        }
    finally:
        stop(api_proc)
        stop(fake_proc)


def main() -> int:
    deterministic_actions = assert_deterministic_planner_contract()
    llm_result = assert_llm_planner_api_contract()
    print(
        json.dumps(
            {
                "deterministic_actions": deterministic_actions,
                "llm": llm_result,
            },
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
