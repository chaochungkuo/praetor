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

## Current Implementation

The first implementation registers:

- mission requested outputs
- planned document versions
- runtime changed files

It also exposes:

- workspace steward snapshot
- mission-scoped steward snapshot
- mission-scoped restructure plan generation
- global restructure plan generation

This is intentionally a foundation. Upload, download, and full move execution
should connect to the same registry instead of inventing separate file logic.
