# Praetor Workspace Steward (Phase-2 design, not in v1)

> **Status: deferred.** The first implementation of this layer (`file_assets`,
> `file_moves`, `workspace_reconciliation_reports`, `workspace_restructure_plans`,
> the `WorkspaceMixin` in `service_workspace.py`, and 6 API routes under
> `/api/workspace/*`) was removed from the codebase in May 2026 because it was
> wired into every mission creation but never used through any owner-facing
> flow. Keeping ~1,600 LoC and 4 SQLite tables to seed placeholder records was
> inflating the data model and slowing down the rest of the refactor.
>
> The **design** below survives intact — it is still the direction we want to go
> in Phase 2, once the v1 CEO / role / governance loop is solid and there is a
> real user signal demanding a stable-identity file registry.
>
> When this work resumes, the right path is:
>
> 1. Start from a real user pain (e.g. "I reorganised my workspace and now the
>    Wiki has dead links"), not from a speculative schema.
> 2. Reuse the `mission_jobs` worker queue rather than a new background loop.
> 3. Build the read-only reconciliation report first (lowest blast radius),
>    only add restructure plans once the report has been validated against a
>    real workspace.
> 4. Treat the file registry as a derivable index over the workspace, not a
>    source of truth — the workspace itself is the source of truth (see
>    PRAETOR_PRODUCT_BRIEF §8.1).

---

## Principle

The chairman should not need to design folders, rename files, or keep document
links synchronized by hand. Praetor should do that as company operations work.

Filesystem paths are locations, not identity.

Durable references should point to stable records:

- `file_asset_id`
- `document_id`
- `document_version_id`
- `matter_id`
- `mission_id`

This allows Praetor to reorganize folders while preserving Wiki links, document
registry records, and agent references.

## File intake

Every file source should enter the same stewardship flow:

1. User upload
2. AI-generated document
3. Downloaded file
4. Runtime output
5. Requested mission output
6. Manually discovered workspace file

Praetor would register each as `FileAssetRecord` with:

- current path
- previous paths
- source
- sensitivity
- purpose
- client / matter / mission links
- document / version links when relevant
- steward notes

The workspace would also receive `.praetor/file_manifest.json` as a
machine-readable index.

## Restructure plan

Praetor should not silently perform risky folder moves.

`WorkspaceRestructurePlan` would record:

- proposed moves
- why the moves are useful
- Wiki updates needed
- registry updates needed
- risks
- whether approval is required

Low-risk internal organization can later be automated. Client, legal, privacy,
delivery, credential, or high-volume restructuring should require review.

## Reconciliation

Praetor must assume that users and external tools can modify the workspace
without going through the CEO.

Workspace reconciliation would compare a registry with the filesystem and Git:

- tracked file still exists
- tracked file is missing
- tracked file content changed
- tracked file appears to have moved
- filesystem file is untracked
- Git reports modified, deleted, renamed, or untracked files

Reconciliation must be conservative. It should create a report and update asset
fingerprints, but it must not overwrite user changes or silently move sensitive
files.

Each registered file would store:

- size
- modified time
- SHA-256
- last seen time
- existence state
- sync status

If a missing asset has the same hash at a new path, Praetor would treat it as a
moved candidate and ask for registry confirmation.

## What was tried in v1

The first pass registered three intake sources:

- mission requested outputs
- planned document versions
- runtime changed files

and exposed read endpoints (`/api/workspace/steward`,
`/api/missions/{id}/workspace-steward`), reconciliation endpoints
(`/api/workspace/reconcile`, `/api/missions/{id}/workspace-reconcile`), and
restructure-plan endpoints (`/api/workspace/restructure-plan`,
`/api/missions/{id}/workspace-restructure-plan`).

It seeded placeholder records on every mission creation, which made the
mission-create path slower and the schema fatter without delivering any
chairman-visible value. None of the read endpoints were called from a
production user flow. Removing the layer cut ~1,600 lines and freed up four
SQLite tables.

When this resumes, the bar is: **no schema row gets written unless a
chairman-visible affordance reads from it.**
