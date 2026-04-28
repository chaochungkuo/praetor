from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path

from .config import ExecutorConfig
from .models import CreateRunRequest


def _tail(value: str, limit: int = 4000) -> str:
    return value[-limit:] if len(value) > limit else value


def _normalize_generic_result(stdout: str, stderr: str, exit_code: int | None, timed_out: bool):
    output = f"{stdout}\n{stderr}".lower()
    if timed_out:
        return ("failed_transient", True, "timeout waiting for executor")
    if (
        ("auth" in output and ("login" in output or "expired" in output))
        or "not logged in" in output
        or "please run /login" in output
        or "please run claude auth login" in output
    ):
        return ("auth_required", True, "executor authentication required")
    if "approve" in output or "confirmation" in output or "press enter" in output:
        return ("interactive_approval_required", True, "executor requested interactive approval")
    if "permission denied" in output or "not permitted" in output:
        return ("failed_permanent", True, "executor permission denied")
    if exit_code == 0:
        return ("completed", False, None)
    return ("failed_permanent", True, "executor exited with non-zero status")


def build_task_prompt(request: CreateRunRequest, host_workdir: str) -> str:
    task = request.task_spec
    approval = task.approval_policy
    lines = [
        f"Task: {task.title}",
        "",
        "Objective:",
        task.instructions.strip(),
        "",
        f"Working directory: {host_workdir}",
        "Operate only inside the working directory and its explicitly provided files.",
        "",
        "Constraints:",
        f"- Shell commands allowed: {'yes' if approval.allow_shell else 'no'}",
        f"- Destructive writes allowed: {'yes' if approval.allow_destructive_write else 'no'}",
        "- Do not read or write outside the mapped workspace or working directory.",
        "- Do not expose credentials, tokens, private keys, personal data, private file contents, or raw transcripts.",
        "- Do not send, upload, publish, email, or otherwise share data externally unless the task explicitly says it is approved.",
        "- If safety, privacy, legal, credential, or destructive-file risk appears, stop and report the escalation need.",
        "- Do not ask interactive approval questions; finish non-interactively.",
        "- Prefer direct file changes and concise final reporting.",
    ]
    if task.input_files:
        lines.extend(["", "Input files:"])
        lines.extend(f"- {item}" for item in task.input_files)
    if task.expected_outputs:
        lines.extend(["", "Expected outputs:"])
        lines.extend(f"- {item}" for item in task.expected_outputs)
    lines.extend(["", "When finished, summarize what changed and any remaining risks."])
    return "\n".join(lines)


def _native_command_name(command: str) -> str:
    return Path(command).name


def _generic_payload(request: CreateRunRequest) -> str:
    return json.dumps(
        {
            "request_id": request.request_id,
            "mission_id": request.mission_id,
            "task_id": request.task_id,
            "task_spec": request.task_spec.model_dump(mode="json"),
            "path_mapping": request.path_mapping.model_dump(mode="json"),
        },
        ensure_ascii=True,
    )


@dataclass
class PreparedExecution:
    command: list[str]
    prompt: str
    stdin_text: str | None = None


@dataclass
class ExecutionOutcome:
    normalized_status: str
    requires_owner_action: bool
    pause_reason: str | None
    stdout_tail: str | None
    stderr_tail: str | None
    usage_update: dict[str, int | float | bool | None] = field(default_factory=dict)


class BaseExecutorRunner:
    name: str

    def default_healthcheck(self, cfg: ExecutorConfig) -> list[str]:
        return [cfg.command, "--help"]

    def prepare(
        self,
        cfg: ExecutorConfig,
        request: CreateRunRequest,
        host_workdir: str,
    ) -> PreparedExecution:
        raise NotImplementedError

    def generic_prepare(self, cfg: ExecutorConfig, request: CreateRunRequest) -> PreparedExecution:
        return PreparedExecution(
            command=[cfg.command, *cfg.args],
            prompt="",
            stdin_text=_generic_payload(request),
        )

    def parse_result(
        self,
        stdout: str,
        stderr: str,
        exit_code: int | None,
        timed_out: bool,
    ) -> ExecutionOutcome:
        normalized_status, requires_owner_action, pause_reason = _normalize_generic_result(
            stdout, stderr, exit_code, timed_out
        )
        return ExecutionOutcome(
            normalized_status=normalized_status,
            requires_owner_action=requires_owner_action,
            pause_reason=pause_reason,
            stdout_tail=_tail(stdout) if stdout else None,
            stderr_tail=_tail(stderr) if stderr else None,
        )


class CodexRunner(BaseExecutorRunner):
    name = "codex"

    def default_healthcheck(self, cfg: ExecutorConfig) -> list[str]:
        return [cfg.command, *cfg.args, "exec", "--help"]

    def prepare(
        self,
        cfg: ExecutorConfig,
        request: CreateRunRequest,
        host_workdir: str,
    ) -> PreparedExecution:
        if _native_command_name(cfg.command) != "codex":
            return self.generic_prepare(cfg, request)
        sandbox = "workspace-write" if request.task_spec.expected_outputs else "read-only"
        prompt = build_task_prompt(request, host_workdir)
        command = [
            cfg.command,
            *cfg.args,
            "-a",
            "never",
            "-s",
            sandbox,
            "exec",
            "--json",
            "--skip-git-repo-check",
            "--ephemeral",
            "-C",
            host_workdir,
            prompt,
        ]
        return PreparedExecution(command=command, prompt=prompt, stdin_text=None)

    def parse_result(
        self,
        stdout: str,
        stderr: str,
        exit_code: int | None,
        timed_out: bool,
    ) -> ExecutionOutcome:
        outcome = super().parse_result(stdout, stderr, exit_code, timed_out)
        usage_update: dict[str, int | float | bool | None] = {}
        final_message: str | None = None

        for raw_line in stdout.splitlines():
            line = raw_line.strip()
            if not line.startswith("{"):
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            event_type = payload.get("type")
            if event_type == "item.completed":
                item = payload.get("item") or {}
                if item.get("type") == "agent_message" and item.get("text"):
                    final_message = item["text"]
            elif event_type == "turn.completed":
                usage = payload.get("usage") or {}
                usage_update = {
                    "input_tokens": usage.get("input_tokens"),
                    "output_tokens": usage.get("output_tokens"),
                    "usage_available": any(
                        usage.get(key) is not None for key in ("input_tokens", "output_tokens")
                    ),
                }

        outcome.usage_update = usage_update
        if final_message:
            outcome.stdout_tail = _tail(final_message)
        return outcome


class ClaudeCodeRunner(BaseExecutorRunner):
    name = "claude_code"

    def prepare(
        self,
        cfg: ExecutorConfig,
        request: CreateRunRequest,
        host_workdir: str,
    ) -> PreparedExecution:
        if _native_command_name(cfg.command) != "claude":
            return self.generic_prepare(cfg, request)
        prompt = build_task_prompt(request, host_workdir)
        allowed_tools = ["Read", "Edit", "Write", "Glob", "Grep"]
        if request.task_spec.approval_policy.allow_shell:
            allowed_tools.append("Bash")
        command = [
            cfg.command,
            *cfg.args,
            "-p",
            prompt,
            "--output-format",
            "json",
            "--permission-mode",
            "dontAsk",
            "--allowedTools",
            ",".join(allowed_tools),
            "--no-session-persistence",
        ]
        return PreparedExecution(command=command, prompt=prompt, stdin_text=None)

    def parse_result(
        self,
        stdout: str,
        stderr: str,
        exit_code: int | None,
        timed_out: bool,
    ) -> ExecutionOutcome:
        outcome = super().parse_result(stdout, stderr, exit_code, timed_out)
        payload: dict[str, object] | None = None
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError:
            for raw_line in reversed(stdout.splitlines()):
                line = raw_line.strip()
                if not line.startswith("{"):
                    continue
                try:
                    payload = json.loads(line)
                    break
                except json.JSONDecodeError:
                    continue

        if not payload:
            return outcome

        result_text = payload.get("result")
        usage = payload.get("usage")
        if isinstance(result_text, str) and result_text:
            outcome.stdout_tail = _tail(result_text)
        if isinstance(usage, dict):
            outcome.usage_update = {
                "input_tokens": usage.get("input_tokens") or usage.get("inputTokens"),
                "output_tokens": usage.get("output_tokens") or usage.get("outputTokens"),
                "estimated_cost": usage.get("estimated_cost")
                or usage.get("estimatedCost")
                or payload.get("total_cost_usd"),
                "usage_available": True,
            }
        return outcome


RUNNERS: dict[str, BaseExecutorRunner] = {
    "codex": CodexRunner(),
    "claude_code": ClaudeCodeRunner(),
}


def get_runner(name: str) -> BaseExecutorRunner:
    return RUNNERS[name]
