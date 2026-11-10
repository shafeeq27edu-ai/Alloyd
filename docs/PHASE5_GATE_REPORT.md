# Phase 5 Gate Report — Data integrity and chat completeness

**Date:** 2026-11-10
**Branch:** `phase-5-data-integrity`
**Status:** Complete. **APPROVED PHASE 5** on 2026-11-10 when the owner instructed "push it and continue with the next task" after this report was posted.

## What changed

| Area | Scope |
| :--- | :--- |
| Chat persistence | Conversation and user message are written in one commit only after routing, provider selection, and key decryption succeed. Failed sends leave no conversation, no messages, and no mode change. |
| Regenerate | New `regenerate` flag reuses the last stored user message; prior answers are deleted and the new answer inserted in one commit on a successful `done` only. |
| History trimming | `app/core/history.py` trims to `HISTORY_MAX_CHARS` (default 24,000) keeping the system prompt and the newest messages; the routing metadata carries an "N older messages omitted" notice that the UI displays. |
| Migrations | `a7f3c1d9e5b2` backfills `conversations.mode = 'auto'` where NULL; `b8e4d2f6a1c3` adds `ix_conversations_user_id` and `ix_messages_conversation_id`. Models declare both indexes. |
| Account deletion | `DELETE /api/auth/account` requires the current password and CSRF, is rate-limited like login, deletes messages → conversations → provider keys → user in one transaction, and clears both auth cookies. Settings has a Danger Zone with password confirmation. |
| Chat controls | Stop generating (AbortController), regenerate, retry after failure, copy response, and delete-conversation confirmation in the workspace UI. |
| Configuration | `HISTORY_MAX_CHARS` in `backend/.env.example`, `docker-compose.yml`, and `docs/RUNNING.md`. |

## Commands and results

| Command | Result |
| :--- | :--- |
| `pytest -q` (backend, `.venv`) | **128 passed**, 1 pre-existing Pydantic warning |
| `npm run lint` | clean |
| `npm test` (SSE parser) | 8/8 passed |
| `npm run build` with `NEXT_PUBLIC_API_BASE_URL` | success |
| `docker compose build backend` / `frontend` | success; images rebuilt with the new code and migrations |
| Alembic on a scratch Postgres database | upgrade to `677b3b6bbe6a`, seed NULL-mode row, upgrade to head → `mode = 'auto'`; both indexes present; downgrade dropped the indexes; re-upgrade restored them |
| Live send with no provider key | `400 No API key configured`; conversation list stayed empty |
| Live failed regenerate with a placeholder key | safe `INVALID_API_KEY` error; stored messages unchanged |
| Live history trim (≈60,000 characters) | routing notice `7 older messages omitted to fit the model's context window.` |
| Live account deletion via Settings | wrong password → 400 and account kept; correct password + one confirmation → 200, redirect to `/login`, all rows deleted, `/api/auth/me` 401 |
| Delete-conversation confirmation | one confirmation prompt; conversation and messages removed |

## Acceptance criteria

| Criterion | Result | Evidence |
| :--- | :--- | :--- |
| Persist the user message only after validation and routing succeed | **PASS** | Single commit after routing/key access; tests for missing keys, invalid manual routes, and failed mode switches; live check on an account with no keys. |
| History truncation with a visible notice and unit tests | **PASS** | Six trimming tests; live notice observed in the routing event; `HISTORY_MAX_CHARS` documented. |
| Backfill migration for `conversations.mode = NULL`, reviewed before use on a real database | **PASS (with review step)** | Migration tested on a scratch Postgres only. It has not been run against any real/production database; running it there remains the owner's explicit call. |
| Account deletion with confirmation and tests | **PASS** | Backend tests plus the live Settings walkthrough; cookies cleared and data removed. |
| Stop, regenerate, copy, retry, delete-conversation confirmation | **PARTIAL** | Regenerate, retry, and delete-conversation confirmation verified live. Stop generating is NOT RUN end-to-end (needs an in-flight provider stream; no keys in this stack). Copy is NOT RUN in the browser because the Clipboard API requires a secure context; the failure toast is the only locally observable behavior. Both are code-reviewed. |
| Indexes on `conversations.user_id` and `messages.conversation_id` | **PASS** | Created by migration and present in the scratch database and the running compose database. |

## Found but not done

- Stop generating and copy were not exercised end-to-end; see the partial row above. They should be re-checked once real provider keys are available and behind HTTPS.
- History trimming is character-based. It is conservative but not token-accurate.
- Account deletion has no soft-delete, grace period, or audit trail.
- The regenerate replacement deletes every message after the last user turn; there is no partial-answer history.

## Risks introduced

- Deleting an account is irreversible and now removes provider keys; a user who deletes by mistake must re-add every key.
- Failed sends still count against the chat rate limit because limiting happens before validation.
- The backfill rewrites rows in one `UPDATE`. On a large database it should be chunked; the current data volume is small.

## Proposed next step

Review and reply `APPROVED PHASE 5`, then start Phase 6 (quality gates) on `phase-6-quality-gates`.
