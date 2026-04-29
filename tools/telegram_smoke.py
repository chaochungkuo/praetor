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
STATE_DIR = pathlib.Path("/tmp/praetor-telegram-smoke-state")
WORKSPACE_DIR = pathlib.Path("/tmp/praetor-telegram-smoke-workspace")
PORT = 9748
BASE_URL = f"http://127.0.0.1:{PORT}"
WEBHOOK_SECRET = "telegram-smoke-secret-with-enough-length"


sys.path.insert(0, str(ROOT / "apps" / "api"))
from praetor_api.models import OnboardingAnswers, TelegramIntegrationSettings  # noqa: E402
from praetor_api.service import PraetorService  # noqa: E402
from praetor_api.storage import AppStorage  # noqa: E402


def post_webhook(update: dict, secret: str = WEBHOOK_SECRET) -> tuple[int, dict]:
    req = urllib.request.Request(
        BASE_URL + "/integrations/telegram/webhook",
        data=json.dumps(update).encode(),
        headers={
            "Content-Type": "application/json",
            "X-Telegram-Bot-Api-Secret-Token": secret,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.load(resp)
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def wait_for_server() -> None:
    for _ in range(50):
        try:
            with urllib.request.urlopen(BASE_URL + "/health", timeout=5):
                return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError("praetor api did not become ready")


def bootstrap_state() -> str:
    storage = AppStorage(STATE_DIR)
    service = PraetorService(storage)
    service.complete_onboarding(
        OnboardingAnswers(
            owner_name="Jove",
            owner_email="jove@example.com",
            owner_password="praetor-telegram-password",
            language="en",
            leadership_style="strategic",
            decision_style="balanced",
            organization_style="lean",
            autonomy_mode="hybrid",
            risk_priority="avoid_wrong_decisions",
            workspace_root=str(WORKSPACE_DIR),
            runtime={"mode": "subscription_executor", "executor": "codex"},
            require_approval=["delete_files", "shell_commands"],
        )
    )
    service.update_telegram_settings(
        TelegramIntegrationSettings(
            enabled=True,
            webhook_secret_set=True,
            allowed_user_id=424242,
            notify_approvals=True,
            allow_low_risk_approval=True,
        )
    )
    return service.create_telegram_pairing_code()


def main() -> int:
    if STATE_DIR.exists():
        subprocess.run(["rm", "-rf", str(STATE_DIR)], check=True)
    if WORKSPACE_DIR.exists():
        subprocess.run(["rm", "-rf", str(WORKSPACE_DIR)], check=True)
    code = bootstrap_state()
    env = os.environ.copy()
    env["PRAETOR_STATE_DIR"] = str(STATE_DIR)
    env["PRAETOR_TELEGRAM_WEBHOOK_SECRET"] = WEBHOOK_SECRET
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
        bad_status, bad_payload = post_webhook({"update_id": 1}, secret="wrong-secret")
        link_status, link_payload = post_webhook(
            {
                "update_id": 2,
                "message": {
                    "chat": {"id": 8888},
                    "from": {"id": 424242, "username": "jove"},
                    "text": f"/link {code}",
                },
            }
        )
        chat_status, chat_payload = post_webhook(
            {
                "update_id": 3,
                "message": {
                    "chat": {"id": 8888},
                    "from": {"id": 424242, "username": "jove"},
                    "text": "Create a mission draft from Telegram for a mobile CEO channel.",
                },
            }
        )
        briefing_status, briefing_payload = post_webhook(
            {
                "update_id": 4,
                "message": {
                    "chat": {"id": 8888},
                    "from": {"id": 424242, "username": "jove"},
                    "text": "/briefing",
                },
            }
        )
        storage = AppStorage(STATE_DIR)
        settings = storage.load_settings()
        messages = storage.list_conversation_messages()
        missions = storage.list_missions(WORKSPACE_DIR)
        print(
            json.dumps(
                {
                    "bad_secret_status": bad_status,
                    "bad_secret_code": bad_payload["error"]["code"],
                    "link_ok": link_status == 200 and link_payload["ok"],
                    "chat_ok": chat_status == 200 and chat_payload["ok"],
                    "briefing_ok": briefing_status == 200 and briefing_payload["ok"],
                    "linked_chat_id": settings.telegram.linked_chat_id if settings else None,
                    "linked_user_id": settings.telegram.linked_user_id if settings else None,
                    "conversation_messages": len(messages),
                    "mission_count": len(missions),
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
