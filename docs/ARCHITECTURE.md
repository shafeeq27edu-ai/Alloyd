# Alloyd Architecture

This document describes the code as it exists. File paths are relative to the
repository root; when behavior and this document disagree, the code wins and
this document is the bug.

## Runtime shape

```
                      ┌──────────────────────────────────────┐
  Browser ───────────▶│ Next.js 16 app (frontend/, port 3000)│
   ▲   HTML, JS       └───────────────┬──────────────────────┘
   │                                  │ fetch, cookies, X-CSRF-Token
   │  SSE (text/event-stream)         ▼
   └───────────────────────  FastAPI (backend/, port 8000, /api/*)
                                     │
                     ┌───────────────┼────────────────┐
                     ▼               ▼                ▼
             PostgreSQL 16     Groq / Gemini /   user's provider key
             (SQLAlchemy)      Anthropic SDK     (decrypted per request)
```

Two stateless application containers plus a database. All environment-specific
values come from environment variables; no hostname is hardcoded. The frontend
is a Next.js standalone build whose browser-facing API URL
(`NEXT_PUBLIC_API_BASE_URL`) is baked in at build time and also drives the CSP
`connect-src` in `frontend/next.config.ts`.

`docker-compose.yml` wires four services: `db` (Postgres 16.4), `migrate` (a
one-shot `alembic upgrade head` that `backend` waits for), `backend`, and
`frontend`, each with a health check.

## Backend

### Entry point and middleware

`backend/app/main.py` creates the app, registers routers, and installs four
HTTP middleware layers. Because Starlette wraps each newly added middleware
outside the previous ones, a request passes through them in this order:

1. `request_context` — accepts or generates a validated `X-Request-ID`, stores
   it in a context variable, times the request, and emits one structured log
   line (method, path, status, duration). No bodies or headers.
2. `add_security_headers` — `X-Content-Type-Options`, `X-Frame-Options`,
   `Referrer-Policy`, and HSTS unless `DEBUG=true`.
3. `limit_request_size` — rejects a declared `Content-Length` above
   `MAX_REQUEST_BYTES` with 413.
4. `CORSMiddleware` — exact `ALLOWED_ORIGINS` allowlist with credentials; a
   wildcard is rejected at startup by config validation.

At import time `RuleRouter.load_and_validate()` runs, so an unknown
provider/model in `router_config.yaml` stops the process instead of producing a
bad route at runtime. Startup (`lifespan`) then waits for the database with
`STARTUP_DB_CHECK_RETRIES` / `STARTUP_DB_CHECK_DELAY_SECONDS` and refuses to
serve if it never becomes reachable.

| Path | Role |
| :--- | :--- |
| `app/api/` | Route handlers: `auth`, `keys`, `chat`, `conversations`, `catalog`; `deps.py` holds auth and CSRF dependencies |
| `app/core/` | `router`, `classifier`, `skills`, `history`, `usage`, `security`, `encryption`, `rate_limit`, `errors`, `title_generator`, `logging_setup` |
| `app/providers/` | SDK adapters plus the registry and the gated mock adapter |
| `app/db/` | Async engine/session (`database.py`) and ORM models (`models.py`) |
| `alembic/` | Schema migrations; the app never calls `create_all` |
| `scripts/` | `report_usage.py`, `evaluate_classifier.py`, `rotate_keys.py`, `smoke_providers.py` |

### Chat request lifecycle

`backend/app/api/chat.py` is the core of the product. `POST /api/chat/`
requires the session cookie and the CSRF double-submit pair, then:

1. **Rate limit** — `chat:{user_id}`, default 15 requests per 60 s.
2. **Resolve conversation and mode without writing.** A missing or foreign
   conversation returns 404. Conversations with `mode = NULL` or a model that is
   no longer in the catalog are treated as Auto with a visible notice.
3. **Route.** In Auto mode the user's stored keys define availability and
   `TaskClassifier` chooses the category. In Manual mode the requested
   provider/model must be in the catalog.
4. **Resolve and decrypt the key** for the chosen provider. A key that cannot be
   decrypted produces a 400 asking the user to re-save it; nothing is written.
5. **Write once.** Only after every fallible step passes are the conversation
   row (if new), the user message, and any mode switch committed. A new
   conversation schedules `generate_and_update_title` as a background task.
   Regenerate (`regenerate: true`) writes no user message; it reuses the last
   stored one. Edit (`edit_message_id`) rewrites that earlier user message and
   deletes every message after it in the same commit, so a failed attempt
   leaves a consistent history rather than answers to discarded wording.
   Editing an assistant message, a message from another conversation, or a
   message in a conversation the user does not own is rejected.
6. **Prepare history.** A matching `@skill` injects a system prompt, then
   `trim_history` enforces `HISTORY_MAX_CHARS` (default 24,000 characters ≈
   6,000 tokens), keeping the system prompt and the newest messages and
   reporting how many older messages were dropped.
7. **Stream** from the adapter with a first-chunk timeout
   (`PROVIDER_FIRST_CHUNK_TIMEOUT_SECONDS`, default 20 s) and an overall SDK
   timeout (`PROVIDER_TIMEOUT_SECONDS`, default 60 s).

The response is `text/event-stream` with `Cache-Control: no-cache, no-transform`
and `X-Accel-Buffering: no`. Event contract:

| Event | Data | Meaning |
| :--- | :--- | :--- |
| `routing` | `provider`, `model`, `mode`, `conversation_id`, `user_message_id`, `category`, optional `notice` | Sent before each attempt, including the fallback attempt; `user_message_id` lets the UI make a just-sent question editable |
| `message` | `{"content": "..."}` | One text delta |
| `usage` | `input_tokens`, `output_tokens`, `token_source`, `estimated_cost_usd` | Once, after a successful answer |
| `done` | `{}` | Answer persisted; stream ends |
| `error` | `{"code", "provider", "message", "retryable"}` | Safe message; never raw provider output |

### Fallback rules

Fallback applies only when all of the following hold: Auto mode, no content has
been streamed yet, and no fallback has already happened in this request. It
fires when the error is `retryable` or `MODEL_UNAVAILABLE`; it never fires for
`INVALID_API_KEY` or `BAD_REQUEST`, and Manual mode never falls back. The failed
provider is marked unavailable and `RuleRouter.route` runs again, which walks the
configured primary/fallback pair and then any other provider the user has a key
for. The replacement attempt carries `fallback_from = "provider/model"` on its
usage row.

`backend/app/core/errors.py` maps SDK failures to `TIMEOUT`,
`PROVIDER_UNAVAILABLE`, `RATE_LIMIT`, `MODEL_UNAVAILABLE`, `INVALID_API_KEY`,
`BAD_REQUEST`, and internal errors, each with a retryable flag and a
user-safe message.

### Routing and classification

- `TaskCategory`: `CODING`, `RESEARCH`, `WRITING`, `PLANNING_DECISION`,
  `GENERAL` (`backend/app/core/router.py`). Image generation was removed in
  Phase 2 and deferred to V2.
- `backend/router_config.yaml` maps each category to a primary and a fallback
  `provider`/`model` pair. `validate_catalog` refuses startup if a category is
  missing or either slot names something outside the adapter catalog.
- `TaskClassifier` (`backend/app/core/classifier.py`) is deterministic: an
  `@skill` mention wins, then ordered regex heuristics per category, then
  `GENERAL`. It makes no network call.
- `backend/tests/data/classifier_prompts.json` holds 62 labeled prompts;
  `backend/scripts/evaluate_classifier.py` reports accuracy, currently 41/62
  (66.1%) with every miss falling through to `GENERAL`. See
  `docs/CLASSIFIER_ACCURACY.md`.

### Providers

`backend/app/providers/base.py` defines `BaseProviderAdapter`:
`get_models()`, `validate_key()`, `send_message()`, `stream_chat()`, and a
`provider_name` property. `stream_chat` yields `(event_type, data)` tuples of
`message`, `usage`, `done`, or `error`. Each adapter (`groq_adapter.py`,
`gemini_adapter.py`, `anthropic_adapter.py`) is the single source of truth for
its model IDs and translates that provider's stream and errors.

- Groq streams with `stream_options={"include_usage": True}`.
- Anthropic reads usage from the final message.
- Gemini passes system prompts as `system_instruction` and reports the last
  cumulative `usage_metadata`.
- `mock_adapter.py` is registered only when `ENABLE_MOCK_PROVIDER=true`; it
  performs no network calls and reports fixed token counts. It exists for E2E
  tests and must never be enabled in production.

`ProviderRegistry` (`registry.py`) instantiates adapters by name and backs
`GET /api/models`, `has_model`, and `fast_model` (used by the title generator
and the single-key fallback).

### Data model

Defined in `backend/app/db/models.py`, created only by Alembic
(`197150f84bcb → 677b3b6bbe6a → a7f3c1d9e5b2 → b8e4d2f6a1c3 → c4d9e8a7b6f5`):

| Table | Holds | Notes |
| :--- | :--- | :--- |
| `users` | id, email, bcrypt hash, created_at | Email is unique |
| `provider_keys` | user_id, provider_name, encrypted_key, key_hint | Fernet ciphertext; `key_hint` is a mask, never the key |
| `conversations` | user_id, title, mode (`auto`/`manual`), provider, model | Indexed by user; mode added in a later migration |
| `messages` | conversation_id, role, content, created_at | Plaintext content, indexed by conversation |
| `usage_events` | user_id, conversation_id, message_id, provider, model, mode, category, status, error_code, fallback_from, latency_ms, input/output tokens, `token_source`, `estimated_cost_usd`, created_at | **One row per provider attempt. Never stores prompts, answers, or raw provider errors.** |

`usage_events.message_id` is a plain indexed string, not a foreign key:
regenerating an answer deletes the old assistant message but the spend it
already caused remains real. Deleting a conversation removes its messages and
usage rows through the ORM cascade; deleting an account issues ordered explicit
deletes (usage → messages → conversations → keys → user) after re-checking the
password, so the wipe is auditable in one place.

Token counts are provider-reported when the provider supplies them; otherwise
`app/core/usage.py` estimates characters ÷ 4 and labels the row
`token_source = estimated`. `estimated_cost_usd` is `null` unless the operator
configures `PRICING_JSON` (USD per million tokens, keyed `provider/model`);
prices are never hardcoded.

### API surface

| Method and path | Auth | CSRF | Purpose |
| :--- | :--- | :--- | :--- |
| `GET /health`, `GET /ready` | none | no | Liveness; readiness runs `SELECT 1` and returns 503 when the DB is down |
| `GET /api/auth/csrf` | none | no | Issues the `csrf_token` cookie |
| `POST /api/auth/register` | none | yes | Create an account (12–72-character password) |
| `POST /api/auth/token` | none | yes | Login; sets HttpOnly cookies, returns no token |
| `POST /api/auth/logout` | cookie | yes | Clears both cookies |
| `DELETE /api/auth/account` | cookie | yes | Password-confirmed permanent deletion |
| `GET /api/auth/me` | cookie | no | Current user |
| `GET /api/keys/` | cookie | no | Masked key hints only |
| `POST /api/keys/` | cookie | yes | Validate against the provider, then store encrypted |
| `DELETE /api/keys/{provider_name}` | cookie | yes | Remove a key |
| `POST /api/chat/` | cookie | yes | Streamed answer (SSE); `regenerate` replaces the last answer, `edit_message_id` rewrites an earlier user message and replaces what followed |
| `GET /api/conversations/` | cookie | no | The user's conversations |
| `GET /api/conversations/{id}/messages` | cookie | no | Messages with their usage metadata |
| `DELETE /api/conversations/{id}` | cookie | yes | Delete a conversation and its messages |
| `GET /api/models` | cookie | no | Provider/model catalog from the adapters |

CSRF is a double-submit token: the `csrf_token` cookie plus a matching
`X-CSRF-Token` header, checked together with the request `Origin`/`Referer`
against `ALLOWED_ORIGINS`. Identity always comes from the verified JWT cookie;
`user_id` is never read from a request body.

### Observability

- JSON logs by default (`LOG_FORMAT=text` for local reading), one line per
  request, plus warnings for fallback and undecryptable keys. Logs contain no
  keys, message content, DSNs, or ciphertext.
- `GET /health` is liveness only; `GET /ready` verifies the database.
- `backend/scripts/report_usage.py` aggregates `usage_events` (totals, statuses,
  error codes, latency p50/p95, tokens with source counts, cost or `n/a`, and
  breakdowns by provider/model, category, mode, and day). It never reads
  `messages`.
- `backend/scripts/rotate_keys.py` re-encrypts stored keys during a manual
  Fernet key rotation; it prints counts and row IDs only.

## Frontend

`frontend/` is Next.js 16 App Router with React 19 and Tailwind v4.

| Path | Role |
| :--- | :--- |
| `src/app/page.tsx` | Chat workspace: conversation list, model selector, composer, message list, streaming state, stop/regenerate/copy controls, inline edit-and-resend, route line with per-answer model switch, usage line |
| `src/app/login/page.tsx` | Login and register (client-side minimum length; the server is authoritative) |
| `src/app/settings/page.tsx` | Add/update/remove provider keys, delete account |
| `src/app/layout.tsx` | Root layout, fonts, toast provider |
| `src/components/` | `Sidebar`, `Select`, `Toast` |
| `src/lib/api.ts` | `API_BASE_URL`, cached CSRF token, `fetchWithAuth` (adds credentials and `X-CSRF-Token` to state-changing calls, caches the token, clears it on 403, redirects to `/login` on 401) |
| `src/lib/sse.ts` | Buffered SSE parser: handles chunk boundaries, CRLF, multi-line `data:`, comments, and a final flush |
| `src/lib/usage.ts` | Token/cost formatting; prefixes estimates with `~`, hides cost when unknown |
| `src/lib/*.test.mjs` | Node `--experimental-strip-types` tests for the parser, API client, and usage formatting |

Markdown answers render through `react-markdown` + `remark-gfm` with syntax
highlighting. `next.config.ts` sets the CSP, `Permissions-Policy`, HSTS in
production, and refuses to build without `NEXT_PUBLIC_API_BASE_URL`.

## Configuration

All backend settings live in `backend/app/config.py` (pydantic-settings, loaded
from the environment then `backend/.env`). Startup validation refuses
placeholder or short `SECRET_KEY`, invalid `ENCRYPTION_KEY` bytes, wildcard
origins, malformed `PRICING_JSON`, and a missing database URL. The full variable
table is in `docs/RUNNING.md`. Frontend variables are
`NEXT_PUBLIC_API_BASE_URL` and, for development only,
`NEXT_ALLOWED_DEV_ORIGINS`.

## Tests and CI

- `backend/tests/` — 149 tests on SQLite locally, the same suite against
  Postgres in CI via `TEST_DATABASE_URL`. Coverage includes auth and cookies,
  CSRF, ownership, key validation/rotation, chat persistence rules, regenerate,
  history trimming, fallback, error mapping, usage events, readiness, catalog,
  and the classifier dataset shape.
- `frontend/src/lib/*.test.mjs` — 22 unit tests.
- `frontend/e2e/smoke.spec.ts` — Playwright smoke on desktop Chromium, WebKit,
  and mobile Chromium against the compose stack with the mock provider.
- `.github/workflows/ci.yml` — four jobs: gitleaks (full history), backend tests
  on Postgres, frontend lint/test/audit/build, and the Compose + Playwright E2E
  job that uploads the Playwright report on failure.

## Deployment shape

One parent domain, web and API on sibling subdomains (for example
`app.example.com` and `api.example.com`). `COOKIE_DOMAIN=.example.com` gives both
hosts one session; `COOKIE_SECURE=true` and HTTPS at the proxy are required.
`ALLOWED_ORIGINS` lists the exact web origin, `TRUSTED_PROXIES` the ingress so
rate limiting sees real client IPs, and `NEXT_PUBLIC_API_BASE_URL` must be set
before building the frontend image. Migrations run with `alembic upgrade head`
before the API serves traffic. Behind a PgBouncer-style transaction pooler,
prepared statements are disabled automatically for Supabase pooler URLs and
port 6543, or explicitly with `DB_DISABLE_PREPARED_STATEMENTS=true`.

## Known architectural limits

- Rate limiting is in-process; multiple API replicas need a shared store.
- No MFA, email verification, password reset, or lockout beyond rate limits.
- Conversation content is stored in plaintext; database access control is the
  boundary.
- The classifier is rule-based and under-classifies subtle prompts (66.1% on the
  current labeled set), always erring toward `GENERAL`.
- Cost is only known when the operator supplies prices.
- Usage events have no export, retention window, or aggregate table yet.
- The CSP keeps `unsafe-inline` for Next.js bootstrap scripts.
