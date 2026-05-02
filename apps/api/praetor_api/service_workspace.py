from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from .models import (
    DocumentRecord,
    FileAssetRecord,
    FileMoveRecord,
    MatterRecord,
    MissionDefinition,
    WorkspaceReconciliationIssue,
    WorkspaceReconciliationReport,
    WorkspaceRestructurePlan,
    WorkspaceScope,
    WorkspaceStewardSnapshot,
    utc_now,
)


class WorkspaceMixin:
    """Workspace file scanning, asset registry, and reconciliation."""

    def workspace_steward_snapshot(self, mission_id: str | None = None, limit: int = 100) -> WorkspaceStewardSnapshot:

        settings = self._require_settings()

        assets = self.storage.list_file_assets(mission_id=mission_id, limit=limit)

        plans = self.storage.list_workspace_restructure_plans(mission_id=mission_id, limit=20)

        reports = self.storage.list_workspace_reconciliation_reports(mission_id=mission_id, limit=20)

        moves = self.storage.list_file_moves(limit=50)

        self.storage.write_workspace_manifest(Path(settings.workspace.root), self.storage.list_file_assets(limit=100_000))

        return WorkspaceStewardSnapshot(

            assets=assets,

            restructure_plans=plans,

            reconciliation_reports=reports,

            recent_moves=moves,

        )





    def list_workspace_reconciliation_reports(

        self,

        mission_id: str | None = None,

        limit: int = 20,

    ) -> list[WorkspaceReconciliationReport]:

        self._require_settings()

        return self.storage.list_workspace_reconciliation_reports(mission_id=mission_id, limit=limit)





    def reconcile_workspace(self, mission_id: str | None = None) -> WorkspaceReconciliationReport:

        settings = self._require_settings()

        workspace_root = Path(settings.workspace.root).resolve()

        mission = self.get_mission(mission_id) if mission_id else None

        scope = self.storage.load_workspace_scope(workspace_root, mission_id) if mission_id else None

        tracked_assets = self.storage.list_file_assets(mission_id=mission_id, limit=100_000)

        existing_by_path = {asset.current_path: asset for asset in tracked_assets}

        scanned = self._scan_workspace_files(workspace_root)

        scanned_by_path = {item["path"]: item for item in scanned}

        scanned_by_hash: dict[str, list[dict[str, Any]]] = {}

        for item in scanned:

            if item.get("sha256"):

                scanned_by_hash.setdefault(str(item["sha256"]), []).append(item)



        missing: list[WorkspaceReconciliationIssue] = []

        changed: list[WorkspaceReconciliationIssue] = []

        moved: list[WorkspaceReconciliationIssue] = []



        for asset in tracked_assets:

            current = scanned_by_path.get(asset.current_path)

            if current is None:

                candidate = None

                if asset.sha256:

                    candidate = next(

                        (item for item in scanned_by_hash.get(asset.sha256, []) if item["path"] != asset.current_path),

                        None,

                    )

                if candidate is not None:

                    issue = WorkspaceReconciliationIssue(

                        type="moved_candidate",

                        summary=f"Tracked asset appears to have moved: {asset.current_path} -> {candidate['path']}",

                        path=asset.current_path,

                        asset_id=asset.id,

                        candidate_path=str(candidate["path"]),

                        recommended_action="Review and update current_path while preserving previous_paths.",

                        requires_approval=asset.sensitivity in {"confidential", "restricted"},

                    )

                    moved.append(issue)

                    asset = asset.model_copy(

                        update={

                            "exists": False,

                            "sync_status": "moved_candidate",

                            "last_seen_at": utc_now(),

                            "updated_at": utc_now(),

                        }

                    )

                else:

                    issue = WorkspaceReconciliationIssue(

                        type="missing_asset",

                        summary=f"Tracked asset is missing from disk: {asset.current_path}",

                        path=asset.current_path,

                        asset_id=asset.id,

                        recommended_action="Review whether the file was intentionally deleted or moved outside Praetor.",

                        requires_approval=asset.sensitivity in {"confidential", "restricted"},

                    )

                    missing.append(issue)

                    asset = asset.model_copy(

                        update={

                            "exists": False,

                            "sync_status": "missing",

                            "last_seen_at": utc_now(),

                            "updated_at": utc_now(),

                        }

                    )

                self.storage.save_file_asset(asset)

                continue



            updates: dict[str, Any] = {

                "size_bytes": current["size_bytes"],

                "modified_at": current["modified_at"],

                "sha256": current["sha256"],

                "exists": True,

                "last_seen_at": utc_now(),

                "updated_at": utc_now(),

            }

            if asset.sha256 and current["sha256"] and asset.sha256 != current["sha256"]:

                changed.append(

                    WorkspaceReconciliationIssue(

                        type="changed_asset",

                        summary=f"Tracked asset content changed outside its last registry fingerprint: {asset.current_path}",

                        path=asset.current_path,

                        asset_id=asset.id,

                        recommended_action="Register a new document version or accept the external edit into the file registry.",

                        requires_approval=asset.sensitivity in {"confidential", "restricted"},

                    )

                )

                updates["sync_status"] = "changed"

            else:

                updates["sync_status"] = "tracked"

            self.storage.save_file_asset(asset.model_copy(update=updates))



        untracked: list[WorkspaceReconciliationIssue] = []

        for item in scanned:

            path = str(item["path"])

            if path in existing_by_path:

                continue

            if mission_id and not self._path_belongs_to_mission(path, mission, scope):

                continue

            untracked.append(

                WorkspaceReconciliationIssue(

                    type="untracked_file",

                    summary=f"File exists on disk but is not in the Workspace Steward registry: {path}",

                    path=path,

                    recommended_action="Classify and register this file, or ignore it if it is temporary.",

                    requires_approval=self._infer_file_sensitivity(path) in {"confidential", "restricted"},

                )

            )



        git_changes = self._scan_git_changes(workspace_root, mission=mission, scope=scope)

        suggested_actions = []

        if missing:

            suggested_actions.append("Review missing assets before closing the mission.")

        if changed:

            suggested_actions.append("Convert accepted external edits into new document versions or registry fingerprints.")

        if moved:

            suggested_actions.append("Confirm moved candidates and update current_path / previous_paths.")

        if untracked:

            suggested_actions.append("Classify untracked files through Workspace Steward intake.")

        if git_changes:

            suggested_actions.append("Review Git changes and decide whether they should become mission artifacts.")



        report = WorkspaceReconciliationReport(

            mission_id=mission_id,

            scanned_files=len(scanned),

            tracked_assets=len(tracked_assets),

            missing_assets=missing,

            changed_assets=changed,

            moved_candidates=moved,

            untracked_files=untracked[:100],

            git_changes=git_changes[:100],

            suggested_actions=suggested_actions,

        )

        self.storage.save_workspace_reconciliation_report(report)

        self.storage.write_workspace_manifest(workspace_root, self.storage.list_file_assets(limit=100_000))

        self._audit(

            "workspace_reconciliation_completed",

            {

                "report_id": report.id,

                "mission_id": mission_id,

                "scanned_files": report.scanned_files,

                "missing": len(missing),

                "changed": len(changed),

                "moved": len(moved),

                "untracked": len(untracked),

                "git_changes": len(git_changes),

            },

        )

        return report





    def create_workspace_restructure_plan(self, mission_id: str | None = None) -> WorkspaceRestructurePlan:

        settings = self._require_settings()

        workspace_root = Path(settings.workspace.root)

        mission = self.get_mission(mission_id) if mission_id else None

        matter = next(iter(self.storage.list_matters(mission_id=mission_id)), None) if mission_id else None

        assets = self.storage.list_file_assets(mission_id=mission_id, limit=100_000)

        moves: list[FileMoveRecord] = []

        for asset in assets:

            target = self._canonical_asset_path(asset, matter)

            if not target or target == asset.current_path:

                continue

            moves.append(

                FileMoveRecord(

                    asset_id=asset.id,

                    from_path=asset.current_path,

                    to_path=target,

                    reason="Workspace Steward recommends canonical matter/project organization.",

                    requires_approval=asset.sensitivity in {"confidential", "restricted"},

                )

            )

        requires_approval = bool(moves) and (len(moves) > 10 or any(move.requires_approval for move in moves))

        plan = WorkspaceRestructurePlan(

            mission_id=mission.id if mission else None,

            matter_id=matter.id if matter else None,

            client_id=matter.client_id if matter else None,

            summary=f"Workspace Steward reviewed {len(assets)} file asset(s) and proposed {len(moves)} move(s).",

            rationale=(

                "Praetor keeps stable file asset IDs and treats filesystem paths as changeable locations. "

                "This plan can be reviewed before files are moved or Wiki links are updated."

            ),

            moves=moves,

            wiki_updates=[

                "Update wiki links to stable praetor://file/<asset_id> references after move execution."

            ] if moves else [],

            registry_updates=[

                "Update document registry paths and previous_paths after move execution."

            ] if moves else [],

            risks=[

                "Do not execute moves that affect client, legal, privacy, or delivery files without approval.",

                "External links or manually written Markdown paths may need review after restructuring.",

            ] if moves else [],

            requires_approval=requires_approval,

        )

        self.storage.save_workspace_restructure_plan(plan)

        for move in moves:

            self.storage.save_file_move(move)

        self.storage.write_workspace_manifest(workspace_root, self.storage.list_file_assets(limit=100_000))

        self._audit(

            "workspace_restructure_plan_created",

            {

                "plan_id": plan.id,

                "mission_id": mission_id,

                "moves": len(moves),

                "requires_approval": requires_approval,

            },

        )

        return plan





    def _register_requested_output_assets(self, mission: MissionDefinition) -> None:

        for output in mission.requested_outputs:

            self._save_file_asset(

                FileAssetRecord(

                    current_path=self._workspace_relative_path(output),

                    source="requested_output",

                    sensitivity=self._infer_file_sensitivity(output),

                    title=Path(output).name,

                    purpose="Requested mission output.",

                    client_id=mission.client_id,

                    matter_id=mission.matter_id,

                    mission_id=mission.id,

                    steward_notes="Registered from mission requested_outputs.",

                )

            )





    def _register_document_assets(self, document: DocumentRecord) -> None:

        for version in document.versions:

            self._save_file_asset(

                FileAssetRecord(

                    current_path=self._workspace_relative_path(version.path),

                    source="document_version",

                    sensitivity=self._infer_file_sensitivity(version.path),

                    title=document.title,

                    purpose=version.reason,

                    client_id=document.client_id,

                    matter_id=document.matter_id,

                    mission_id=document.mission_id,

                    document_id=document.id,

                    document_version_id=version.id,

                    steward_notes=f"Registered from document registry version v{version.version:03d}.",

                )

            )





    def _register_runtime_output_assets(self, mission: MissionDefinition, changed_files: list[str]) -> None:

        for path in changed_files:

            self._save_file_asset(

                FileAssetRecord(

                    current_path=self._workspace_relative_path(path),

                    source="runtime_output",

                    sensitivity=self._infer_file_sensitivity(path),

                    title=Path(path).name,

                    purpose="Executor changed or generated this file.",

                    client_id=mission.client_id,

                    matter_id=mission.matter_id,

                    mission_id=mission.id,

                    steward_notes="Registered from runtime changed_files.",

                )

            )





    def _save_file_asset(self, asset: FileAssetRecord) -> None:

        settings = self._require_settings()

        workspace_root = Path(settings.workspace.root).resolve()

        fingerprint = self._file_fingerprint(workspace_root / asset.current_path)

        if fingerprint is not None:

            asset = asset.model_copy(

                update={

                    "size_bytes": fingerprint["size_bytes"],

                    "modified_at": fingerprint["modified_at"],

                    "sha256": fingerprint["sha256"],

                    "last_seen_at": utc_now(),

                    "exists": True,

                    "sync_status": "tracked",

                    "updated_at": utc_now(),

                }

            )

        existing = next(

            (

                item

                for item in self.storage.list_file_assets(limit=100_000)

                if item.current_path == asset.current_path

                or (

                    asset.document_version_id is not None

                    and item.document_version_id == asset.document_version_id

                )

            ),

            None,

        )

        if existing is not None:

            asset = existing.model_copy(

                update={

                    "source": asset.source,

                    "sensitivity": asset.sensitivity,

                    "title": asset.title or existing.title,

                    "purpose": asset.purpose or existing.purpose,

                    "client_id": asset.client_id or existing.client_id,

                    "matter_id": asset.matter_id or existing.matter_id,

                    "mission_id": asset.mission_id or existing.mission_id,

                    "document_id": asset.document_id or existing.document_id,

                    "document_version_id": asset.document_version_id or existing.document_version_id,

                    "steward_notes": asset.steward_notes or existing.steward_notes,

                    "updated_at": utc_now(),

                }

            )

        self.storage.save_file_asset(asset)

        self.storage.write_workspace_manifest(Path(settings.workspace.root), self.storage.list_file_assets(limit=100_000))





    def _scan_workspace_files(self, workspace_root: Path) -> list[dict[str, Any]]:

        files: list[dict[str, Any]] = []

        skip_dirs = {".git", ".praetor", "node_modules", ".venv", "__pycache__", ".pytest_cache", "dist", "build"}

        for path in workspace_root.rglob("*"):

            if any(part in skip_dirs for part in path.relative_to(workspace_root).parts[:-1]):

                continue

            if not path.is_file():

                continue

            rel = path.relative_to(workspace_root).as_posix()

            fingerprint = self._file_fingerprint(path)

            if fingerprint is None:

                continue

            files.append({"path": rel, **fingerprint})

        return files



    @staticmethod



    def _file_fingerprint(path: Path) -> dict[str, Any] | None:

        try:

            stat = path.stat()

            if not path.is_file():

                return None

            digest = hashlib.sha256()

            with path.open("rb") as handle:

                for chunk in iter(lambda: handle.read(1024 * 1024), b""):

                    digest.update(chunk)

            return {

                "size_bytes": stat.st_size,

                "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=utc_now().tzinfo),

                "sha256": digest.hexdigest(),

            }

        except OSError:

            return None





    def _scan_git_changes(

        self,

        workspace_root: Path,

        *,

        mission: MissionDefinition | None = None,

        scope: WorkspaceScope | None = None,

    ) -> list:

        repos = self._find_git_repos(workspace_root)

        changes = []

        from .models import GitChangeRecord



        for repo in repos:

            try:

                result = subprocess.run(

                    ["git", "-C", str(repo), "status", "--porcelain"],

                    check=False,

                    capture_output=True,

                    text=True,

                    timeout=10,

                )

            except (OSError, subprocess.TimeoutExpired):

                continue

            if result.returncode != 0:

                continue

            repo_rel = repo.relative_to(workspace_root).as_posix() if repo != workspace_root else "."

            for line in result.stdout.splitlines():

                if not line:

                    continue

                status = line[:2].strip() or line[:2]

                raw_path = line[3:] if len(line) > 3 else ""

                rel_path = raw_path.split(" -> ")[-1]

                workspace_rel = rel_path if repo_rel == "." else f"{repo_rel}/{rel_path}"

                if mission and not self._path_belongs_to_mission(workspace_rel, mission, scope):

                    continue

                changes.append(GitChangeRecord(repo_path=repo_rel, path=workspace_rel, status=status))

        return changes



    @staticmethod



    def _find_git_repos(workspace_root: Path) -> list[Path]:

        repos = []

        if (workspace_root / ".git").exists():

            repos.append(workspace_root)

        for git_dir in workspace_root.glob("**/.git"):

            repo = git_dir.parent

            if repo == workspace_root:

                continue

            if any(part in {"node_modules", ".praetor"} for part in repo.relative_to(workspace_root).parts):

                continue

            repos.append(repo)

            if len(repos) >= 20:

                break

        return repos



    @staticmethod



    def _path_belongs_to_mission(path: str, mission: MissionDefinition | None, scope: WorkspaceScope | None) -> bool:

        if mission is None:

            return True

        prefixes = [f"Missions/{mission.id}/"]

        if scope is not None:

            prefixes.append(scope.root.rstrip("/") + "/")

        return any(path == prefix.rstrip("/") or path.startswith(prefix) for prefix in prefixes)





    def _canonical_asset_path(self, asset: FileAssetRecord, matter: MatterRecord | None = None) -> str | None:

        if matter is None:

            return None

        filename = Path(asset.current_path).name

        if not filename:

            return None

        if asset.document_id or asset.source == "document_version":

            return f"{matter.folder}/versions/{filename}"

        if asset.source == "runtime_output":

            return f"{matter.folder}/outputs/{filename}"

        if asset.source == "requested_output":

            return f"{matter.folder}/requested/{filename}"

        return f"{matter.folder}/files/{filename}"



    @staticmethod



    def _workspace_relative_path(path: str) -> str:

        path = path.strip()

        for prefix in ["/app/workspace/", "/workspace/"]:

            if path.startswith(prefix):

                return path[len(prefix) :].lstrip("/")

        return path.lstrip("/")



    @staticmethod



    def _infer_file_sensitivity(path: str) -> str:

        lowered = path.lower()

        if any(term in lowered for term in ["secret", "token", "key", "credential", "private"]):

            return "restricted"

        if any(term in lowered for term in ["contract", "legal", "合約", "合同", "client", "customer"]):

            return "confidential"

        return "internal"




