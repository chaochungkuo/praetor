from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Iterator

from .models import (
    AgentMessage,
    AgentInstance,
    AgentRoleSpec,
    AppSettings,
    ApprovalRequest,
    GovernanceReview,
    ClientRecord,
    ConversationMessage,
    DelegationRecord,
    DocumentRecord,
    EscalationRecord,
    KnowledgeUpdate,
    MemoryPromotionReview,
    MatterDecisionRecord,
    MatterRecord,
    MeetingRecord,
    MissionDefinition,
    MissionTeam,
    OpenQuestionRecord,
    OwnerAuthRecord,
    RunAttempt,
    StandingOrder,
    TaskDefinition,
    WorkflowContract,
    WorkspaceScope,
    WorkSession,
)


SAFE_ID_RE = re.compile(r"^[a-z][a-z0-9_]*_[a-f0-9]{12}$")


def validate_safe_id(value: str, *, label: str = "id") -> str:
    if not SAFE_ID_RE.fullmatch(value):
        raise ValueError(f"Invalid {label}.")
    return value


class SQLiteIndex:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS missions (
                    mission_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
        try:
            os.chmod(self.db_path, 0o600)
        except OSError:
            pass

    def save_settings(self, settings: AppSettings) -> None:
        payload = settings.model_dump_json(indent=2)
        updated_at = settings.updated_at.isoformat()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO settings (id, payload_json, updated_at)
                VALUES (1, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    payload_json = excluded.payload_json,
                    updated_at = excluded.updated_at
                """,
                (payload, updated_at),
            )

    def load_settings(self) -> AppSettings | None:
        with self.connect() as conn:
            row = conn.execute("SELECT payload_json FROM settings WHERE id = 1").fetchone()
        if row is None:
            return None
        return AppSettings.model_validate_json(row["payload_json"])

    def upsert_mission(self, mission: MissionDefinition) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO missions (mission_id, title, status, priority, updated_at, payload_json)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(mission_id) DO UPDATE SET
                    title = excluded.title,
                    status = excluded.status,
                    priority = excluded.priority,
                    updated_at = excluded.updated_at,
                    payload_json = excluded.payload_json
                """,
                (
                    mission.id,
                    mission.title,
                    mission.status,
                    mission.priority,
                    mission.updated_at.isoformat(),
                    mission.model_dump_json(indent=2),
                ),
            )

    def list_missions(self) -> list[MissionDefinition]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT payload_json FROM missions ORDER BY updated_at DESC, mission_id DESC"
            ).fetchall()
        return [MissionDefinition.model_validate_json(row["payload_json"]) for row in rows]


class FilesystemStore:
    def __init__(self, state_dir: Path) -> None:
        self.state_dir = state_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.settings_path = self.state_dir / "settings.json"
        self.auth_path = self.state_dir / "auth.json"
        self.audit_path = self.state_dir / "audit.jsonl"
        self.approvals_path = self.state_dir / "approvals.json"
        self.governance_reviews_path = self.state_dir / "governance_reviews.json"
        self.conversation_path = self.state_dir / "office_conversation.json"
        self.agent_messages_path = self.state_dir / "agent_messages.json"
        self.work_sessions_path = self.state_dir / "work_sessions.json"
        self.run_attempts_path = self.state_dir / "run_attempts.json"
        self.clients_path = self.state_dir / "clients.json"
        self.matters_path = self.state_dir / "matters.json"
        self.documents_path = self.state_dir / "documents.json"
        self.matter_decisions_path = self.state_dir / "matter_decisions.json"
        self.open_questions_path = self.state_dir / "open_questions.json"
        self.knowledge_updates_path = self.state_dir / "knowledge_updates.json"
        self.memory_promotion_reviews_path = self.state_dir / "memory_promotion_reviews.json"
        self.agent_roles_path = self.state_dir / "agent_roles.json"
        self.agents_path = self.state_dir / "agents.json"
        self.teams_path = self.state_dir / "mission_teams.json"
        self.delegations_path = self.state_dir / "delegations.json"
        self.escalations_path = self.state_dir / "escalations.json"
        self.standing_orders_path = self.state_dir / "standing_orders.json"

    def save_settings(self, settings: AppSettings) -> None:
        _write_private_text(self.settings_path, settings.model_dump_json(indent=2))

    def load_settings(self) -> AppSettings | None:
        if not self.settings_path.exists():
            return None
        return AppSettings.model_validate_json(self.settings_path.read_text(encoding="utf-8"))

    def save_auth(self, auth_record: OwnerAuthRecord) -> None:
        _write_private_text(self.auth_path, auth_record.model_dump_json(indent=2))

    def load_auth(self) -> OwnerAuthRecord | None:
        if not self.auth_path.exists():
            return None
        return OwnerAuthRecord.model_validate_json(self.auth_path.read_text(encoding="utf-8"))

    def mission_dir(self, workspace_root: Path, mission_id: str) -> Path:
        validate_safe_id(mission_id, label="mission_id")
        return workspace_root / "Missions" / mission_id

    def meeting_dir(self, workspace_root: Path, mission_id: str) -> Path:
        return self.mission_dir(workspace_root, mission_id) / "meetings"

    def save_mission(self, workspace_root: Path, mission: MissionDefinition) -> Path:
        mission_dir = self.mission_dir(workspace_root, mission.id)
        logs_dir = mission_dir / "logs"
        mission_dir.mkdir(parents=True, exist_ok=True)
        logs_dir.mkdir(parents=True, exist_ok=True)

        _write_workspace_text(
            mission_dir / "mission.json",
            mission.model_dump_json(indent=2),
        )
        _write_workspace_text(
            mission_dir / "MISSION.md",
            f"# {mission.title}\n\nStatus: {mission.status}\n\n"
            f"Summary: {mission.summary or ''}\n",
        )
        _write_workspace_text(
            mission_dir / "STATUS.md",
            f"# Status\n\n- status: {mission.status}\n- priority: {mission.priority}\n",
        )
        _write_workspace_text(mission_dir / "TASKS.md", "# Tasks\n\n")
        _write_workspace_text(mission_dir / "DECISIONS.md", "# Decisions\n\n")
        _write_workspace_text(mission_dir / "CONTEXT.md", "# Context\n\n")
        _write_workspace_text(mission_dir / "PM_REPORT.md", "# PM Report\n\n")
        _write_workspace_text(mission_dir / "REPORT.md", "# Report\n\n")
        return mission_dir

    def save_task(self, workspace_root: Path, task: TaskDefinition) -> Path:
        mission_dir = self.mission_dir(workspace_root, task.mission_id)
        mission_dir.mkdir(parents=True, exist_ok=True)
        tasks_dir = mission_dir / "logs"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        path = tasks_dir / f"{task.id}.task.json"
        validate_safe_id(task.id, label="task_id")
        _write_workspace_text(path, task.model_dump_json(indent=2))
        return path

    def append_report(
        self,
        workspace_root: Path,
        mission_id: str,
        text: str,
    ) -> None:
        mission_dir = self.mission_dir(workspace_root, mission_id)
        report = mission_dir / "REPORT.md"
        existing = report.read_text(encoding="utf-8") if report.exists() else "# Report\n\n"
        _write_workspace_text(report, existing.rstrip() + "\n\n" + text.strip() + "\n")

    def append_pm_report(
        self,
        workspace_root: Path,
        mission_id: str,
        text: str,
    ) -> None:
        mission_dir = self.mission_dir(workspace_root, mission_id)
        report = mission_dir / "PM_REPORT.md"
        existing = report.read_text(encoding="utf-8") if report.exists() else "# PM Report\n\n"
        _write_workspace_text(report, existing.rstrip() + "\n\n" + text.strip() + "\n")

    def load_mission(self, workspace_root: Path, mission_id: str) -> MissionDefinition | None:
        path = self.mission_dir(workspace_root, mission_id) / "mission.json"
        if not path.exists():
            return None
        return MissionDefinition.model_validate_json(path.read_text(encoding="utf-8"))

    def list_tasks(self, workspace_root: Path, mission_id: str) -> list[TaskDefinition]:
        tasks_dir = self.mission_dir(workspace_root, mission_id) / "logs"
        if not tasks_dir.exists():
            return []
        tasks: list[TaskDefinition] = []
        for path in sorted(tasks_dir.glob("*.task.json")):
            try:
                tasks.append(TaskDefinition.model_validate_json(path.read_text(encoding="utf-8")))
            except Exception:
                continue
        return tasks

    def read_mission_texts(self, workspace_root: Path, mission_id: str) -> dict[str, str]:
        mission_dir = self.mission_dir(workspace_root, mission_id)
        texts: dict[str, str] = {}
        for name in ["MISSION.md", "STATUS.md", "TASKS.md", "DECISIONS.md", "CONTEXT.md", "PM_REPORT.md", "REPORT.md"]:
            path = mission_dir / name
            texts[name] = path.read_text(encoding="utf-8") if path.exists() else ""
        return texts

    def save_bridge_run(self, workspace_root: Path, mission_id: str, payload: dict) -> Path:
        mission_dir = self.mission_dir(workspace_root, mission_id)
        logs_dir = mission_dir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        run_id = payload.get("run_id", "unknown")
        validate_safe_id(str(run_id), label="run_id")
        path = logs_dir / f"{run_id}.bridge.json"
        _write_workspace_text(path, json.dumps(payload, indent=2, ensure_ascii=True))
        return path

    def list_bridge_runs(self, workspace_root: Path, mission_id: str) -> list[dict]:
        logs_dir = self.mission_dir(workspace_root, mission_id) / "logs"
        if not logs_dir.exists():
            return []
        runs: list[dict] = []
        for path in sorted(logs_dir.glob("*.bridge.json")):
            try:
                runs.append(json.loads(path.read_text(encoding="utf-8")))
            except Exception:
                continue
        runs.sort(key=lambda item: item.get("finished_at") or item.get("started_at") or "", reverse=True)
        return runs

    def list_recent_runs(self, workspace_root: Path, limit: int = 25) -> list[dict]:
        missions_root = workspace_root / "Missions"
        if not missions_root.exists():
            return []
        runs: list[dict] = []
        for path in missions_root.glob("*/logs/*.bridge.json"):
            try:
                runs.append(json.loads(path.read_text(encoding="utf-8")))
            except Exception:
                continue
        runs.sort(key=lambda item: item.get("finished_at") or item.get("started_at") or "", reverse=True)
        return runs[:limit]

    def append_audit_event(self, payload: dict) -> None:
        with self.audit_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=True) + "\n")
        try:
            os.chmod(self.audit_path, 0o600)
        except OSError:
            pass

    def list_audit_events(self, limit: int = 50) -> list[dict]:
        if not self.audit_path.exists():
            return []
        lines = self.audit_path.read_text(encoding="utf-8").splitlines()
        events: list[dict] = []
        for line in lines[-limit:]:
            try:
                events.append(json.loads(line))
            except Exception:
                continue
        events.reverse()
        return events

    def list_missions(self, workspace_root: Path) -> list[MissionDefinition]:
        missions_root = workspace_root / "Missions"
        if not missions_root.exists():
            return []
        missions: list[MissionDefinition] = []
        for path in sorted(missions_root.glob("*/mission.json")):
            try:
                missions.append(MissionDefinition.model_validate_json(path.read_text(encoding="utf-8")))
            except Exception:
                continue
        missions.sort(key=lambda item: item.updated_at, reverse=True)
        return missions

    def list_wiki_pages(self, workspace_root: Path) -> list[dict[str, str]]:
        wiki_root = workspace_root / "Wiki"
        if not wiki_root.exists():
            return []
        pages: list[dict[str, str]] = []
        for path in sorted(wiki_root.glob("*.md")):
            pages.append(
                {
                    "name": path.name,
                    "path": str(path.relative_to(workspace_root)),
                    "content": path.read_text(encoding="utf-8"),
                }
            )
        return pages

    def append_wiki_page(self, workspace_root: Path, page_name: str, text: str) -> Path:
        safe_name = page_name.replace("/", "-").replace("\\", "-").strip() or "CEO Memory.md"
        if not safe_name.endswith(".md"):
            safe_name = f"{safe_name}.md"
        path = workspace_root / "Wiki" / safe_name
        existing = path.read_text(encoding="utf-8") if path.exists() else f"# {safe_name.removesuffix('.md')}\n\n"
        _write_workspace_text(path, existing.rstrip() + "\n\n" + text.strip() + "\n")
        return path

    def save_approval(self, approval: ApprovalRequest) -> None:
        approvals = self.list_approvals()
        approvals = [item for item in approvals if item.id != approval.id] + [approval]
        approvals.sort(key=lambda item: item.created_at, reverse=True)
        _write_private_text(
            self.approvals_path,
            json.dumps([item.model_dump(mode="json") for item in approvals], indent=2, ensure_ascii=True),
        )

    def list_approvals(self) -> list[ApprovalRequest]:
        if not self.approvals_path.exists():
            return []
        payload = json.loads(self.approvals_path.read_text(encoding="utf-8"))
        return [ApprovalRequest.model_validate(item) for item in payload]

    def save_governance_review(self, review: GovernanceReview) -> None:
        reviews = self.list_governance_reviews(limit=100)
        reviews = [item for item in reviews if item.id != review.id] + [review]
        reviews.sort(key=lambda item: item.created_at, reverse=True)
        self._write_model_list(self.governance_reviews_path, reviews)

    def list_governance_reviews(self, limit: int = 20) -> list[GovernanceReview]:
        reviews = self._read_model_list(self.governance_reviews_path, GovernanceReview)
        reviews.sort(key=lambda item: item.created_at, reverse=True)
        return reviews[:limit]

    def save_meeting(self, workspace_root: Path, meeting: MeetingRecord) -> Path:
        meetings_dir = self.meeting_dir(workspace_root, meeting.mission_id)
        meetings_dir.mkdir(parents=True, exist_ok=True)
        path = meetings_dir / f"{meeting.id}.meeting.json"
        validate_safe_id(meeting.id, label="meeting_id")
        _write_workspace_text(path, meeting.model_dump_json(indent=2))
        markdown = meetings_dir / f"{meeting.id}.md"
        _write_workspace_text(
            markdown,
            "\n".join(
                [
                    f"# Meeting {meeting.id}",
                    "",
                    f"Type: {meeting.type}",
                    f"Moderator: {meeting.moderator}",
                    "",
                    "## Agenda",
                    *[f"- {item}" for item in meeting.agenda],
                    "",
                    "## Outputs",
                    *[f"- {item}" for item in meeting.outputs],
                    "",
                ]
            ),
        )
        return path

    def list_meetings(self, workspace_root: Path, mission_id: str | None = None) -> list[MeetingRecord]:
        roots = []
        if mission_id is not None:
            roots = [self.meeting_dir(workspace_root, mission_id)]
        else:
            roots = list((workspace_root / "Missions").glob("*/meetings"))
        meetings: list[MeetingRecord] = []
        for root in roots:
            if not root.exists():
                continue
            for path in sorted(root.glob("*.meeting.json")):
                try:
                    meetings.append(MeetingRecord.model_validate_json(path.read_text(encoding="utf-8")))
                except Exception:
                    continue
        meetings.sort(key=lambda item: item.created_at, reverse=True)
        return meetings

    def append_conversation_message(self, message: ConversationMessage) -> None:
        messages = self.list_conversation_messages()
        messages.append(message)
        _write_private_text(
            self.conversation_path,
            json.dumps([item.model_dump(mode="json") for item in messages], indent=2, ensure_ascii=True),
        )

    def list_conversation_messages(self, limit: int = 50) -> list[ConversationMessage]:
        if not self.conversation_path.exists():
            return []
        payload = json.loads(self.conversation_path.read_text(encoding="utf-8"))
        messages = [ConversationMessage.model_validate(item) for item in payload]
        return messages[-limit:]

    def append_agent_message(self, message: AgentMessage) -> None:
        messages = self.list_agent_messages(limit=10_000)
        messages.append(message)
        _write_private_text(
            self.agent_messages_path,
            json.dumps([item.model_dump(mode="json") for item in messages], indent=2, ensure_ascii=True),
        )

    def list_agent_messages(self, mission_id: str | None = None, limit: int = 50) -> list[AgentMessage]:
        if not self.agent_messages_path.exists():
            return []
        payload = json.loads(self.agent_messages_path.read_text(encoding="utf-8"))
        messages = [AgentMessage.model_validate(item) for item in payload]
        if mission_id is not None:
            messages = [item for item in messages if item.mission_id == mission_id]
        messages.sort(key=lambda item: item.created_at)
        return messages[-limit:]

    def save_work_session(self, session: WorkSession) -> None:
        sessions = self.list_work_sessions(limit=10_000)
        sessions = [item for item in sessions if item.id != session.id] + [session]
        sessions.sort(key=lambda item: item.updated_at, reverse=True)
        _write_private_text(
            self.work_sessions_path,
            json.dumps([item.model_dump(mode="json") for item in sessions], indent=2, ensure_ascii=True),
        )

    def list_work_sessions(self, mission_id: str | None = None, limit: int = 50) -> list[WorkSession]:
        if not self.work_sessions_path.exists():
            return []
        payload = json.loads(self.work_sessions_path.read_text(encoding="utf-8"))
        sessions = [WorkSession.model_validate(item) for item in payload]
        if mission_id is not None:
            sessions = [item for item in sessions if item.mission_id == mission_id]
        sessions.sort(key=lambda item: item.updated_at, reverse=True)
        return sessions[:limit]

    def save_run_attempt(self, attempt: RunAttempt) -> None:
        attempts = self.list_run_attempts(limit=10_000)
        attempts = [item for item in attempts if item.id != attempt.id] + [attempt]
        attempts.sort(key=lambda item: item.updated_at, reverse=True)
        self._write_model_list(self.run_attempts_path, attempts)

    def list_run_attempts(self, mission_id: str | None = None, limit: int = 50) -> list[RunAttempt]:
        attempts = self._read_model_list(self.run_attempts_path, RunAttempt)
        if mission_id is not None:
            attempts = [item for item in attempts if item.mission_id == mission_id]
        attempts.sort(key=lambda item: item.updated_at, reverse=True)
        return attempts[:limit]

    def save_client(self, workspace_root: Path, client: ClientRecord) -> None:
        clients = self.list_clients()
        clients = [item for item in clients if item.id != client.id and item.slug != client.slug] + [client]
        clients.sort(key=lambda item: item.name.lower())
        self._write_model_list(self.clients_path, clients)
        client_dir = workspace_root / client.folder
        _write_workspace_text(
            client_dir / "profile.md",
            "\n".join(
                [
                    f"# {client.name}",
                    "",
                    client.summary or "Client profile managed by Praetor.",
                    "",
                ]
            ),
        )
        _write_workspace_text(
            client_dir / "knowledge.md",
            f"# {client.name} Knowledge\n\nStable, confirmed knowledge about this client belongs here.\n",
        )

    def list_clients(self) -> list[ClientRecord]:
        return self._read_model_list(self.clients_path, ClientRecord)

    def save_matter(self, workspace_root: Path, matter: MatterRecord) -> None:
        matters = self.list_matters()
        matters = [item for item in matters if item.id != matter.id] + [matter]
        matters.sort(key=lambda item: item.updated_at, reverse=True)
        self._write_model_list(self.matters_path, matters)
        matter_dir = workspace_root / matter.folder
        _write_workspace_text(
            workspace_root / matter.brief_path,
            f"# {matter.title}\n\nStatus: {matter.status}\n\n",
        )
        _write_workspace_text(workspace_root / matter.decisions_path, "# Decisions\n\n")
        _write_workspace_text(workspace_root / matter.open_questions_path, "# Open Questions\n\n")
        for name in ["documents", "versions", "sources"]:
            (matter_dir / name).mkdir(parents=True, exist_ok=True)
        registry = {
            "matter_id": matter.id,
            "client_id": matter.client_id,
            "mission_id": matter.mission_id,
            "title": matter.title,
            "status": matter.status,
        }
        _write_workspace_text(
            matter_dir / "registry.json",
            json.dumps(registry, indent=2, ensure_ascii=True),
        )

    def save_workspace_scope(self, workspace_root: Path, scope: WorkspaceScope) -> Path:
        path = self.mission_dir(workspace_root, scope.mission_id) / "workspace_scope.json"
        _write_workspace_text(path, scope.model_dump_json(indent=2))
        return path

    def load_workspace_scope(self, workspace_root: Path, mission_id: str) -> WorkspaceScope | None:
        path = self.mission_dir(workspace_root, mission_id) / "workspace_scope.json"
        if not path.exists():
            return None
        return WorkspaceScope.model_validate_json(path.read_text(encoding="utf-8"))

    def load_workflow_contract(self, workspace_root: Path) -> WorkflowContract:
        path = workspace_root / "PRAETOR_WORKFLOW.md"
        body = path.read_text(encoding="utf-8") if path.exists() else ""
        return WorkflowContract(
            path=str(path.relative_to(workspace_root)) if path.exists() else "PRAETOR_WORKFLOW.md",
            body=body,
            default_completion_contract=[
                "requested outputs are present or explicitly waived",
                "documents are registered with version reasons",
                "open questions are resolved or marked non-blocking",
                "required approvals and reviews are complete",
                "final report and knowledge promotion state are recorded",
            ],
            approval_policy={
                "destructive_write": "escalate",
                "external_communication": "escalate",
                "privacy_sensitive_memory": "escalate",
            },
            workspace_policy={
                "default_write_scope": "mission_or_matter_workspace",
                "workflow_file": "PRAETOR_WORKFLOW.md",
            },
        )

    def list_matters(self, client_id: str | None = None, mission_id: str | None = None) -> list[MatterRecord]:
        matters = self._read_model_list(self.matters_path, MatterRecord)
        if client_id is not None:
            matters = [item for item in matters if item.client_id == client_id]
        if mission_id is not None:
            matters = [item for item in matters if item.mission_id == mission_id]
        return matters

    def save_document(self, document: DocumentRecord) -> None:
        documents = self.list_documents()
        documents = [item for item in documents if item.id != document.id] + [document]
        documents.sort(key=lambda item: item.updated_at, reverse=True)
        self._write_model_list(self.documents_path, documents)

    def list_documents(self, matter_id: str | None = None, mission_id: str | None = None) -> list[DocumentRecord]:
        documents = self._read_model_list(self.documents_path, DocumentRecord)
        if matter_id is not None:
            documents = [item for item in documents if item.matter_id == matter_id]
        if mission_id is not None:
            documents = [item for item in documents if item.mission_id == mission_id]
        return documents

    def save_matter_decision(self, workspace_root: Path, decision: MatterDecisionRecord) -> None:
        decisions = self.list_matter_decisions()
        decisions = [item for item in decisions if item.id != decision.id] + [decision]
        decisions.sort(key=lambda item: item.created_at, reverse=True)
        self._write_model_list(self.matter_decisions_path, decisions)
        matter = next((item for item in self.list_matters() if item.id == decision.matter_id), None)
        if matter is not None:
            path = workspace_root / matter.decisions_path
            existing = path.read_text(encoding="utf-8") if path.exists() else "# Decisions\n\n"
            text = f"- {decision.summary}"
            if decision.rationale:
                text += f" Reason: {decision.rationale}"
            _write_workspace_text(path, existing.rstrip() + "\n" + text + "\n")

    def list_matter_decisions(self, matter_id: str | None = None, mission_id: str | None = None) -> list[MatterDecisionRecord]:
        decisions = self._read_model_list(self.matter_decisions_path, MatterDecisionRecord)
        if matter_id is not None:
            decisions = [item for item in decisions if item.matter_id == matter_id]
        if mission_id is not None:
            decisions = [item for item in decisions if item.mission_id == mission_id]
        return decisions

    def save_open_question(self, workspace_root: Path, question: OpenQuestionRecord) -> None:
        questions = self.list_open_questions()
        questions = [item for item in questions if item.id != question.id] + [question]
        questions.sort(key=lambda item: item.asked_at, reverse=True)
        self._write_model_list(self.open_questions_path, questions)
        matter = next((item for item in self.list_matters() if item.id == question.matter_id), None)
        if matter is not None:
            path = workspace_root / matter.open_questions_path
            existing = path.read_text(encoding="utf-8") if path.exists() else "# Open Questions\n\n"
            blocking = f" Blocking: {question.blocking}" if question.blocking else ""
            _write_workspace_text(path, existing.rstrip() + f"\n- [{question.status}] {question.question}{blocking}\n")

    def list_open_questions(
        self,
        matter_id: str | None = None,
        mission_id: str | None = None,
        status: str | None = None,
    ) -> list[OpenQuestionRecord]:
        questions = self._read_model_list(self.open_questions_path, OpenQuestionRecord)
        if matter_id is not None:
            questions = [item for item in questions if item.matter_id == matter_id]
        if mission_id is not None:
            questions = [item for item in questions if item.mission_id == mission_id]
        if status is not None:
            questions = [item for item in questions if item.status == status]
        return questions

    def save_knowledge_update(self, update: KnowledgeUpdate) -> None:
        updates = self.list_knowledge_updates()
        updates = [item for item in updates if item.id != update.id] + [update]
        updates.sort(key=lambda item: item.created_at, reverse=True)
        self._write_model_list(self.knowledge_updates_path, updates)

    def list_knowledge_updates(
        self,
        matter_id: str | None = None,
        mission_id: str | None = None,
        status: str | None = None,
    ) -> list[KnowledgeUpdate]:
        updates = self._read_model_list(self.knowledge_updates_path, KnowledgeUpdate)
        if matter_id is not None:
            updates = [item for item in updates if item.matter_id == matter_id]
        if mission_id is not None:
            updates = [item for item in updates if item.mission_id == mission_id]
        if status is not None:
            updates = [item for item in updates if item.status == status]
        return updates

    def save_memory_promotion_review(self, review: MemoryPromotionReview) -> None:
        reviews = self.list_memory_promotion_reviews(limit=10_000)
        reviews = [item for item in reviews if item.id != review.id] + [review]
        reviews.sort(key=lambda item: item.updated_at, reverse=True)
        self._write_model_list(self.memory_promotion_reviews_path, reviews)

    def list_memory_promotion_reviews(
        self,
        mission_id: str | None = None,
        limit: int = 50,
    ) -> list[MemoryPromotionReview]:
        reviews = self._read_model_list(self.memory_promotion_reviews_path, MemoryPromotionReview)
        if mission_id is not None:
            reviews = [item for item in reviews if item.mission_id == mission_id]
        reviews.sort(key=lambda item: item.updated_at, reverse=True)
        return reviews[:limit]

    def save_agent_role(self, role: AgentRoleSpec) -> None:
        roles = self.list_agent_roles()
        roles = [item for item in roles if item.id != role.id and item.name != role.name] + [role]
        roles.sort(key=lambda item: item.name.lower())
        self._write_model_list(self.agent_roles_path, roles)

    def list_agent_roles(self) -> list[AgentRoleSpec]:
        return self._read_model_list(self.agent_roles_path, AgentRoleSpec)

    def save_agent(self, agent: AgentInstance) -> None:
        agents = self.list_agents()
        agents = [item for item in agents if item.id != agent.id] + [agent]
        agents.sort(key=lambda item: item.created_at, reverse=True)
        self._write_model_list(self.agents_path, agents)

    def list_agents(self, mission_id: str | None = None) -> list[AgentInstance]:
        agents = self._read_model_list(self.agents_path, AgentInstance)
        if mission_id is not None:
            agents = [item for item in agents if item.mission_id == mission_id]
        return agents

    def save_team(self, team: MissionTeam) -> None:
        teams = self.list_teams()
        teams = [item for item in teams if item.id != team.id and item.mission_id != team.mission_id] + [team]
        teams.sort(key=lambda item: item.updated_at, reverse=True)
        self._write_model_list(self.teams_path, teams)

    def list_teams(self, mission_id: str | None = None) -> list[MissionTeam]:
        teams = self._read_model_list(self.teams_path, MissionTeam)
        if mission_id is not None:
            teams = [item for item in teams if item.mission_id == mission_id]
        return teams

    def save_delegation(self, delegation: DelegationRecord) -> None:
        delegations = self.list_delegations()
        delegations = [item for item in delegations if item.id != delegation.id] + [delegation]
        delegations.sort(key=lambda item: item.updated_at, reverse=True)
        self._write_model_list(self.delegations_path, delegations)

    def list_delegations(self, mission_id: str | None = None) -> list[DelegationRecord]:
        delegations = self._read_model_list(self.delegations_path, DelegationRecord)
        if mission_id is not None:
            delegations = [item for item in delegations if item.mission_id == mission_id]
        return delegations

    def save_escalation(self, escalation: EscalationRecord) -> None:
        escalations = self.list_escalations()
        escalations = [item for item in escalations if item.id != escalation.id] + [escalation]
        escalations.sort(key=lambda item: item.created_at, reverse=True)
        self._write_model_list(self.escalations_path, escalations)

    def list_escalations(self, mission_id: str | None = None, status: str | None = None) -> list[EscalationRecord]:
        escalations = self._read_model_list(self.escalations_path, EscalationRecord)
        if mission_id is not None:
            escalations = [item for item in escalations if item.mission_id == mission_id]
        if status is not None:
            escalations = [item for item in escalations if item.status == status]
        return escalations

    def save_standing_order(self, order: StandingOrder) -> None:
        orders = self.list_standing_orders()
        orders = [item for item in orders if item.id != order.id] + [order]
        orders.sort(key=lambda item: item.updated_at, reverse=True)
        self._write_model_list(self.standing_orders_path, orders)

    def list_standing_orders(self) -> list[StandingOrder]:
        return self._read_model_list(self.standing_orders_path, StandingOrder)

    @staticmethod
    def _write_model_list(path: Path, items: list) -> None:
        _write_private_text(
            path,
            json.dumps([item.model_dump(mode="json") for item in items], indent=2, ensure_ascii=True),
        )

    @staticmethod
    def _read_model_list(path: Path, model) -> list:
        if not path.exists():
            return []
        payload = json.loads(path.read_text(encoding="utf-8"))
        return [model.model_validate(item) for item in payload]


class AppStorage:
    def __init__(self, state_dir: Path) -> None:
        self.fs = FilesystemStore(state_dir)
        self.index = SQLiteIndex(state_dir / "index.sqlite3")

    def save_settings(self, settings: AppSettings) -> None:
        self.fs.save_settings(settings)
        self.index.save_settings(settings)

    def save_auth(self, auth_record: OwnerAuthRecord) -> None:
        self.fs.save_auth(auth_record)

    def load_auth(self) -> OwnerAuthRecord | None:
        return self.fs.load_auth()

    def load_settings(self) -> AppSettings | None:
        settings = self.fs.load_settings()
        if settings is not None:
            self.index.save_settings(settings)
            return settings
        return self.index.load_settings()

    def save_mission(self, workspace_root: Path, mission: MissionDefinition) -> Path:
        path = self.fs.save_mission(workspace_root, mission)
        self.index.upsert_mission(mission)
        return path

    def load_mission(self, workspace_root: Path, mission_id: str) -> MissionDefinition | None:
        mission = self.fs.load_mission(workspace_root, mission_id)
        if mission is not None:
            self.index.upsert_mission(mission)
            return mission
        return None

    def list_missions(self, workspace_root: Path) -> list[MissionDefinition]:
        missions = self.fs.list_missions(workspace_root)
        if missions:
            for mission in missions:
                self.index.upsert_mission(mission)
            return missions
        return self.index.list_missions()

    def save_task(self, workspace_root: Path, task: TaskDefinition) -> Path:
        return self.fs.save_task(workspace_root, task)

    def append_report(self, workspace_root: Path, mission_id: str, text: str) -> None:
        self.fs.append_report(workspace_root, mission_id, text)

    def append_pm_report(self, workspace_root: Path, mission_id: str, text: str) -> None:
        self.fs.append_pm_report(workspace_root, mission_id, text)

    def list_tasks(self, workspace_root: Path, mission_id: str) -> list[TaskDefinition]:
        return self.fs.list_tasks(workspace_root, mission_id)

    def read_mission_texts(self, workspace_root: Path, mission_id: str) -> dict[str, str]:
        return self.fs.read_mission_texts(workspace_root, mission_id)

    def save_bridge_run(self, workspace_root: Path, mission_id: str, payload: dict) -> Path:
        return self.fs.save_bridge_run(workspace_root, mission_id, payload)

    def list_bridge_runs(self, workspace_root: Path, mission_id: str) -> list[dict]:
        return self.fs.list_bridge_runs(workspace_root, mission_id)

    def list_recent_runs(self, workspace_root: Path, limit: int = 25) -> list[dict]:
        return self.fs.list_recent_runs(workspace_root, limit=limit)

    def list_wiki_pages(self, workspace_root: Path) -> list[dict[str, str]]:
        return self.fs.list_wiki_pages(workspace_root)

    def append_wiki_page(self, workspace_root: Path, page_name: str, text: str) -> Path:
        return self.fs.append_wiki_page(workspace_root, page_name, text)

    def save_meeting(self, workspace_root: Path, meeting: MeetingRecord) -> Path:
        return self.fs.save_meeting(workspace_root, meeting)

    def list_meetings(self, workspace_root: Path, mission_id: str | None = None) -> list[MeetingRecord]:
        return self.fs.list_meetings(workspace_root, mission_id=mission_id)

    def append_conversation_message(self, message: ConversationMessage) -> None:
        self.fs.append_conversation_message(message)

    def list_conversation_messages(self, limit: int = 50) -> list[ConversationMessage]:
        return self.fs.list_conversation_messages(limit=limit)

    def append_agent_message(self, message: AgentMessage) -> None:
        self.fs.append_agent_message(message)

    def list_agent_messages(self, mission_id: str | None = None, limit: int = 50) -> list[AgentMessage]:
        return self.fs.list_agent_messages(mission_id=mission_id, limit=limit)

    def save_work_session(self, session: WorkSession) -> None:
        self.fs.save_work_session(session)

    def list_work_sessions(self, mission_id: str | None = None, limit: int = 50) -> list[WorkSession]:
        return self.fs.list_work_sessions(mission_id=mission_id, limit=limit)

    def save_run_attempt(self, attempt: RunAttempt) -> None:
        self.fs.save_run_attempt(attempt)

    def list_run_attempts(self, mission_id: str | None = None, limit: int = 50) -> list[RunAttempt]:
        return self.fs.list_run_attempts(mission_id=mission_id, limit=limit)

    def save_client(self, workspace_root: Path, client: ClientRecord) -> None:
        self.fs.save_client(workspace_root, client)

    def list_clients(self) -> list[ClientRecord]:
        return self.fs.list_clients()

    def save_matter(self, workspace_root: Path, matter: MatterRecord) -> None:
        self.fs.save_matter(workspace_root, matter)

    def list_matters(self, client_id: str | None = None, mission_id: str | None = None) -> list[MatterRecord]:
        return self.fs.list_matters(client_id=client_id, mission_id=mission_id)

    def save_workspace_scope(self, workspace_root: Path, scope: WorkspaceScope) -> Path:
        return self.fs.save_workspace_scope(workspace_root, scope)

    def load_workspace_scope(self, workspace_root: Path, mission_id: str) -> WorkspaceScope | None:
        return self.fs.load_workspace_scope(workspace_root, mission_id)

    def load_workflow_contract(self, workspace_root: Path) -> WorkflowContract:
        return self.fs.load_workflow_contract(workspace_root)

    def save_document(self, document: DocumentRecord) -> None:
        self.fs.save_document(document)

    def list_documents(self, matter_id: str | None = None, mission_id: str | None = None) -> list[DocumentRecord]:
        return self.fs.list_documents(matter_id=matter_id, mission_id=mission_id)

    def save_matter_decision(self, workspace_root: Path, decision: MatterDecisionRecord) -> None:
        self.fs.save_matter_decision(workspace_root, decision)

    def list_matter_decisions(
        self,
        matter_id: str | None = None,
        mission_id: str | None = None,
    ) -> list[MatterDecisionRecord]:
        return self.fs.list_matter_decisions(matter_id=matter_id, mission_id=mission_id)

    def save_open_question(self, workspace_root: Path, question: OpenQuestionRecord) -> None:
        self.fs.save_open_question(workspace_root, question)

    def list_open_questions(
        self,
        matter_id: str | None = None,
        mission_id: str | None = None,
        status: str | None = None,
    ) -> list[OpenQuestionRecord]:
        return self.fs.list_open_questions(matter_id=matter_id, mission_id=mission_id, status=status)

    def save_knowledge_update(self, update: KnowledgeUpdate) -> None:
        self.fs.save_knowledge_update(update)

    def list_knowledge_updates(
        self,
        matter_id: str | None = None,
        mission_id: str | None = None,
        status: str | None = None,
    ) -> list[KnowledgeUpdate]:
        return self.fs.list_knowledge_updates(matter_id=matter_id, mission_id=mission_id, status=status)

    def save_memory_promotion_review(self, review: MemoryPromotionReview) -> None:
        self.fs.save_memory_promotion_review(review)

    def list_memory_promotion_reviews(
        self,
        mission_id: str | None = None,
        limit: int = 50,
    ) -> list[MemoryPromotionReview]:
        return self.fs.list_memory_promotion_reviews(mission_id=mission_id, limit=limit)

    def save_agent_role(self, role: AgentRoleSpec) -> None:
        self.fs.save_agent_role(role)

    def list_agent_roles(self) -> list[AgentRoleSpec]:
        return self.fs.list_agent_roles()

    def save_agent(self, agent: AgentInstance) -> None:
        self.fs.save_agent(agent)

    def list_agents(self, mission_id: str | None = None) -> list[AgentInstance]:
        return self.fs.list_agents(mission_id=mission_id)

    def save_team(self, team: MissionTeam) -> None:
        self.fs.save_team(team)

    def list_teams(self, mission_id: str | None = None) -> list[MissionTeam]:
        return self.fs.list_teams(mission_id=mission_id)

    def save_delegation(self, delegation: DelegationRecord) -> None:
        self.fs.save_delegation(delegation)

    def list_delegations(self, mission_id: str | None = None) -> list[DelegationRecord]:
        return self.fs.list_delegations(mission_id=mission_id)

    def save_escalation(self, escalation: EscalationRecord) -> None:
        self.fs.save_escalation(escalation)

    def list_escalations(self, mission_id: str | None = None, status: str | None = None) -> list[EscalationRecord]:
        return self.fs.list_escalations(mission_id=mission_id, status=status)

    def save_standing_order(self, order: StandingOrder) -> None:
        self.fs.save_standing_order(order)

    def list_standing_orders(self) -> list[StandingOrder]:
        return self.fs.list_standing_orders()

    def save_approval(self, approval: ApprovalRequest) -> None:
        self.fs.save_approval(approval)

    def list_approvals(self) -> list[ApprovalRequest]:
        return self.fs.list_approvals()

    def save_governance_review(self, review: GovernanceReview) -> None:
        self.fs.save_governance_review(review)

    def list_governance_reviews(self, limit: int = 20) -> list[GovernanceReview]:
        return self.fs.list_governance_reviews(limit=limit)

    def append_audit_event(self, payload: dict) -> None:
        self.fs.append_audit_event(payload)

    def list_audit_events(self, limit: int = 50) -> list[dict]:
        return self.fs.list_audit_events(limit=limit)


def parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def write_json(path: Path, payload: dict) -> None:
    _write_private_text(path, json.dumps(payload, indent=2, ensure_ascii=True))


def _write_private_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _write_workspace_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
