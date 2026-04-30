# Praetor Workspace Steward

The chairman should not need to design folders, rename files, or keep document
links synchronized by hand. Praetor should do that as company operations work.

## Principle

Filesystem paths are locations, not identity.

Durable references should point to stable records:

- `file_asset_id`
- `document_id`
- `document_version_id`
- `matter_id`
- `mission_id`

This allows Praetor to reorganize folders while preserving Wiki links, document
registry records, and agent references.

## File Intake

Every file source should enter the same stewardship flow:

1. User upload
2. AI-generated document
3. Downloaded file
4. Runtime output
5. Requested mission output
6. Manually discovered workspace file

Praetor registers each as `FileAssetRecord` with:

- current path
- previous paths
- source
- sensitivity
- purpose
- client / matter / mission links
- document / version links when relevant
- steward notes

The workspace also receives `.praetor/file_manifest.json` as a machine-readable
index.

## Restructure Plan

Praetor should not silently perform risky folder moves.

`WorkspaceRestructurePlan` records:

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

Workspace reconciliation compares the registry with the filesystem and Git:

- tracked file still exists
- tracked file is missing
- tracked file content changed
- tracked file appears to have moved
- filesystem file is untracked
- Git reports modified, deleted, renamed, or untracked files

Reconciliation is conservative. It creates a report and updates asset
fingerprints, but it does not overwrite user changes or silently move sensitive
files.

Each registered file can store:

- size
- modified time
- SHA-256
- last seen time
- existence state
- sync status

If a missing asset has the same hash at a new path, Praetor treats it as a moved
candidate and asks for registry confirmation.

## Current Implementation

The first implementation registers:

- mission requested outputs
- planned document versions
- runtime changed files

It also exposes:

- workspace steward snapshot
- mission-scoped steward snapshot
- workspace reconciliation report generation
- mission-scoped reconciliation report generation
- mission-scoped restructure plan generation
- global restructure plan generation

This is intentionally a foundation. Upload, download, and full move execution
should connect to the same registry instead of inventing separate file logic.
