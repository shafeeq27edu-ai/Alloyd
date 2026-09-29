# Alloyd V1 Audit

**Date**: 2026-09-29  
**Scope**: Full codebase read — every backend and frontend source file  
**Verdict**: 🟡 CONDITIONALLY READY — functional for internal dogfooding, not for public deployment

---

## 1. V1 Definition of Done (from AGENTS.md)

> The builder and a small group of developers can use Alloyd for real work for at least one week without needing to constantly switch to separate AI provider interfaces.

### Does the current codebase meet this?

**Yes, conditionally.** Every piece of the core loop is implemented and wired end-to-end:

| Capability | Status | Notes |
|---|---|---|
| Register / Login | ✅ Working | bcrypt hashing, JWT cookies |
| BYOK key storage | ✅ Working | Fernet-encrypted, per-user |
| Manual model selection | ✅ Working | Provider + model picker in chat UI |
| Auto-routing | ✅ Working | Keyword classifier → YAML-driven rule router |
| Streaming chat | ✅ Working | SSE via fetch, markdown rendering |
| Fallback on failure | ✅ Working | Retryable errors trigger alternate provider |
| Conversation history | ✅ Working | Per-user, DB-backed, sidebar navigation |
| Async title generation | ✅ Working | Uses cheapest available provider key |
| Skills (system prompts) | ✅ Working | 6 skills, triggered via `@skill_name` |
| Settings page | ✅ Working | Key management, onboarding redirect |
| CSRF protection | ✅ Working | Synchronizer token pattern + Origin validation |
| Rate limiting | ✅ Working | In-memory sliding window (login, register, chat) |

The product is usable *today* for the described scenario on localhost.

---

## 2. Architecture

```
frontend/  (Next.js 16 + React 19 + Tailwind 4)
  src/app/           — page.tsx (chat), login/, settings/
  src/components/    — Sidebar, Select, Toast
  src/lib/           — api.ts (fetchWithAuth, CSRF handling)

backend/  (FastAPI, async SQLAlchemy, PostgreSQL)
  app/api/           — auth, chat, keys, conversations, deps
  app/core/          — security, encryption, router, classifier, skills, rate_limit, title_generator, errors
  app/db/            — models, database
  app/providers/     — base, registry, groq, anthropic, gemini adapters
  router_config.yaml — rule-based routing table
  tests/             — 7 test files (auth, chat, classifier, conversations, keys, rate_limit, conftest)
```

### Observations

- **Clean layering.** API → Core → DB → Providers. No circular imports. Provider adapters are self-contained.
- **Registry pattern works.** `ProviderRegistry.register()` in `__init__.py` keeps adapter discovery simple and explicit.
- **Router is data-driven.** `router_config.yaml` separates routing policy from code. Good for iteration.
- **Classifier is heuristic.** Regex-based keyword matching is fast and deterministic. Adequate for V1 — will misclassify edge cases but won't crash.
- **No service layer.** API handlers do direct DB queries. Acceptable at current size (~5 endpoints), but will need extraction before adding features.

---

## 3. Security

### What's been done well

| Control | Implementation |
|---|---|
| Password hashing | `bcrypt` (direct, not passlib) |
| JWT auth | `PyJWT` HS256, HttpOnly cookie, `Secure` toggled by `DEBUG` |
| Key encryption | Fernet symmetric encryption at rest |
| CSRF | Synchronizer token + Origin validation + `hmac.compare_digest` |
| Rate limiting | Per-IP login/register, per-user chat |
| Cookie flags | `HttpOnly=True`, `Secure=not DEBUG`, `SameSite=Lax` |
| Dependency hygiene | Replaced `python-jose`, `passlib`, `google-generativeai` |

### What remains concerning

| Issue | Severity | Detail |
|---|---|---|
| Default `SECRET_KEY` in config.py | **P0** | `"super_secret_key_for_testing_only"` — if `.env` is missing, production signs JWTs with a known key. Should fail-fast instead of defaulting. |
| Default `ENCRYPTION_KEY` in config.py | **P0** | `"VlYp1_8P_aIqTf8w4P5q9G_oV7qHk_4fB_3oU_1Yg_8="` — same issue. All stored API keys become decryptable with a public value. |
| `DEBUG=True` default | **P1** | Means `Secure=False` on cookies by default. Acceptable for localhost dev, but a forgotten `.env` in production disables cookie security. |
| No password policy | **P1** | `UserCreate` accepts any string. A 1-character password passes validation. |
| `alloyd.db` committed to repo | **P1** | 57KB SQLite file in `backend/`. Contains test data. Should be in `.gitignore`. |
| Rate limiter is in-memory | **P2** | Resets on restart, per-worker in multi-worker deployments. Documented and acceptable for V1. |
| No token rotation / refresh | **P2** | 7-day token lifetime, no refresh flow. Users will be force-logged-out weekly. |
| `X-Forwarded-For` trusted blindly | **P2** | `get_client_ip()` trusts the first entry without proxy validation. Spoofable behind a misconfigured reverse proxy. |

### Recommendation

For internal dogfooding: **fix the two P0s** (crash if `SECRET_KEY` / `ENCRYPTION_KEY` are defaults, or remove defaults entirely). The rest can wait.

---

## 4. Provider Adapters

All three adapters (`groq`, `anthropic`, `gemini`) follow the same contract:

| Method | Purpose |
|---|---|
| `get_models()` | Returns hardcoded model list |
| `send_message()` | Non-streaming call (used by title generator) |
| `stream_chat()` | SSE generator for chat |
| `_map_error()` | Maps SDK exceptions → `ProviderError` |

### Quality notes

- **Gemini system messages are silently dropped.** `_convert_messages()` skips `role == "system"`. The Gemini SDK supports a `system_instruction` parameter — it's not being used. Skills injected as system prompts will be ignored when routed to Gemini.
- **Anthropic correctly separates system messages** into the `system` kwarg. Good.
- **`max_tokens` is hardcoded to 4096** in the Anthropic adapter. Not configurable. Adequate for V1.
- **New Groq/Anthropic clients are instantiated per request.** No connection pooling. Acceptable at low scale.
- **Model lists are hardcoded.** No dynamic discovery. Models will go stale over time. Acceptable for V1 since the user can override via manual mode.

### Bug: Gemini system prompt silently dropped

This is a **functional gap**, not a crash. If a user invokes `@researcher` and auto-routing sends it to Gemini, the system prompt is silently ignored. The model still responds, but without the skill context.

**Impact**: Medium. Degrades quality of skill-routed Gemini responses.  
**Fix**: Pass system messages via `system_instruction` in `generate_content` kwargs.

---

## 5. Chat & Routing

### Stream lifecycle

1. Rate limit check (429 before any work)
2. Conversation lookup or creation
3. User message saved to DB
4. Route: auto (classify → route → key lookup) or manual
5. Stream begins → `routing` event → `message` chunks → `done` event
6. Assistant message saved to DB on `done`
7. On retryable error (before first chunk): fallback once, then surface error

### Issues found

- **`asyncio.create_task` for title generation** runs a detached task. If the app shuts down while it's running, the task is silently cancelled. Not harmful, but titles may occasionally not update.
- **Title generator creates its own session** (`AsyncSessionLocal()`), which is correct — it doesn't share the request's DB session.
- **`category` variable referenced in fallback scope.** In `generate()`, `category` is only defined when `req_mode == "auto"`. The `provider_availability` dict is also only defined in auto mode. If `req_mode == "manual"` and a retryable error occurs, the fallback branch would reference undefined variables. However, fallback is gated on `req_mode == "auto"`, so this path is unreachable. **Safe but fragile.**
- **No message length limit.** A user could send a 10MB message body. FastAPI has a default body limit, but it's generous.

---

## 6. Frontend

### What works

- Clean dark-mode UI with responsive layout
- Sidebar with conversation history, mobile hamburger menu
- Auto-resizing textarea, Enter-to-send, Shift+Enter for newlines
- Markdown rendering with syntax highlighting (`react-markdown` + `prism`)
- Routing metadata shown on hover (provider, model, category, auto badge)
- Skill quick-start cards on empty state
- Toast notifications for errors
- Onboarding redirect (no keys → settings page)

### Issues

| Issue | Severity | Detail |
|---|---|---|
| `API_BASE_URL` defaults to localhost | **P0 for deployment** | Already uses `process.env.NEXT_PUBLIC_API_BASE_URL` with fallback. Fixed as of the CSRF work. This is only a deployment-config concern now, not a code change. |
| Greeting is hardcoded "Good afternoon" | **P3** | Doesn't change with time of day. Minor polish. |
| Model list is hardcoded in frontend | **P2** | `page.tsx` duplicates the model list from the backend adapters. No `/api/models` endpoint to sync them. |
| No loading indicator during streaming | **P3** | The send button disables, but there's no visual "thinking" state. |
| SSE parsing splits on `\n` | **P2** | The parser in `handleSend` splits chunks by newline and matches `event:` / `data:` prefixes. This works for well-formed SSE but can break if a chunk boundary falls mid-event. Edge case — unlikely to cause real issues in practice. |
| No conversation delete confirmation | **P3** | Sidebar delete is immediate. No undo. |

---

## 7. Database

- 4 tables: `users`, `provider_keys`, `conversations`, `messages`
- UUIDs as primary keys (string-based, `uuid4`)
- Cascade deletes: user → keys, user → conversations → messages
- Alembic configured for migrations
- `alloyd.db` (SQLite) in the repo — appears to be a dev artifact, not the production DB path (which is PostgreSQL via `DATABASE_URL`)

### Notes

- No indexes beyond the default PK indexes and `users.email` (which has `index=True`).
- `conversations` and `messages` query by `user_id` and `conversation_id` respectively — these foreign keys would benefit from explicit indexes at scale. Not a V1 issue.
- No soft deletes. Conversation deletion is permanent.

---

## 8. Tests

7 test files exist:

| File | Coverage |
|---|---|
| `test_auth.py` | Registration, login |
| `test_chat.py` | Chat streaming, routing, fallback |
| `test_classifier.py` | Task classification categories |
| `test_conversations.py` | Conversation CRUD |
| `test_keys.py` | Key storage, retrieval, deletion |
| `test_rate_limit.py` | Rate limit enforcement, 429 responses |
| `conftest.py` | Test fixtures, mock DB, mock providers |

### Assessment

- Tests exist for all major backend flows. This is significantly better than zero.
- No frontend tests (no Jest/Vitest/Playwright). Acceptable for V1 — manual testing is sufficient at this stage.
- Tests use a mock provider and in-memory SQLite. They test the API contract, not real provider integration.

---

## 9. What's missing for "real work for one week"

### Must fix (blocks dogfooding)

1. **Remove default `SECRET_KEY` / `ENCRYPTION_KEY`** — these must fail if not explicitly set, or dogfooding data is insecure even on localhost.

### Should fix (will cause friction during the week)

2. **Gemini system prompt support** — skills routed to Gemini will be noticeably worse.
3. **A `/api/models` endpoint** — so the frontend model list stays in sync without manual code changes.

### Nice to have (won't block the week)

4. Time-appropriate greeting
5. Streaming "thinking" indicator
6. Delete confirmation in sidebar
7. Password minimum length

---

## 10. What's NOT missing

These are things that might *seem* needed but are explicitly out of scope for V1:

- Multi-user admin panel — not needed, it's for a small group
- OpenAI support — not promised for V1
- File uploads / multimodal — not promised
- Usage tracking / analytics — not promised
- Custom routing rules UI — YAML file is fine for now
- Redis-backed rate limiting — in-memory is fine for single-instance dogfooding
- CI/CD pipeline — manual deploy is fine for V1
- Comprehensive error monitoring — `print()` in title_generator is honest about the current state

---

## 11. File inventory

### Backend (17 source files)
- `app/main.py` — FastAPI app, CORS, router mounts
- `app/config.py` — Settings via pydantic-settings
- `app/api/auth.py` — Register, login, logout, CSRF, /me
- `app/api/chat.py` — Streaming chat with routing + fallback
- `app/api/conversations.py` — List, messages, delete
- `app/api/keys.py` — CRUD for encrypted provider keys
- `app/api/deps.py` — Auth dependency, CSRF verification
- `app/core/security.py` — bcrypt, JWT creation
- `app/core/encryption.py` — Fernet encrypt/decrypt
- `app/core/router.py` — YAML-driven rule router
- `app/core/classifier.py` — Regex task classifier
- `app/core/skills.py` — 6 hardcoded skill definitions
- `app/core/rate_limit.py` — In-memory sliding window
- `app/core/title_generator.py` — Async title via cheapest provider
- `app/core/errors.py` — ProviderError + ErrorCode enum
- `app/db/models.py` — User, ProviderKey, Conversation, Message
- `app/db/database.py` — Engine, session factory, Base
- `app/providers/base.py` — Abstract adapter interface
- `app/providers/registry.py` — Provider registry
- `app/providers/__init__.py` — Registers groq, anthropic, gemini
- `app/providers/groq_adapter.py` — Groq SDK adapter
- `app/providers/anthropic_adapter.py` — Anthropic SDK adapter
- `app/providers/gemini_adapter.py` — Google GenAI SDK adapter

### Frontend (8 source files)
- `src/app/page.tsx` — Main chat page (414 lines)
- `src/app/layout.tsx` — Root layout
- `src/app/globals.css` — Global styles
- `src/app/login/page.tsx` — Login/register page
- `src/app/settings/page.tsx` — Key management settings
- `src/components/Sidebar.tsx` — Conversation sidebar
- `src/components/Select.tsx` — Custom select component
- `src/components/Toast.tsx` — Toast notification system
- `src/lib/api.ts` — API client with auth + CSRF

### Tests (7 files)
- `tests/conftest.py`, `test_auth.py`, `test_chat.py`, `test_classifier.py`, `test_conversations.py`, `test_keys.py`, `test_rate_limit.py`

### Config
- `router_config.yaml` — 6-category routing rules
- `requirements.txt` — 14 Python dependencies
- `package.json` — 7 runtime + 8 dev JS dependencies
- `.env.example` — Template for production secrets
- `alembic.ini` + `alembic/` — Migration tooling

---

## 12. Verdict

| Question | Answer |
|---|---|
| Can a developer register, add API keys, and chat? | Yes |
| Does auto-routing work? | Yes |
| Does manual model selection work? | Yes |
| Do skills inject correctly? | Yes (except Gemini — system prompt dropped) |
| Is the auth secure enough for internal use? | Yes, if P0 defaults are removed |
| Is the UI pleasant to use? | Yes — clean, dark, responsive |
| Will it survive a week of real use? | Likely, with the two fixes above |

**Final status: 🟡 CONDITIONALLY READY**

Fix the two P0s (default secrets), optionally fix Gemini system prompts, and this is ready for a one-week internal dogfood.
