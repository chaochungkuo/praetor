from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
import json
import os
import re
import sqlite3
import threading
from pathlib import Path
from typing import Any, Iterator

from .models import (
    AgentMessage,
    AgentInstance,
    AgentEmploymentContract,
    AgentPermissionProfile,
    AgentRoleSpec,
    AgentSkillSpec,
    AppSettings,
    ApprovalRequest,
    BoardBriefing,
    GovernanceReview,
    ClientRecord,
    ConversationMessage,
    DelegationRecord,
    DocumentRecord,
    EscalationRecord,
    ExecutiveCadence,
    ExecutorControlRecord,
    KnowledgeUpdate,
    MemoryPromotionReview,
    MatterDecisionRecord,
    MatterRecord,
    MeetingRecord,
    MissionDefinition,
    MissionJob,
    MissionStageTransition,
    MissionTeam,
    OpenQuestionRecord,
    OwnerAuthRecord,
    RunAttempt,
    StandingOrder,
    SkillSource,
    TaskDefinition,
    TeamTemplate,
    WorkflowContract,
    WorkspaceScope,
    WorkTraceEvent,
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
            conn.execute(
                "CREATE TABLE IF NOT EXISTS _migrations (table_name TEXT PRIMARY KEY, migrated_at TEXT NOT NULL)"
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS approvals (
                    id TEXT PRIMARY KEY,
                    mission_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_approvals_status ON approvals(status)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS governance_reviews (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation_messages (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_messages (
                    id TEXT PRIMARY KEY,
                    mission_id TEXT,
                    created_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_messages_mission ON agent_messages(mission_id)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS work_sessions (
                    id TEXT PRIMARY KEY,
                    mission_id TEXT,
                    updated_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_work_sessions_mission ON work_sessions(mission_id)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS run_attempts (
                    id TEXT PRIMARY KEY,
                    mission_id TEXT,
                    updated_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_run_attempts_mission ON run_attempts(mission_id)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS mission_jobs (
                    id TEXT PRIMARY KEY,
                    mission_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    enqueued_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_mission_jobs_mission ON mission_jobs(mission_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_mission_jobs_status ON mission_jobs(status, enqueued_at)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS clients (
                    id TEXT PRIMARY KEY,
                    slug TEXT NOT NULL,
                    name TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_clients_slug ON clients(slug)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS matters (
                    id TEXT PRIMARY KEY,
                    client_id TEXT,
                    mission_id TEXT,
                    updated_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_matters_client ON matters(client_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_matters_mission ON matters(mission_id)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    matter_id TEXT,
                    mission_id TEXT,
                    updated_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_matter ON documents(matter_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_mission ON documents(mission_id)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS matter_decisions (
                    id TEXT PRIMARY KEY,
                    matter_id TEXT,
                    mission_id TEXT,
                    created_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_matter_decisions_matter ON matter_decisions(matter_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_matter_decisions_mission ON matter_decisions(mission_id)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS open_questions (
                    id TEXT PRIMARY KEY,
                    matter_id TEXT,
                    mission_id TEXT,
                    status TEXT,
                    asked_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_open_questions_matter ON open_questions(matter_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_open_questions_mission ON open_questions(mission_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_open_questions_status ON open_questions(status)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS knowledge_updates (
                    id TEXT PRIMARY KEY,
                    matter_id TEXT,
                    mission_id TEXT,
                    status TEXT,
                    created_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_updates_matter ON knowledge_updates(matter_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_updates_mission ON knowledge_updates(mission_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_updates_status ON knowledge_updates(status)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_promotion_reviews (
                    id TEXT PRIMARY KEY,
                    mission_id TEXT,
                    updated_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_mem_reviews_mission ON memory_promotion_reviews(mission_id)"
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS board_briefings (
                    id TEXT PRIMARY KEY,
                    mission_id TEXT,
                    updated_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_board_briefings_mission ON board_briefings(mission_id)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_roles (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_roles_name ON agent_roles(name)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS skill_sources (
                    id TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_skill_sources_url ON skill_sources(url)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_skills (
                    id TEXT PRIMARY KEY,
                    source_id TEXT,
                    source_path TEXT,
                    name TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_skills_source ON agent_skills(source_id)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS agents (
                    id TEXT PRIMARY KEY,
                    mission_id TEXT,
                    created_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_agents_mission ON agents(mission_id)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_permission_profiles (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_perm_profiles_name ON agent_permission_profiles(name)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_employment_contracts (
                    id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    mission_id TEXT,
                    updated_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_contracts_agent ON agent_employment_contracts(agent_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_contracts_mission ON agent_employment_contracts(mission_id)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS mission_teams (
                    id TEXT PRIMARY KEY,
                    mission_id TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_mission_teams_mission ON mission_teams(mission_id)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS team_templates (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_team_templates_name ON team_templates(name)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS mission_stage_transitions (
                    id TEXT PRIMARY KEY,
                    mission_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_stage_transitions_mission ON mission_stage_transitions(mission_id)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS work_trace_events (
                    id TEXT PRIMARY KEY,
                    mission_id TEXT,
                    created_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_work_trace_mission ON work_trace_events(mission_id)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS executor_controls (
                    id TEXT PRIMARY KEY,
                    mission_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_executor_controls_mission ON executor_controls(mission_id)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS executive_cadences (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_executive_cadences_name ON executive_cadences(name)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS delegations (
                    id TEXT PRIMARY KEY,
                    mission_id TEXT,
                    updated_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_delegations_mission ON delegations(mission_id)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS escalations (
                    id TEXT PRIMARY KEY,
                    mission_id TEXT,
                    status TEXT,
                    created_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_escalations_mission ON escalations(mission_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_escalations_status ON escalations(status)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS standing_orders (
                    id TEXT PRIMARY KEY,
                    updated_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS meetings (
                    id TEXT PRIMARY KEY,
                    mission_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_meetings_mission ON meetings(mission_id)")
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

    def get_mission(self, mission_id: str) -> MissionDefinition | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT payload_json FROM missions WHERE mission_id = ?", (mission_id,)
            ).fetchone()
        if row is None:
            return None
        return MissionDefinition.model_validate_json(row["payload_json"])

    # --- Meetings ---

    def upsert_meeting(self, meeting: MeetingRecord) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO meetings (id, mission_id, type, created_at, payload_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    meeting.id,
                    meeting.mission_id,
                    meeting.type,
                    meeting.created_at.isoformat(),
                    meeting.model_dump_json(indent=2),
                ),
            )

    def list_meetings(self, mission_id: str | None = None) -> list[MeetingRecord]:
        with self.connect() as conn:
            if mission_id is not None:
                rows = conn.execute(
                    "SELECT payload_json FROM meetings WHERE mission_id = ? ORDER BY created_at DESC",
                    (mission_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT payload_json FROM meetings ORDER BY created_at DESC"
                ).fetchall()
        return [MeetingRecord.model_validate_json(row["payload_json"]) for row in rows]

    # --- Migration tracking ---

    def is_migrated(self, table_name: str) -> bool:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM _migrations WHERE table_name = ?", (table_name,)
            ).fetchone()
        return row is not None

    def mark_migrated(self, table_name: str) -> None:
        now = datetime.utcnow().isoformat()
        with self.connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO _migrations (table_name, migrated_at) VALUES (?, ?)",
                (table_name, now),
            )

    # --- Approvals ---

    def upsert_approval(self, approval: ApprovalRequest) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO approvals (id, mission_id, status, created_at, payload_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    approval.id,
                    approval.mission_id,
                    approval.status,
                    approval.created_at.isoformat(),
                    approval.model_dump_json(indent=2),
                ),
            )

    def list_approvals(self) -> list[ApprovalRequest]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT payload_json FROM approvals ORDER BY created_at DESC"
            ).fetchall()
        return [ApprovalRequest.model_validate_json(row["payload_json"]) for row in rows]

    # --- GovernanceReviews ---

    def upsert_governance_review(self, review: GovernanceReview) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO governance_reviews (id, created_at, payload_json)
                VALUES (?, ?, ?)
                """,
                (review.id, review.created_at.isoformat(), review.model_dump_json(indent=2)),
            )

    def list_governance_reviews(self, limit: int = 20) -> list[GovernanceReview]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT payload_json FROM governance_reviews ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [GovernanceReview.model_validate_json(row["payload_json"]) for row in rows]

    # --- ConversationMessages ---

    def upsert_conversation_message(self, message: ConversationMessage) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO conversation_messages (id, created_at, payload_json)
                VALUES (?, ?, ?)
                """,
                (message.id, message.created_at.isoformat(), message.model_dump_json(indent=2)),
            )

    def list_conversation_messages(self, limit: int = 50) -> list[ConversationMessage]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT payload_json FROM (
                    SELECT payload_json, created_at FROM conversation_messages
                    ORDER BY created_at DESC LIMIT ?
                ) ORDER BY created_at ASC
                """,
                (limit,),
            ).fetchall()
        return [ConversationMessage.model_validate_json(row["payload_json"]) for row in rows]

    # --- AgentMessages ---

    def upsert_agent_message(self, message: AgentMessage) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO agent_messages (id, mission_id, created_at, payload_json)
                VALUES (?, ?, ?, ?)
                """,
                (
                    message.id,
                    message.mission_id,
                    message.created_at.isoformat(),
                    message.model_dump_json(indent=2),
                ),
            )

    def list_agent_messages(self, mission_id: str | None = None, limit: int = 50) -> list[AgentMessage]:
        with self.connect() as conn:
            if mission_id is not None:
                rows = conn.execute(
                    """
                    SELECT payload_json FROM (
                        SELECT payload_json, created_at FROM agent_messages WHERE mission_id = ?
                        ORDER BY created_at DESC LIMIT ?
                    ) ORDER BY created_at ASC
                    """,
                    (mission_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT payload_json FROM (
                        SELECT payload_json, created_at FROM agent_messages
                        ORDER BY created_at DESC LIMIT ?
                    ) ORDER BY created_at ASC
                    """,
                    (limit,),
                ).fetchall()
        return [AgentMessage.model_validate_json(row["payload_json"]) for row in rows]

    # --- WorkSessions ---

    def upsert_work_session(self, session: WorkSession) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO work_sessions (id, mission_id, updated_at, payload_json)
                VALUES (?, ?, ?, ?)
                """,
                (
                    session.id,
                    session.mission_id,
                    session.updated_at.isoformat(),
                    session.model_dump_json(indent=2),
                ),
            )

    def list_work_sessions(self, mission_id: str | None = None, limit: int = 50) -> list[WorkSession]:
        with self.connect() as conn:
            if mission_id is not None:
                rows = conn.execute(
                    "SELECT payload_json FROM work_sessions WHERE mission_id = ? ORDER BY updated_at DESC LIMIT ?",
                    (mission_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT payload_json FROM work_sessions ORDER BY updated_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return [WorkSession.model_validate_json(row["payload_json"]) for row in rows]

    # --- RunAttempts ---

    def upsert_run_attempt(self, attempt: RunAttempt) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO run_attempts (id, mission_id, updated_at, payload_json)
                VALUES (?, ?, ?, ?)
                """,
                (
                    attempt.id,
                    attempt.mission_id,
                    attempt.updated_at.isoformat(),
                    attempt.model_dump_json(indent=2),
                ),
            )

    def list_run_attempts(self, mission_id: str | None = None, limit: int = 50) -> list[RunAttempt]:
        with self.connect() as conn:
            if mission_id is not None:
                rows = conn.execute(
                    "SELECT payload_json FROM run_attempts WHERE mission_id = ? ORDER BY updated_at DESC LIMIT ?",
                    (mission_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT payload_json FROM run_attempts ORDER BY updated_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return [RunAttempt.model_validate_json(row["payload_json"]) for row in rows]

    # --- MissionJobs ---

    def upsert_mission_job(self, job: MissionJob) -> None:
        updated_at = (job.finished_at or job.started_at or job.enqueued_at).isoformat()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO mission_jobs (id, mission_id, status, enqueued_at, updated_at, payload_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    job.id,
                    job.mission_id,
                    job.status,
                    job.enqueued_at.isoformat(),
                    updated_at,
                    job.model_dump_json(indent=2),
                ),
            )

    def get_mission_job(self, job_id: str) -> MissionJob | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT payload_json FROM mission_jobs WHERE id = ?", (job_id,)
            ).fetchone()
        if row is None:
            return None
        return MissionJob.model_validate_json(row["payload_json"])

    def list_mission_jobs(self, mission_id: str | None = None, limit: int = 20) -> list[MissionJob]:
        with self.connect() as conn:
            if mission_id is not None:
                rows = conn.execute(
                    "SELECT payload_json FROM mission_jobs WHERE mission_id = ? ORDER BY enqueued_at DESC LIMIT ?",
                    (mission_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT payload_json FROM mission_jobs ORDER BY enqueued_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return [MissionJob.model_validate_json(row["payload_json"]) for row in rows]

    def claim_next_queued_mission_job(self) -> MissionJob | None:
        """Atomically transition the oldest queued job to running."""
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT payload_json FROM mission_jobs
                WHERE status = 'queued'
                ORDER BY enqueued_at ASC
                LIMIT 1
                """
            ).fetchone()
            if row is None:
                return None
            job = MissionJob.model_validate_json(row["payload_json"])
            now = datetime.utcnow()
            job.status = "running"
            job.started_at = now.replace(tzinfo=job.enqueued_at.tzinfo)
            updated = job.model_dump_json(indent=2)
            cursor = conn.execute(
                """
                UPDATE mission_jobs
                   SET status = 'running', updated_at = ?, payload_json = ?
                 WHERE id = ? AND status = 'queued'
                """,
                (job.started_at.isoformat(), updated, job.id),
            )
            if cursor.rowcount == 0:
                return None
        return job

    def reset_running_mission_jobs(self) -> int:
        """Mark any jobs still 'running' as 'interrupted' (called on app startup)."""
        count = 0
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT id, payload_json FROM mission_jobs WHERE status = 'running'"
            ).fetchall()
            for row in rows:
                job = MissionJob.model_validate_json(row["payload_json"])
                job.status = "interrupted"
                job.error = job.error or "API restarted while job was running."
                job.finished_at = datetime.utcnow().replace(tzinfo=job.enqueued_at.tzinfo)
                conn.execute(
                    "UPDATE mission_jobs SET status = 'interrupted', updated_at = ?, payload_json = ? WHERE id = ?",
                    (job.finished_at.isoformat(), job.model_dump_json(indent=2), job.id),
                )
                count += 1
        return count

    # --- Clients ---

    def upsert_client(self, client: ClientRecord) -> None:
        with self.connect() as conn:
            conn.execute(
                "DELETE FROM clients WHERE id != ? AND slug = ?", (client.id, client.slug)
            )
            conn.execute(
                """
                INSERT OR REPLACE INTO clients (id, slug, name, payload_json)
                VALUES (?, ?, ?, ?)
                """,
                (client.id, client.slug, client.name, client.model_dump_json(indent=2)),
            )

    def list_clients(self) -> list[ClientRecord]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT payload_json FROM clients ORDER BY name ASC"
            ).fetchall()
        return [ClientRecord.model_validate_json(row["payload_json"]) for row in rows]

    # --- Matters ---

    def get_matter(self, matter_id: str) -> MatterRecord | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT payload_json FROM matters WHERE id = ?", (matter_id,)
            ).fetchone()
        if row is None:
            return None
        return MatterRecord.model_validate_json(row["payload_json"])

    def upsert_matter(self, matter: MatterRecord) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO matters (id, client_id, mission_id, updated_at, payload_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    matter.id,
                    matter.client_id,
                    matter.mission_id,
                    matter.updated_at.isoformat(),
                    matter.model_dump_json(indent=2),
                ),
            )

    def list_matters(
        self, client_id: str | None = None, mission_id: str | None = None
    ) -> list[MatterRecord]:
        with self.connect() as conn:
            sql = "SELECT payload_json FROM matters WHERE 1=1"
            params: list = []
            if client_id is not None:
                sql += " AND client_id = ?"
                params.append(client_id)
            if mission_id is not None:
                sql += " AND mission_id = ?"
                params.append(mission_id)
            sql += " ORDER BY updated_at DESC"
            rows = conn.execute(sql, params).fetchall()
        return [MatterRecord.model_validate_json(row["payload_json"]) for row in rows]

    # --- Documents ---

    def upsert_document(self, document: DocumentRecord) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO documents (id, matter_id, mission_id, updated_at, payload_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    document.id,
                    document.matter_id,
                    document.mission_id,
                    document.updated_at.isoformat(),
                    document.model_dump_json(indent=2),
                ),
            )

    def list_documents(
        self, matter_id: str | None = None, mission_id: str | None = None
    ) -> list[DocumentRecord]:
        with self.connect() as conn:
            sql = "SELECT payload_json FROM documents WHERE 1=1"
            params: list = []
            if matter_id is not None:
                sql += " AND matter_id = ?"
                params.append(matter_id)
            if mission_id is not None:
                sql += " AND mission_id = ?"
                params.append(mission_id)
            sql += " ORDER BY updated_at DESC"
            rows = conn.execute(sql, params).fetchall()
        return [DocumentRecord.model_validate_json(row["payload_json"]) for row in rows]

    # --- MatterDecisions ---

    def upsert_matter_decision(self, decision: MatterDecisionRecord) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO matter_decisions (id, matter_id, mission_id, created_at, payload_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    decision.id,
                    decision.matter_id,
                    decision.mission_id,
                    decision.created_at.isoformat(),
                    decision.model_dump_json(indent=2),
                ),
            )

    def list_matter_decisions(
        self, matter_id: str | None = None, mission_id: str | None = None
    ) -> list[MatterDecisionRecord]:
        with self.connect() as conn:
            sql = "SELECT payload_json FROM matter_decisions WHERE 1=1"
            params: list = []
            if matter_id is not None:
                sql += " AND matter_id = ?"
                params.append(matter_id)
            if mission_id is not None:
                sql += " AND mission_id = ?"
                params.append(mission_id)
            sql += " ORDER BY created_at DESC"
            rows = conn.execute(sql, params).fetchall()
        return [MatterDecisionRecord.model_validate_json(row["payload_json"]) for row in rows]

    # --- OpenQuestions ---

    def upsert_open_question(self, question: OpenQuestionRecord) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO open_questions
                    (id, matter_id, mission_id, status, asked_at, payload_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    question.id,
                    question.matter_id,
                    question.mission_id,
                    question.status,
                    question.asked_at.isoformat(),
                    question.model_dump_json(indent=2),
                ),
            )

    def list_open_questions(
        self,
        matter_id: str | None = None,
        mission_id: str | None = None,
        status: str | None = None,
    ) -> list[OpenQuestionRecord]:
        with self.connect() as conn:
            sql = "SELECT payload_json FROM open_questions WHERE 1=1"
            params: list = []
            if matter_id is not None:
                sql += " AND matter_id = ?"
                params.append(matter_id)
            if mission_id is not None:
                sql += " AND mission_id = ?"
                params.append(mission_id)
            if status is not None:
                sql += " AND status = ?"
                params.append(status)
            sql += " ORDER BY asked_at DESC"
            rows = conn.execute(sql, params).fetchall()
        return [OpenQuestionRecord.model_validate_json(row["payload_json"]) for row in rows]

    # --- KnowledgeUpdates ---

    def upsert_knowledge_update(self, update: KnowledgeUpdate) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO knowledge_updates
                    (id, matter_id, mission_id, status, created_at, payload_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    update.id,
                    update.matter_id,
                    update.mission_id,
                    update.status,
                    update.created_at.isoformat(),
                    update.model_dump_json(indent=2),
                ),
            )

    def list_knowledge_updates(
        self,
        matter_id: str | None = None,
        mission_id: str | None = None,
        status: str | None = None,
    ) -> list[KnowledgeUpdate]:
        with self.connect() as conn:
            sql = "SELECT payload_json FROM knowledge_updates WHERE 1=1"
            params: list = []
            if matter_id is not None:
                sql += " AND matter_id = ?"
                params.append(matter_id)
            if mission_id is not None:
                sql += " AND mission_id = ?"
                params.append(mission_id)
            if status is not None:
                sql += " AND status = ?"
                params.append(status)
            sql += " ORDER BY created_at DESC"
            rows = conn.execute(sql, params).fetchall()
        return [KnowledgeUpdate.model_validate_json(row["payload_json"]) for row in rows]

    # --- MemoryPromotionReviews ---

    def upsert_memory_promotion_review(self, review: MemoryPromotionReview) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO memory_promotion_reviews (id, mission_id, updated_at, payload_json)
                VALUES (?, ?, ?, ?)
                """,
                (review.id, review.mission_id, review.updated_at.isoformat(), review.model_dump_json(indent=2)),
            )

    def list_memory_promotion_reviews(
        self, mission_id: str | None = None, limit: int = 50
    ) -> list[MemoryPromotionReview]:
        with self.connect() as conn:
            if mission_id is not None:
                rows = conn.execute(
                    """
                    SELECT payload_json FROM memory_promotion_reviews
                    WHERE mission_id = ? ORDER BY updated_at DESC LIMIT ?
                    """,
                    (mission_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT payload_json FROM memory_promotion_reviews ORDER BY updated_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return [MemoryPromotionReview.model_validate_json(row["payload_json"]) for row in rows]

    # --- BoardBriefings ---

    def upsert_board_briefing(self, briefing: BoardBriefing) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO board_briefings (id, mission_id, updated_at, payload_json)
                VALUES (?, ?, ?, ?)
                """,
                (
                    briefing.id,
                    briefing.mission_id,
                    briefing.updated_at.isoformat(),
                    briefing.model_dump_json(indent=2),
                ),
            )

    def list_board_briefings(self, mission_id: str | None = None, limit: int = 50) -> list[BoardBriefing]:
        with self.connect() as conn:
            if mission_id is not None:
                rows = conn.execute(
                    """
                    SELECT payload_json FROM board_briefings
                    WHERE mission_id = ? ORDER BY updated_at DESC LIMIT ?
                    """,
                    (mission_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT payload_json FROM board_briefings ORDER BY updated_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return [BoardBriefing.model_validate_json(row["payload_json"]) for row in rows]

    # --- AgentRoles ---

    def upsert_agent_role(self, role: AgentRoleSpec) -> None:
        with self.connect() as conn:
            conn.execute(
                "DELETE FROM agent_roles WHERE id != ? AND name = ?", (role.id, role.name)
            )
            conn.execute(
                "INSERT OR REPLACE INTO agent_roles (id, name, payload_json) VALUES (?, ?, ?)",
                (role.id, role.name, role.model_dump_json(indent=2)),
            )

    def list_agent_roles(self) -> list[AgentRoleSpec]:
        with self.connect() as conn:
            rows = conn.execute("SELECT payload_json FROM agent_roles ORDER BY name ASC").fetchall()
        return [AgentRoleSpec.model_validate_json(row["payload_json"]) for row in rows]

    # --- SkillSources ---

    def upsert_skill_source(self, source: SkillSource) -> None:
        with self.connect() as conn:
            conn.execute(
                "DELETE FROM skill_sources WHERE id != ? AND url = ?", (source.id, source.url)
            )
            conn.execute(
                """
                INSERT OR REPLACE INTO skill_sources (id, url, updated_at, payload_json)
                VALUES (?, ?, ?, ?)
                """,
                (source.id, source.url, source.updated_at.isoformat(), source.model_dump_json(indent=2)),
            )

    def list_skill_sources(self) -> list[SkillSource]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT payload_json FROM skill_sources ORDER BY updated_at DESC"
            ).fetchall()
        return [SkillSource.model_validate_json(row["payload_json"]) for row in rows]

    # --- AgentSkills ---

    def upsert_agent_skill(self, skill: AgentSkillSpec) -> None:
        with self.connect() as conn:
            if skill.source_id is not None:
                conn.execute(
                    "DELETE FROM agent_skills WHERE id != ? AND source_id = ? AND source_path = ?",
                    (skill.id, skill.source_id, skill.source_path),
                )
            conn.execute(
                """
                INSERT OR REPLACE INTO agent_skills (id, source_id, source_path, name, payload_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (skill.id, skill.source_id, skill.source_path, skill.name, skill.model_dump_json(indent=2)),
            )

    def list_agent_skills(self, source_id: str | None = None) -> list[AgentSkillSpec]:
        with self.connect() as conn:
            if source_id is not None:
                rows = conn.execute(
                    "SELECT payload_json FROM agent_skills WHERE source_id = ? ORDER BY name ASC",
                    (source_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT payload_json FROM agent_skills ORDER BY name ASC"
                ).fetchall()
        return [AgentSkillSpec.model_validate_json(row["payload_json"]) for row in rows]

    # --- Agents ---

    def upsert_agent(self, agent: AgentInstance) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO agents (id, mission_id, created_at, payload_json)
                VALUES (?, ?, ?, ?)
                """,
                (agent.id, agent.mission_id, agent.created_at.isoformat(), agent.model_dump_json(indent=2)),
            )

    def list_agents(self, mission_id: str | None = None) -> list[AgentInstance]:
        with self.connect() as conn:
            if mission_id is not None:
                rows = conn.execute(
                    "SELECT payload_json FROM agents WHERE mission_id = ? ORDER BY created_at DESC",
                    (mission_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT payload_json FROM agents ORDER BY created_at DESC"
                ).fetchall()
        return [AgentInstance.model_validate_json(row["payload_json"]) for row in rows]

    # --- Agent governance ---

    def upsert_agent_permission_profile(self, profile: AgentPermissionProfile) -> None:
        with self.connect() as conn:
            conn.execute(
                "DELETE FROM agent_permission_profiles WHERE id != ? AND name = ?",
                (profile.id, profile.name),
            )
            conn.execute(
                """
                INSERT OR REPLACE INTO agent_permission_profiles (id, name, updated_at, payload_json)
                VALUES (?, ?, ?, ?)
                """,
                (profile.id, profile.name, profile.updated_at.isoformat(), profile.model_dump_json(indent=2)),
            )

    def list_agent_permission_profiles(self) -> list[AgentPermissionProfile]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT payload_json FROM agent_permission_profiles ORDER BY name ASC"
            ).fetchall()
        return [AgentPermissionProfile.model_validate_json(row["payload_json"]) for row in rows]

    def upsert_agent_contract(self, contract: AgentEmploymentContract) -> None:
        with self.connect() as conn:
            conn.execute(
                "DELETE FROM agent_employment_contracts WHERE id != ? AND agent_id = ?",
                (contract.id, contract.agent_id),
            )
            conn.execute(
                """
                INSERT OR REPLACE INTO agent_employment_contracts (id, agent_id, mission_id, updated_at, payload_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    contract.id,
                    contract.agent_id,
                    contract.mission_id,
                    contract.updated_at.isoformat(),
                    contract.model_dump_json(indent=2),
                ),
            )

    def list_agent_contracts(self, mission_id: str | None = None) -> list[AgentEmploymentContract]:
        with self.connect() as conn:
            if mission_id is not None:
                rows = conn.execute(
                    """
                    SELECT payload_json FROM agent_employment_contracts
                    WHERE mission_id = ? ORDER BY updated_at DESC
                    """,
                    (mission_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT payload_json FROM agent_employment_contracts ORDER BY updated_at DESC"
                ).fetchall()
        return [AgentEmploymentContract.model_validate_json(row["payload_json"]) for row in rows]

    # --- MissionTeams ---

    def upsert_team(self, team: MissionTeam) -> None:
        with self.connect() as conn:
            conn.execute(
                "DELETE FROM mission_teams WHERE id != ? AND mission_id = ?", (team.id, team.mission_id)
            )
            conn.execute(
                """
                INSERT OR REPLACE INTO mission_teams (id, mission_id, updated_at, payload_json)
                VALUES (?, ?, ?, ?)
                """,
                (team.id, team.mission_id, team.updated_at.isoformat(), team.model_dump_json(indent=2)),
            )

    def list_teams(self, mission_id: str | None = None) -> list[MissionTeam]:
        with self.connect() as conn:
            if mission_id is not None:
                rows = conn.execute(
                    "SELECT payload_json FROM mission_teams WHERE mission_id = ? ORDER BY updated_at DESC",
                    (mission_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT payload_json FROM mission_teams ORDER BY updated_at DESC"
                ).fetchall()
        return [MissionTeam.model_validate_json(row["payload_json"]) for row in rows]

    # --- Team templates and mission stage trace ---

    def upsert_team_template(self, template: TeamTemplate) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM team_templates WHERE id != ? AND name = ?", (template.id, template.name))
            conn.execute(
                """
                INSERT OR REPLACE INTO team_templates (id, name, updated_at, payload_json)
                VALUES (?, ?, ?, ?)
                """,
                (template.id, template.name, template.updated_at.isoformat(), template.model_dump_json(indent=2)),
            )

    def list_team_templates(self) -> list[TeamTemplate]:
        with self.connect() as conn:
            rows = conn.execute("SELECT payload_json FROM team_templates ORDER BY name ASC").fetchall()
        return [TeamTemplate.model_validate_json(row["payload_json"]) for row in rows]

    def upsert_mission_stage_transition(self, transition: MissionStageTransition) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO mission_stage_transitions (id, mission_id, created_at, payload_json)
                VALUES (?, ?, ?, ?)
                """,
                (
                    transition.id,
                    transition.mission_id,
                    transition.created_at.isoformat(),
                    transition.model_dump_json(indent=2),
                ),
            )

    def list_mission_stage_transitions(self, mission_id: str | None = None) -> list[MissionStageTransition]:
        with self.connect() as conn:
            if mission_id is not None:
                rows = conn.execute(
                    """
                    SELECT payload_json FROM mission_stage_transitions
                    WHERE mission_id = ? ORDER BY created_at ASC
                    """,
                    (mission_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT payload_json FROM mission_stage_transitions ORDER BY created_at DESC"
                ).fetchall()
        return [MissionStageTransition.model_validate_json(row["payload_json"]) for row in rows]

    def upsert_work_trace_event(self, event: WorkTraceEvent) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO work_trace_events (id, mission_id, created_at, payload_json)
                VALUES (?, ?, ?, ?)
                """,
                (event.id, event.mission_id, event.created_at.isoformat(), event.model_dump_json(indent=2)),
            )

    def list_work_trace_events(self, mission_id: str | None = None, limit: int = 100) -> list[WorkTraceEvent]:
        with self.connect() as conn:
            if mission_id is not None:
                rows = conn.execute(
                    """
                    SELECT payload_json FROM work_trace_events
                    WHERE mission_id = ? ORDER BY created_at DESC LIMIT ?
                    """,
                    (mission_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT payload_json FROM work_trace_events ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return [WorkTraceEvent.model_validate_json(row["payload_json"]) for row in rows]

    def upsert_executor_control(self, control: ExecutorControlRecord) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO executor_controls (id, mission_id, created_at, payload_json)
                VALUES (?, ?, ?, ?)
                """,
                (control.id, control.mission_id, control.created_at.isoformat(), control.model_dump_json(indent=2)),
            )

    def list_executor_controls(self, mission_id: str | None = None, limit: int = 100) -> list[ExecutorControlRecord]:
        with self.connect() as conn:
            if mission_id is not None:
                rows = conn.execute(
                    """
                    SELECT payload_json FROM executor_controls
                    WHERE mission_id = ? ORDER BY created_at DESC LIMIT ?
                    """,
                    (mission_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT payload_json FROM executor_controls ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return [ExecutorControlRecord.model_validate_json(row["payload_json"]) for row in rows]

    def upsert_executive_cadence(self, cadence: ExecutiveCadence) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM executive_cadences WHERE id != ? AND name = ?", (cadence.id, cadence.name))
            conn.execute(
                """
                INSERT OR REPLACE INTO executive_cadences (id, name, updated_at, payload_json)
                VALUES (?, ?, ?, ?)
                """,
                (cadence.id, cadence.name, cadence.updated_at.isoformat(), cadence.model_dump_json(indent=2)),
            )

    def list_executive_cadences(self) -> list[ExecutiveCadence]:
        with self.connect() as conn:
            rows = conn.execute("SELECT payload_json FROM executive_cadences ORDER BY name ASC").fetchall()
        return [ExecutiveCadence.model_validate_json(row["payload_json"]) for row in rows]

    # --- Delegations ---

    def upsert_delegation(self, delegation: DelegationRecord) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO delegations (id, mission_id, updated_at, payload_json)
                VALUES (?, ?, ?, ?)
                """,
                (
                    delegation.id,
                    delegation.mission_id,
                    delegation.updated_at.isoformat(),
                    delegation.model_dump_json(indent=2),
                ),
            )

    def list_delegations(self, mission_id: str | None = None) -> list[DelegationRecord]:
        with self.connect() as conn:
            if mission_id is not None:
                rows = conn.execute(
                    "SELECT payload_json FROM delegations WHERE mission_id = ? ORDER BY updated_at DESC",
                    (mission_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT payload_json FROM delegations ORDER BY updated_at DESC"
                ).fetchall()
        return [DelegationRecord.model_validate_json(row["payload_json"]) for row in rows]

    # --- Escalations ---

    def upsert_escalation(self, escalation: EscalationRecord) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO escalations (id, mission_id, status, created_at, payload_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    escalation.id,
                    escalation.mission_id,
                    escalation.status,
                    escalation.created_at.isoformat(),
                    escalation.model_dump_json(indent=2),
                ),
            )

    def list_escalations(
        self, mission_id: str | None = None, status: str | None = None
    ) -> list[EscalationRecord]:
        with self.connect() as conn:
            sql = "SELECT payload_json FROM escalations WHERE 1=1"
            params: list = []
            if mission_id is not None:
                sql += " AND mission_id = ?"
                params.append(mission_id)
            if status is not None:
                sql += " AND status = ?"
                params.append(status)
            sql += " ORDER BY created_at DESC"
            rows = conn.execute(sql, params).fetchall()
        return [EscalationRecord.model_validate_json(row["payload_json"]) for row in rows]

    # --- StandingOrders ---

    def upsert_standing_order(self, order: StandingOrder) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO standing_orders (id, updated_at, payload_json)
                VALUES (?, ?, ?)
                """,
                (order.id, order.updated_at.isoformat(), order.model_dump_json(indent=2)),
            )

    def list_standing_orders(self) -> list[StandingOrder]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT payload_json FROM standing_orders ORDER BY updated_at DESC"
            ).fetchall()
        return [StandingOrder.model_validate_json(row["payload_json"]) for row in rows]


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
        self.board_briefings_path = self.state_dir / "board_briefings.json"
        self.agent_roles_path = self.state_dir / "agent_roles.json"
        self.skill_sources_path = self.state_dir / "skill_sources.json"
        self.agent_skills_path = self.state_dir / "agent_skills.json"
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
        self.save_client_workspace_files(workspace_root, client)

    def save_client_workspace_files(self, workspace_root: Path, client: ClientRecord) -> None:
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
        self.save_matter_workspace_files(workspace_root, matter)

    def save_matter_workspace_files(self, workspace_root: Path, matter: MatterRecord) -> None:
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
        self.append_matter_decision_workspace_file(workspace_root, decision)

    def append_matter_decision_workspace_file(
        self, workspace_root: Path, decision: MatterDecisionRecord
    ) -> None:
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
        self.append_open_question_workspace_file(workspace_root, question)

    def append_open_question_workspace_file(
        self, workspace_root: Path, question: OpenQuestionRecord
    ) -> None:
        matter = next((item for item in self.list_matters() if item.id == question.matter_id), None)
        if matter is not None:
            path = workspace_root / matter.open_questions_path
            existing = path.read_text(encoding="utf-8") if path.exists() else "# Open Questions\n\n"
            blocking = f" Blocking: {question.blocking}" if question.blocking else ""
            _write_workspace_text(
                path, existing.rstrip() + f"\n- [{question.status}] {question.question}{blocking}\n"
            )

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

    def save_board_briefing(self, briefing: BoardBriefing) -> None:
        briefings = self.list_board_briefings(limit=10_000)
        briefings = [item for item in briefings if item.id != briefing.id] + [briefing]
        briefings.sort(key=lambda item: item.updated_at, reverse=True)
        self._write_model_list(self.board_briefings_path, briefings)

    def list_board_briefings(self, mission_id: str | None = None, limit: int = 50) -> list[BoardBriefing]:
        briefings = self._read_model_list(self.board_briefings_path, BoardBriefing)
        if mission_id is not None:
            briefings = [item for item in briefings if item.mission_id == mission_id]
        briefings.sort(key=lambda item: item.updated_at, reverse=True)
        return briefings[:limit]

    def save_agent_role(self, role: AgentRoleSpec) -> None:
        roles = self.list_agent_roles()
        roles = [item for item in roles if item.id != role.id and item.name != role.name] + [role]
        roles.sort(key=lambda item: item.name.lower())
        self._write_model_list(self.agent_roles_path, roles)

    def list_agent_roles(self) -> list[AgentRoleSpec]:
        return self._read_model_list(self.agent_roles_path, AgentRoleSpec)

    def save_skill_source(self, source: SkillSource) -> None:
        sources = self.list_skill_sources()
        sources = [item for item in sources if item.id != source.id and item.url != source.url] + [source]
        sources.sort(key=lambda item: item.updated_at, reverse=True)
        self._write_model_list(self.skill_sources_path, sources)

    def list_skill_sources(self) -> list[SkillSource]:
        return self._read_model_list(self.skill_sources_path, SkillSource)

    def save_agent_skill(self, skill: AgentSkillSpec) -> None:
        skills = self.list_agent_skills()
        skills = [
            item
            for item in skills
            if item.id != skill.id
            and not (skill.source_id is not None and item.source_id == skill.source_id and item.source_path == skill.source_path)
        ] + [skill]
        skills.sort(key=lambda item: (item.name.lower(), item.source_path or ""))
        self._write_model_list(self.agent_skills_path, skills)

    def list_agent_skills(self, source_id: str | None = None) -> list[AgentSkillSpec]:
        skills = self._read_model_list(self.agent_skills_path, AgentSkillSpec)
        if source_id is not None:
            skills = [item for item in skills if item.source_id == source_id]
        return skills

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
        self._cache: dict[Any, Any] = {}
        self._cache_lock = threading.RLock()
        self._run_migrations()

    # --- Process-wide read cache ---
    # A single shared cache (with a lock) avoids the cross-thread staleness
    # that a thread-local cache would suffer from: writes happen on FastAPI
    # thread-pool workers while reads in async middleware happen on the
    # event-loop thread, so per-thread invalidation could not see each
    # other's changes.

    def cache_clear(self) -> None:
        with self._cache_lock:
            self._cache.clear()

    def compute_cached(self, key: Any, fn) -> Any:
        """Cache a computed value (not storage data) in the shared scope."""
        return self._cached(key, fn)

    def _cached(self, key: Any, fn) -> Any:
        with self._cache_lock:
            if key in self._cache:
                return self._cache[key]
        value = fn()
        with self._cache_lock:
            self._cache.setdefault(key, value)
            return self._cache[key]

    def _invalidate(self, *keys: Any) -> None:
        with self._cache_lock:
            for k in keys:
                self._cache.pop(k, None)

    def _invalidate_prefix(self, prefix: Any) -> None:
        with self._cache_lock:
            to_delete = [
                k for k in self._cache
                if k == prefix or (isinstance(k, tuple) and k[0] == prefix)
            ]
            for k in to_delete:
                del self._cache[k]

    # --- Migration helpers ---

    def _run_migrations(self) -> None:
        _migrations = {
            "approvals": (self.fs.approvals_path, self.fs.list_approvals, self.index.upsert_approval),
            "governance_reviews": (
                self.fs.governance_reviews_path,
                self.fs.list_governance_reviews,
                self.index.upsert_governance_review,
            ),
            "conversation_messages": (
                self.fs.conversation_path,
                self.fs.list_conversation_messages,
                self.index.upsert_conversation_message,
            ),
            "agent_messages": (
                self.fs.agent_messages_path,
                lambda: self.fs.list_agent_messages(limit=100_000),
                self.index.upsert_agent_message,
            ),
            "work_sessions": (
                self.fs.work_sessions_path,
                lambda: self.fs.list_work_sessions(limit=100_000),
                self.index.upsert_work_session,
            ),
            "run_attempts": (
                self.fs.run_attempts_path,
                lambda: self.fs.list_run_attempts(limit=100_000),
                self.index.upsert_run_attempt,
            ),
            "clients": (self.fs.clients_path, self.fs.list_clients, self.index.upsert_client),
            "matters": (self.fs.matters_path, self.fs.list_matters, self.index.upsert_matter),
            "documents": (self.fs.documents_path, self.fs.list_documents, self.index.upsert_document),
            "matter_decisions": (
                self.fs.matter_decisions_path,
                self.fs.list_matter_decisions,
                self.index.upsert_matter_decision,
            ),
            "open_questions": (
                self.fs.open_questions_path,
                self.fs.list_open_questions,
                self.index.upsert_open_question,
            ),
            "knowledge_updates": (
                self.fs.knowledge_updates_path,
                self.fs.list_knowledge_updates,
                self.index.upsert_knowledge_update,
            ),
            "memory_promotion_reviews": (
                self.fs.memory_promotion_reviews_path,
                lambda: self.fs.list_memory_promotion_reviews(limit=100_000),
                self.index.upsert_memory_promotion_review,
            ),
            "board_briefings": (
                self.fs.board_briefings_path,
                lambda: self.fs.list_board_briefings(limit=100_000),
                self.index.upsert_board_briefing,
            ),
            "agent_roles": (self.fs.agent_roles_path, self.fs.list_agent_roles, self.index.upsert_agent_role),
            "skill_sources": (
                self.fs.skill_sources_path,
                self.fs.list_skill_sources,
                self.index.upsert_skill_source,
            ),
            "agent_skills": (
                self.fs.agent_skills_path,
                self.fs.list_agent_skills,
                self.index.upsert_agent_skill,
            ),
            "agents": (self.fs.agents_path, self.fs.list_agents, self.index.upsert_agent),
            "mission_teams": (self.fs.teams_path, self.fs.list_teams, self.index.upsert_team),
            "delegations": (
                self.fs.delegations_path,
                self.fs.list_delegations,
                self.index.upsert_delegation,
            ),
            "escalations": (
                self.fs.escalations_path,
                self.fs.list_escalations,
                self.index.upsert_escalation,
            ),
            "standing_orders": (
                self.fs.standing_orders_path,
                self.fs.list_standing_orders,
                self.index.upsert_standing_order,
            ),
        }
        for table_name, (json_path, list_fn, upsert_fn) in _migrations.items():
            if not self.index.is_migrated(table_name) and json_path.exists():
                try:
                    for item in list_fn():
                        upsert_fn(item)
                except Exception:
                    pass
                self.index.mark_migrated(table_name)

    # --- Settings & Auth ---

    def save_settings(self, settings: AppSettings) -> None:
        self.fs.save_settings(settings)
        self.index.save_settings(settings)
        self._invalidate("settings", "_runtime_health")

    def save_auth(self, auth_record: OwnerAuthRecord) -> None:
        self.fs.save_auth(auth_record)

    def load_auth(self) -> OwnerAuthRecord | None:
        return self.fs.load_auth()

    def load_settings(self) -> AppSettings | None:
        def _fetch():
            s = self.index.load_settings()
            if s is not None:
                return s
            s = self.fs.load_settings()
            if s is not None:
                self.index.save_settings(s)
            return s
        return self._cached("settings", _fetch)

    # --- Missions ---

    def save_mission(self, workspace_root: Path, mission: MissionDefinition) -> Path:
        path = self.fs.save_mission(workspace_root, mission)
        self.index.upsert_mission(mission)
        self._invalidate("missions", ("mission", mission.id))
        return path

    def load_mission(self, workspace_root: Path, mission_id: str) -> MissionDefinition | None:
        def _fetch():
            m = self.index.get_mission(mission_id)
            if m is not None:
                return m
            m = self.fs.load_mission(workspace_root, mission_id)
            if m is not None:
                self.index.upsert_mission(m)
            return m
        return self._cached(("mission", mission_id), _fetch)

    def list_missions(self, workspace_root: Path) -> list[MissionDefinition]:
        def _fetch():
            ms = self.index.list_missions()
            if ms:
                return ms
            ms = self.fs.list_missions(workspace_root)
            for m in ms:
                self.index.upsert_mission(m)
            return ms
        return self._cached("missions", _fetch)

    # --- Workspace files (filesystem-only) ---

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
        path = self.fs.save_meeting(workspace_root, meeting)
        self.index.upsert_meeting(meeting)
        self._invalidate_prefix("meetings")
        return path

    def list_meetings(self, workspace_root: Path, mission_id: str | None = None) -> list[MeetingRecord]:
        key = ("meetings", mission_id)
        def _fetch():
            ms = self.index.list_meetings(mission_id=mission_id)
            if ms:
                return ms
            ms = self.fs.list_meetings(workspace_root, mission_id=mission_id)
            for m in ms:
                self.index.upsert_meeting(m)
            return ms
        return self._cached(key, _fetch)

    def save_workspace_scope(self, workspace_root: Path, scope: WorkspaceScope) -> Path:
        return self.fs.save_workspace_scope(workspace_root, scope)

    def load_workspace_scope(self, workspace_root: Path, mission_id: str) -> WorkspaceScope | None:
        return self.fs.load_workspace_scope(workspace_root, mission_id)

    def load_workflow_contract(self, workspace_root: Path) -> WorkflowContract:
        return self.fs.load_workflow_contract(workspace_root)

    # --- Audit log (filesystem-only, append log) ---

    def append_audit_event(self, payload: dict) -> None:
        self.fs.append_audit_event(payload)

    def list_audit_events(self, limit: int = 50) -> list[dict]:
        return self.fs.list_audit_events(limit=limit)

    # --- Approvals (SQLite-primary) ---

    def save_approval(self, approval: ApprovalRequest) -> None:
        self.index.upsert_approval(approval)
        self._invalidate("approvals")

    def list_approvals(self) -> list[ApprovalRequest]:
        return self._cached("approvals", self.index.list_approvals)

    # --- GovernanceReviews (SQLite-primary) ---

    def save_governance_review(self, review: GovernanceReview) -> None:
        self.index.upsert_governance_review(review)

    def list_governance_reviews(self, limit: int = 20) -> list[GovernanceReview]:
        return self.index.list_governance_reviews(limit=limit)

    # --- ConversationMessages (SQLite-primary) ---

    def append_conversation_message(self, message: ConversationMessage) -> None:
        self.index.upsert_conversation_message(message)

    def list_conversation_messages(self, limit: int = 50) -> list[ConversationMessage]:
        return self.index.list_conversation_messages(limit=limit)

    # --- AgentMessages (SQLite-primary) ---

    def append_agent_message(self, message: AgentMessage) -> None:
        self.index.upsert_agent_message(message)

    def list_agent_messages(self, mission_id: str | None = None, limit: int = 50) -> list[AgentMessage]:
        return self.index.list_agent_messages(mission_id=mission_id, limit=limit)

    # --- WorkSessions (SQLite-primary) ---

    def save_work_session(self, session: WorkSession) -> None:
        self.index.upsert_work_session(session)

    def list_work_sessions(self, mission_id: str | None = None, limit: int = 50) -> list[WorkSession]:
        return self.index.list_work_sessions(mission_id=mission_id, limit=limit)

    # --- RunAttempts (SQLite-primary) ---

    def save_run_attempt(self, attempt: RunAttempt) -> None:
        self.index.upsert_run_attempt(attempt)

    def list_run_attempts(self, mission_id: str | None = None, limit: int = 50) -> list[RunAttempt]:
        return self.index.list_run_attempts(mission_id=mission_id, limit=limit)

    # --- MissionJobs (SQLite-primary) ---

    def save_mission_job(self, job: MissionJob) -> None:
        self.index.upsert_mission_job(job)

    def get_mission_job(self, job_id: str) -> MissionJob | None:
        return self.index.get_mission_job(job_id)

    def list_mission_jobs(self, mission_id: str | None = None, limit: int = 20) -> list[MissionJob]:
        return self.index.list_mission_jobs(mission_id=mission_id, limit=limit)

    def claim_next_queued_mission_job(self) -> MissionJob | None:
        return self.index.claim_next_queued_mission_job()

    def reset_running_mission_jobs(self) -> int:
        return self.index.reset_running_mission_jobs()

    # --- Clients (SQLite-primary + workspace files) ---

    def save_client(self, workspace_root: Path, client: ClientRecord) -> None:
        self.index.upsert_client(client)
        self.fs.save_client_workspace_files(workspace_root, client)
        self._invalidate("clients")

    def list_clients(self) -> list[ClientRecord]:
        return self._cached("clients", self.index.list_clients)

    # --- Matters (SQLite-primary + workspace files) ---

    def save_matter(self, workspace_root: Path, matter: MatterRecord) -> None:
        self.index.upsert_matter(matter)
        self.fs.save_matter_workspace_files(workspace_root, matter)
        self._invalidate_prefix("matters")

    def list_matters(self, client_id: str | None = None, mission_id: str | None = None) -> list[MatterRecord]:
        key = ("matters", client_id, mission_id)
        return self._cached(key, lambda: self.index.list_matters(client_id=client_id, mission_id=mission_id))

    # --- Documents (SQLite-primary) ---

    def save_document(self, document: DocumentRecord) -> None:
        self.index.upsert_document(document)

    def list_documents(self, matter_id: str | None = None, mission_id: str | None = None) -> list[DocumentRecord]:
        return self.index.list_documents(matter_id=matter_id, mission_id=mission_id)

    # --- MatterDecisions (SQLite-primary + workspace files) ---

    def save_matter_decision(self, workspace_root: Path, decision: MatterDecisionRecord) -> None:
        self.index.upsert_matter_decision(decision)
        matter = self.index.get_matter(decision.matter_id)
        if matter is not None:
            path = workspace_root / matter.decisions_path
            existing = path.read_text(encoding="utf-8") if path.exists() else "# Decisions\n\n"
            text = f"- {decision.summary}"
            if decision.rationale:
                text += f" Reason: {decision.rationale}"
            _write_workspace_text(path, existing.rstrip() + "\n" + text + "\n")

    def list_matter_decisions(
        self,
        matter_id: str | None = None,
        mission_id: str | None = None,
    ) -> list[MatterDecisionRecord]:
        return self.index.list_matter_decisions(matter_id=matter_id, mission_id=mission_id)

    # --- OpenQuestions (SQLite-primary + workspace files) ---

    def save_open_question(self, workspace_root: Path, question: OpenQuestionRecord) -> None:
        self.index.upsert_open_question(question)
        matter = self.index.get_matter(question.matter_id)
        if matter is not None:
            path = workspace_root / matter.open_questions_path
            existing = path.read_text(encoding="utf-8") if path.exists() else "# Open Questions\n\n"
            blocking = f" Blocking: {question.blocking}" if question.blocking else ""
            _write_workspace_text(
                path, existing.rstrip() + f"\n- [{question.status}] {question.question}{blocking}\n"
            )

    def list_open_questions(
        self,
        matter_id: str | None = None,
        mission_id: str | None = None,
        status: str | None = None,
    ) -> list[OpenQuestionRecord]:
        return self.index.list_open_questions(matter_id=matter_id, mission_id=mission_id, status=status)

    # --- KnowledgeUpdates (SQLite-primary) ---

    def save_knowledge_update(self, update: KnowledgeUpdate) -> None:
        self.index.upsert_knowledge_update(update)

    def list_knowledge_updates(
        self,
        matter_id: str | None = None,
        mission_id: str | None = None,
        status: str | None = None,
    ) -> list[KnowledgeUpdate]:
        return self.index.list_knowledge_updates(matter_id=matter_id, mission_id=mission_id, status=status)

    # --- MemoryPromotionReviews (SQLite-primary) ---

    def save_memory_promotion_review(self, review: MemoryPromotionReview) -> None:
        self.index.upsert_memory_promotion_review(review)

    def list_memory_promotion_reviews(
        self,
        mission_id: str | None = None,
        limit: int = 50,
    ) -> list[MemoryPromotionReview]:
        return self.index.list_memory_promotion_reviews(mission_id=mission_id, limit=limit)

    # --- BoardBriefings (SQLite-primary) ---

    def save_board_briefing(self, briefing: BoardBriefing) -> None:
        self.index.upsert_board_briefing(briefing)

    def list_board_briefings(self, mission_id: str | None = None, limit: int = 50) -> list[BoardBriefing]:
        return self.index.list_board_briefings(mission_id=mission_id, limit=limit)

    # --- AgentRoles (SQLite-primary) ---

    def save_agent_role(self, role: AgentRoleSpec) -> None:
        self.index.upsert_agent_role(role)
        self._invalidate("agent_roles")

    def list_agent_roles(self) -> list[AgentRoleSpec]:
        return self._cached("agent_roles", self.index.list_agent_roles)

    # --- SkillSources (SQLite-primary) ---

    def save_skill_source(self, source: SkillSource) -> None:
        self.index.upsert_skill_source(source)
        self._invalidate("skill_sources")

    def list_skill_sources(self) -> list[SkillSource]:
        return self._cached("skill_sources", self.index.list_skill_sources)

    # --- AgentSkills (SQLite-primary) ---

    def save_agent_skill(self, skill: AgentSkillSpec) -> None:
        self.index.upsert_agent_skill(skill)
        self._invalidate_prefix("agent_skills")

    def list_agent_skills(self, source_id: str | None = None) -> list[AgentSkillSpec]:
        key = ("agent_skills", source_id)
        return self._cached(key, lambda: self.index.list_agent_skills(source_id=source_id))

    # --- Agents (SQLite-primary) ---

    def save_agent(self, agent: AgentInstance) -> None:
        self.index.upsert_agent(agent)
        self._invalidate_prefix("agents")

    def list_agents(self, mission_id: str | None = None) -> list[AgentInstance]:
        key = ("agents", mission_id)
        return self._cached(key, lambda: self.index.list_agents(mission_id=mission_id))

    # --- Agent governance (SQLite-primary) ---

    def save_agent_permission_profile(self, profile: AgentPermissionProfile) -> None:
        self.index.upsert_agent_permission_profile(profile)
        self._invalidate("agent_permission_profiles")

    def list_agent_permission_profiles(self) -> list[AgentPermissionProfile]:
        return self._cached("agent_permission_profiles", self.index.list_agent_permission_profiles)

    def save_agent_contract(self, contract: AgentEmploymentContract) -> None:
        self.index.upsert_agent_contract(contract)
        self._invalidate_prefix("agent_contracts")

    def list_agent_contracts(self, mission_id: str | None = None) -> list[AgentEmploymentContract]:
        key = ("agent_contracts", mission_id)
        return self._cached(key, lambda: self.index.list_agent_contracts(mission_id=mission_id))

    # --- MissionTeams (SQLite-primary) ---

    def save_team(self, team: MissionTeam) -> None:
        self.index.upsert_team(team)

    def list_teams(self, mission_id: str | None = None) -> list[MissionTeam]:
        return self.index.list_teams(mission_id=mission_id)

    # --- Team templates and mission stage trace (SQLite-primary) ---

    def save_team_template(self, template: TeamTemplate) -> None:
        self.index.upsert_team_template(template)
        self._invalidate("team_templates")

    def list_team_templates(self) -> list[TeamTemplate]:
        return self._cached("team_templates", self.index.list_team_templates)

    def save_mission_stage_transition(self, transition: MissionStageTransition) -> None:
        self.index.upsert_mission_stage_transition(transition)
        self._invalidate_prefix("mission_stage_transitions")

    def list_mission_stage_transitions(self, mission_id: str | None = None) -> list[MissionStageTransition]:
        key = ("mission_stage_transitions", mission_id)
        return self._cached(key, lambda: self.index.list_mission_stage_transitions(mission_id=mission_id))

    def save_work_trace_event(self, event: WorkTraceEvent) -> None:
        self.index.upsert_work_trace_event(event)
        self._invalidate_prefix("work_trace_events")

    def list_work_trace_events(self, mission_id: str | None = None, limit: int = 100) -> list[WorkTraceEvent]:
        key = ("work_trace_events", mission_id, limit)
        return self._cached(key, lambda: self.index.list_work_trace_events(mission_id=mission_id, limit=limit))

    def save_executor_control(self, control: ExecutorControlRecord) -> None:
        self.index.upsert_executor_control(control)
        self._invalidate_prefix("executor_controls")

    def list_executor_controls(self, mission_id: str | None = None, limit: int = 100) -> list[ExecutorControlRecord]:
        key = ("executor_controls", mission_id, limit)
        return self._cached(key, lambda: self.index.list_executor_controls(mission_id=mission_id, limit=limit))

    def save_executive_cadence(self, cadence: ExecutiveCadence) -> None:
        self.index.upsert_executive_cadence(cadence)
        self._invalidate("executive_cadences")

    def list_executive_cadences(self) -> list[ExecutiveCadence]:
        return self._cached("executive_cadences", self.index.list_executive_cadences)

    # --- Delegations (SQLite-primary) ---

    def save_delegation(self, delegation: DelegationRecord) -> None:
        self.index.upsert_delegation(delegation)

    def list_delegations(self, mission_id: str | None = None) -> list[DelegationRecord]:
        return self.index.list_delegations(mission_id=mission_id)

    # --- Escalations (SQLite-primary) ---

    def save_escalation(self, escalation: EscalationRecord) -> None:
        self.index.upsert_escalation(escalation)

    def list_escalations(self, mission_id: str | None = None, status: str | None = None) -> list[EscalationRecord]:
        return self.index.list_escalations(mission_id=mission_id, status=status)

    # --- StandingOrders (SQLite-primary) ---

    def save_standing_order(self, order: StandingOrder) -> None:
        self.index.upsert_standing_order(order)
        self._invalidate("standing_orders")

    def list_standing_orders(self) -> list[StandingOrder]:
        return self._cached("standing_orders", self.index.list_standing_orders)


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
