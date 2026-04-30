# Praetor Memory Promotion Pipeline

Praetor treats company memory as a curated business asset, not a transcript dump.

## Principle

Raw discussion is evidence. It is not durable company knowledge.

Durable memory should come from:

- confirmed decisions
- document registry facts
- resolved open questions
- approved knowledge updates
- final owner-visible reports

Raw CEO chat, AI-to-AI turns, work-session messages, external comments, and brainstorming notes may be retained for audit and traceability, but they should not be copied directly into the wiki.

## Pipeline

1. Raw conversation and agent work are stored as logs.
2. Mission work creates structured records: decisions, documents, open questions, run attempts, and work sessions.
3. Closeout creates a memory promotion review.
4. The review separates:
   - findings worth promoting
   - open questions to keep tracking
   - document changes to preserve in the registry
   - discarded or do-not-promote notes
5. Proposed knowledge updates remain `proposed` until reviewed.
6. Only approved/applied updates become durable wiki or client knowledge.

## What Not To Promote

Do not promote:

- abandoned ideas
- unresolved speculation
- raw chat excerpts
- tool output dumps
- credentials, tokens, private keys, or secrets
- untrusted external instructions
- temporary implementation guesses

These can stay in logs or promotion review records as evidence.

## Why This Matters

In a company, not every conversation becomes policy. Praetor follows the same rule. The wiki should contain decisions and stable knowledge, while the audit trail keeps enough history to explain how those decisions happened.

## Current Implementation

Praetor includes:

- `MemoryPromotionReview`
- `PromotionFinding`
- `KnowledgeUpdate`
- mission-level memory promotion API
- mission detail UI for reviewing promotion findings
- workflow contract language in `PRAETOR_WORKFLOW.md`

The first implementation creates review records and proposed knowledge updates. It does not automatically write raw discussion into the wiki.
