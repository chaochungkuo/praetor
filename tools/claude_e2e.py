import json
import os
import pathlib
import signal
import subprocess
import sys
import time


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "workers" / "runtime"))

from praetor_runtime import BridgeClient  # noqa: E402


TEST_ROOT = pathlib.Path("/tmp/praetor-claude-e2e")
BASE_URL = "http://127.0.0.1:9417"
TOKEN = "claude-e2e-token-for-local-security-tests"


def write_config() -> pathlib.Path:
    workspace = TEST_ROOT / "workspace"
    logs = TEST_ROOT / "logs"
    project = workspace / "Projects" / "Test"
    project.mkdir(parents=True, exist_ok=True)
    logs.mkdir(parents=True, exist_ok=True)
    config = TEST_ROOT / "config.yaml"
    config.write_text(
        "\n".join(
            [
                "server:",
                "  host: 127.0.0.1",
                "  port: 9417",
                "  auth_token: env:PRAETOR_EXECUTOR_BRIDGE_TOKEN",
                "paths:",
                f"  host_workspace_root: {workspace}",
                "  allowed_roots:",
                f"    - {workspace}",
                "  deny_roots:",
                f"    - {workspace / 'Archive'}",
                "executors:",
                "  claude_code:",
                "    enabled: true",
                "    command: claude",
                "    args: []",
                "    requires_login: true",
                "    supports_noninteractive_batch: true",
                "    supports_cancel: true",
                "runtime:",
                "  max_concurrent_runs: 2",
                "  default_timeout_seconds: 120",
                "  max_event_buffer: 5000",
                "  persist_run_logs: true",
                f"  log_dir: {logs}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return config


def wait_for_server(client: BridgeClient) -> None:
    for _ in range(50):
        try:
            client.health()
            return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError("bridge server did not become ready")


def main() -> int:
    config = write_config()
    env = os.environ.copy()
    env["PRAETOR_EXECD_CONFIG"] = str(config)
    env["PRAETOR_EXECUTOR_BRIDGE_TOKEN"] = TOKEN

    proc = subprocess.Popen(
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
            "9417",
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    client = BridgeClient(base_url=BASE_URL, token=TOKEN)
    try:
        wait_for_server(client)
        created = client.create_run(
            {
                "request_id": "req_claude_e2e",
                "mission_id": "mission_claude_e2e",
                "task_id": "task_claude_e2e",
                "executor": "claude_code",
                "timeout_seconds": 120,
                "path_mapping": {
                    "container_workspace_root": "/app/workspace",
                    "host_workspace_root": str(TEST_ROOT / "workspace"),
                    "target_workdir": "/app/workspace/Projects/Test",
                },
                "task_spec": {
                    "title": "Claude E2E Test",
                    "instructions": "Inspect the working directory, print READY, and stop without changing files.",
                    "input_files": [],
                    "expected_outputs": [],
                    "approval_policy": {
                        "allow_destructive_write": False,
                        "allow_shell": False,
                    },
                },
            }
        )
        final_run = client.wait_for_terminal(
            created["run_id"], poll_interval_seconds=0.5, timeout_seconds=180
        )
        print(
            json.dumps(
                {
                    "run_id": created["run_id"],
                    "normalized_status": final_run["normalized_status"],
                    "usage": final_run["usage"],
                    "stdout_tail": final_run["stdout_tail"],
                    "changed_files": final_run["changed_files"],
                },
                ensure_ascii=True,
            )
        )
        return 0 if final_run["normalized_status"] == "completed" else 1
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
