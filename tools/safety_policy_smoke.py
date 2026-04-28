from __future__ import annotations

from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parents[1]
API_PATH = ROOT / "apps" / "api"
BRIDGE_PATH = ROOT / "bridges" / "praetor-execd"
for path in (API_PATH, BRIDGE_PATH):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from praetor_api.models import (  # noqa: E402
    AppSettings,
    CompanyDNA,
    GovernancePolicy,
    MissionDefinition,
    PlannerAction,
    RuntimeSelection,
    StandingOrder,
    WorkspaceConfig,
    WorkspacePermissions,
)
from praetor_api.planner import CEOPlannerContext, LLMCEOPlanner  # noqa: E402
from praetor_api.providers import build_generation_prompt  # noqa: E402
from praetor_api.safety_policy import build_prompt_safety_policy, contains_sensitive_material  # noqa: E402
from praetor_api.service import PraetorService  # noqa: E402
from praetor_api.storage import AppStorage  # noqa: E402
from praetor_api.workspace import bootstrap_workspace  # noqa: E402
from praetor_execd.executor_plugins import build_task_prompt  # noqa: E402
from praetor_execd.models import ApprovalPolicy, CreateRunRequest, PathMapping, TaskSpec  # noqa: E402


def main() -> None:
    workspace = Path("/tmp/praetor-workspace")
    settings = AppSettings(
        owner={"name": "Owner", "preferred_language": "zh-TW"},
        runtime=RuntimeSelection(mode="api", provider="openai", model="gpt-4.1-mini"),
        workspace=WorkspaceConfig(
            root=str(workspace),
            permissions=WorkspacePermissions(
                allow_read=[str(workspace)],
                allow_write=[str(workspace / "Projects"), str(workspace / "Wiki")],
                deny_write=[str(workspace / "Archive"), str(workspace / "Finance" / "Locked")],
            ),
        ),
        governance=GovernancePolicy(
            require_approval=["delete_files", "external_communication", "shell_commands"],
            never_allow=["access_outside_workspace", "store_raw_credentials_or_tokens"],
        ),
        company_dna=CompanyDNA(language="zh-TW"),
    )
    mission = MissionDefinition(title="Security policy test", summary="Confirm safety prompts.")
    orders = [
        StandingOrder(
            scope="privacy",
            instruction="Do not store raw credentials or unnecessary personal data.",
            effect="data_minimization_required",
        )
    ]
    policy = build_prompt_safety_policy(
        settings=settings,
        standing_orders=orders,
        mission=mission,
        role_name="Developer",
    ).text
    assert_contains(
        policy,
        [
            "Praetor safety and privacy policy",
            "Allowed write roots",
            "Denied write roots",
            "credentials",
            "raw voice transcripts",
            "external services",
            "Runtime path enforcement is authoritative",
        ],
    )

    api_prompt = build_generation_prompt(
        mission=mission,
        retrieval_contents={},
        safety_policy=policy,
    )
    assert_contains(api_prompt, ["Denied write roots", "Do not store raw credentials"])

    planner_prompt = LLMCEOPlanner._build_prompt(
        CEOPlannerContext(
            instruction="Send this file outside Praetor",
            related_mission_id=mission.id,
            mission_count=1,
            pending_approvals=0,
            safety_policy=policy,
        )
    )
    assert_contains(planner_prompt, ["decision_escalation", "external services", "chairman"])

    bridge_prompt = build_task_prompt(
        CreateRunRequest(
            request_id="req_test",
            mission_id=mission.id,
            task_id="task_test",
            executor="codex",
            timeout_seconds=60,
            path_mapping=PathMapping(
                container_workspace_root="/app/workspace",
                host_workspace_root=str(workspace),
                target_workdir="/app/workspace/Projects/Security",
            ),
            task_spec=TaskSpec(
                title="Bridge safety",
                instructions=policy,
                input_files=[],
                expected_outputs=["REPORT.md"],
                approval_policy=ApprovalPolicy(allow_destructive_write=False, allow_shell=False),
            ),
        ),
        str(workspace / "Projects" / "Security"),
    )
    assert_contains(bridge_prompt, ["Do not read or write outside", "Do not expose credentials"])
    if not contains_sensitive_material("api_key = sk-this_should_not_be_stored_1234567890"):
        raise AssertionError("Expected API key shaped text to be treated as sensitive.")
    assert_sensitive_memory_is_blocked(settings)


def assert_sensitive_memory_is_blocked(settings: AppSettings) -> None:
    state_dir = Path("/tmp/praetor-safety-policy-smoke-state")
    workspace = Path(settings.workspace.root)
    shutil.rmtree(state_dir, ignore_errors=True)
    shutil.rmtree(workspace, ignore_errors=True)
    bootstrap_workspace(workspace)
    storage = AppStorage(state_dir)
    storage.save_settings(settings)
    service = PraetorService(storage=storage)
    action = PlannerAction(
        type="memory_update",
        title="Unsafe memory",
        body="Remember this api_key = sk-this_should_not_be_stored_1234567890",
    )
    result = service._apply_planner_action(action, action.body or "", None)
    if result.status != "skipped":
        raise AssertionError(f"Expected sensitive memory update to be skipped: {result}")
    if not storage.list_escalations():
        raise AssertionError("Expected sensitive memory update to create an escalation.")
    memory_page = workspace / "Wiki" / "CEO Memory.md"
    if memory_page.exists() and "sk-this_should_not_be_stored" in memory_page.read_text(encoding="utf-8"):
        raise AssertionError("Sensitive material was written to memory.")


def assert_contains(text: str, expected: list[str]) -> None:
    missing = [item for item in expected if item not in text]
    if missing:
        raise AssertionError(f"Missing expected text: {missing}")


if __name__ == "__main__":
    main()
