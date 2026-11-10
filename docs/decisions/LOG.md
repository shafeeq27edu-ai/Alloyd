# Decision Log

## 2026-11-08 — Phase 1 dependency baseline

**Context:** A fresh venv from `requirements.txt` failed because async SQLAlchemy needs `greenlet`; the file declared `sqlalchemy` without the `asyncio` extra. Dependencies are unpinned, so the fresh install resolved to newer majors than the previous venv (Anthropic 2.6, google-genai 3.0, bcrypt 5.0, SQLAlchemy 2.1).

**Options:**
- (a) Declare `sqlalchemy[asyncio]`, keep the current resolved versions.
- (b) Pin every dependency to the previous venv's versions.
- (c) Migrate code to current majors and pin.

**Decision:** (a) for Phase 1. Declare the extra, keep the fresh versions, and use the 48-test suite as the baseline. Real SDK compatibility is proven by the Phase 2 smoke script. Pinning or migration is revisited in Phase 4.

**Why:** The minimal change restores a trustworthy baseline without freezing stale SDKs. The tests mock provider SDKs, so they cannot prove real-provider compatibility either way.

**Revisit if:** the smoke script fails against current SDKs, a major upgrade breaks app code, or Phase 4 starts.

## 2026-11-08 — Single model catalog in adapters

**Context:** Model IDs were duplicated across adapters, `router_config.yaml`, `title_generator.py`, and `page.tsx`, and several were retired.

**Options:**
- (a) Keep per-layer lists and sync them manually.
- (b) Make each adapter's `get_models()` the only source; validate the router at startup and expose the catalog through an authenticated API.

**Decision:** (b). `ProviderRegistry.all_models()`, `has_model()`, and `fast_model()` read adapter definitions; `validate_catalog()` refuses startup on unknown providers/models; `GET /api/models` serves the catalog; the frontend and title generator consume it.

**Why:** One list removes drift. Startup validation turns a silent bad route into a fast failure, and the frontend can no longer offer retired IDs.

**Revisit if:** a provider needs per-account model availability or dynamic discovery.

## 2026-11-08 — Auto fallback on MODEL_UNAVAILABLE

**Context:** A retired model returns 404. Treating that as a hard failure leaves Auto mode stuck.

**Decision:** Auto mode falls back on retryable errors **and** `MODEL_UNAVAILABLE`, logging a loud warning. It never falls back on `INVALID_API_KEY` or `BAD_REQUEST`. Manual mode reports the error and never falls back.

**Why:** Fallback on 404 keeps Auto usable when a provider retires a model; auth and request-shape errors are user/config problems that another provider cannot fix. Manual mode must honor the user's explicit choice.

## 2026-11-08 — Buffered SSE parser

**Context:** The frontend split each network chunk on `\n`, so events split across chunks were dropped or corrupted.

**Options:**
- (a) Patch the page-local loop.
- (b) Add a small parser module with cross-chunk buffering and tests.

**Decision:** (b), `src/lib/sse.ts`. It handles CRLF, multi-line `data:`, comments, blank-line dispatch, and a final flush. Stream responses also send `Cache-Control: no-transform` and `X-Accel-Buffering: no`.

**Why:** SSE framing is easy to get subtly wrong; isolating it makes it unit-testable without browser plumbing.

## 2026-11-08 — Image generation deferred to V2

**Context:** `IMAGE_GENERATION` selected text models that cannot generate images, so the route always produced text or failed.

**Decision:** Remove the category from the router, classifier, config, and frontend. Image prompts classify as `GENERAL`. Reintroduce image generation in V2 as a proper capability with an image-capable model catalog.

**Why:** Shipping a category that cannot work is worse than routing those prompts to a model that can discuss them.

## 2026-11-08 — Phase 2 closed with the owner smoke criterion waived

**Context:** Phase 2 acceptance requires the owner to run `backend/scripts/smoke_providers.py` with real provider keys. The owner directed Phase 2 to close and Phase 3 to start without pasting smoke output. The script was never run, so real-provider compatibility is unproven.

**Decision:** Close Phase 2 with that criterion recorded as owner-waived / NOT RUN, never as PASS. Automated evidence stands at 87 backend tests, 8 SSE parser tests, lint 0, build 0. The gap carries into later phases.

**Why:** The owner owns the risk decision, but the gate report must stay honest: an unrun check is not a passed check. Mocked tests cannot prove the real SDKs, model IDs, or streaming behavior.

**Revisit if:** provider calls fail in daily use, model IDs are rejected, or before the Phase 9 release-candidate audit — run the smoke script then.

## 2026-11-08 — Phase 3 auth and browser hardening

**Context:** Login and register had no Origin/CSRF check, the JWT was readable by client JavaScript, `X-Forwarded-For` was trusted from any caller, the CSP allowed `unsafe-eval` in production, `DEBUG` defaulted to on, and some error paths printed exception text that could contain a DSN.

**Options:**
- Login CSRF: (a) double-submit token plus Origin check on every state-changing route; (b) rely on `SameSite=Strict` for the session cookie.
- Session token: (a) cookie-only; (b) keep returning it in JSON for non-browser clients.
- Proxy trust: (a) honor `X-Forwarded-For` only behind configured proxies; (b) trust it from anyone.
- CSP: (a) static policy, drop `unsafe-eval` in production; (b) nonce/hash-based policy.

**Decision:** (a) in each case. Origin + CSRF on login, register, and logout; JWT cookie-only; `TRUSTED_PROXIES` allowlist with an empty default; static CSP without `unsafe-eval` in production, keeping `unsafe-inline`.

**Why:** `SameSite=Strict` breaks the sibling-subdomain flow planned for Phase 4 and does not cover same-site attacks. No in-repo client consumes the JSON token. An allowlist keeps rate limiting meaningful behind a proxy without trusting spoofed headers. A nonce CSP needs more frontend plumbing than this phase allows; `unsafe-inline` is the recorded residual risk in `docs/SECURITY.md`.

**Revisit if:** non-browser API clients need a token flow, a shared rate-limit store is introduced, or the frontend adopts nonce-based CSP.

## 2026-11-09 — Refresh the provider model catalog from live catalogs

**Context:** The walkthrough found every chat failing with `MODEL_UNAVAILABLE`. Groq retired the Llama 3.3/3.1 chat models on 2026-08-16, so the catalog and `router_config.yaml` pointed at IDs the API no longer serves. The Gemini Pro ID had also drifted.

**Options:**
- (a) Keep the old IDs and rely on Auto fallback.
- (b) Update adapter catalogs and routes to IDs the providers currently serve: `groq/openai/gpt-oss-120b` and `openai/gpt-oss-20b`, `gemini/gemini-3.1-pro-preview` and `gemini-3.8-flash`, Anthropic `claude-sonnet-5-5` / `claude-haiku-5-5`.

**Decision:** (b). Startup validation still refuses unknown IDs, so a future retirement fails loudly instead of silently routing.

**Why:** Fallback only hides the problem for Auto users and cannot help Manual mode; the catalog is the single source of truth and must name models that exist. Model IDs rot faster than the app, so this refresh should be repeated before release audits.

**Revisit if:** a provider deprecates these IDs, or a live catalog check can be automated in CI.

## 2026-11-09 — Phase 3 closed with Groq verified live

**Context:** Phase 3 acceptance requires per-fix tests, documented manual checks of cookie flags and headers, a clean secret scan of tree and history, and no secret-like values in test logs. The Phase 2 real-provider smoke was still NOT RUN.

**Decision:** Close Phase 3 with the evidence recorded in `docs/SECURITY.md`. Real-provider compatibility for the one configured provider (Groq) was verified through the running app: both catalog models in Manual mode and Auto routing streamed and persisted correctly. Gemini and Anthropic remain NOT RUN because no keys are configured; `backend/scripts/smoke_providers.py` is still the path to cover them.

**Why:** The app-level run exercises the same server-side adapters, key decryption, and SSE path without exposing stored keys, so it is stronger than a mocked test for Groq. It cannot substitute for keys the project does not have.

**Revisit if:** Gemini or Anthropic keys are added, or before the Phase 9 release audit.

## 2026-11-09 — Phase 4 configuration, cookies, and the compose migration step

**Context:** Phase 4 requires that deployment be a configuration change only, including a frontend and API on sibling subdomains of one parent domain, plus a local production-like stack with Postgres.

**Options:**
- Cookie scope: (a) one parent-domain cookie configured by `COOKIE_DOMAIN`; (b) separate tokens per subdomain; (c) proxy the API through the frontend origin.
- Secure flag: (a) derive from `DEBUG` with an explicit `COOKIE_SECURE` override; (b) always on; (c) always off.
- Migrations in Docker: (a) a one-shot `migrate` service that the API waits for; (b) run `alembic upgrade head` inside the API entrypoint on every boot; (c) document a manual command only.
- Pooler support: (a) auto-detect the Supabase transaction pooler / port 6543 and disable asyncpg's statement cache; (b) require a query parameter from the operator.

**Decision:** (a) in each case. `COOKIE_SECURE` overrides the `DEBUG`-derived default; migrations are a separate compose service gated by `service_completed_successfully`; pooler detection is automatic with `DB_DISABLE_PREPARED_STATEMENTS` as an explicit override.

**Why:** A parent-domain cookie is the only approach that keeps one session for both hosts without a proxy or a second login. Deriving Secure from DEBUG keeps local HTTP workable while production stays secure by default. Auto-migrating inside the API hides failures and races with multiple replicas; a one-shot service makes the step explicit and repeatable. The pooler detection prevents intermittent `prepared statement "__asyncpg_stmt_…" does not exist` errors without every operator needing to know the asyncpg quirk.

**Revisit if:** the product moves to separate registrable domains (then CORS credentials and cookie scope must be redesigned), or migrations gain a release pipeline outside compose.

## 2026-11-09 — Two-host local verification uses lvh.me

**Context:** The Phase 4 acceptance run needs a frontend and API on sibling subdomains without asking the owner to edit the hosts file.

**Decision:** Use `app.lvh.me:3000` and `api.lvh.me:8000`. Public wildcard DNS resolves `*.lvh.me` to `127.0.0.1`, so no hosts-file entry or admin rights are needed, and `lvh.me` is a registrable domain, making both hosts same-site for `SameSite=Lax`.

**Why:** It exercises the real cookie-domain and CORS paths rather than a same-origin proxy, and it is reproducible on any machine.

**Revisit if:** a local TLS setup is needed; then `lvh.me` still works with a self-signed certificate and `COOKIE_SECURE=true`.

## 2026-11-10 — Chat writes commit only after routing succeeds

**Context:** Previously the conversation and user message were written before routing and provider-key resolution. A request that ended in "no API key" or "model unavailable" left behind an empty conversation and an unanswered user message.

**Options:**
- (a) Keep writing first and delete on failure.
- (b) Resolve conversation, routing mode, provider, model, and key first; write the conversation row, the (optional) user message, and the mode switch in one commit immediately before streaming.

**Decision:** (b). Nothing is written before every fallible validation passes. Regenerate writes no user message at all; it reuses the last stored one.

**Why:** Compensation deletes can fail and add partial-write windows. A single commit after validation makes "no partial conversations" a structural property rather than cleanup logic. The tests assert the conversations table stays empty for missing keys, invalid manual routes, and invalid mode switches.

**Revisit if:** a request needs to survive validation but persist before an asynchronous queue consumes it.

## 2026-11-10 — Regenerate reuses the last user turn and replaces answers on success only

**Context:** Regenerating an answer must not duplicate the user message, and a failed regeneration must not destroy the existing answer.

**Options:**
- (a) Delete the old assistant messages up front, then stream.
- (b) Stream first, and on a successful `done` delete the answers that followed the last user message and insert the new one in the same commit.

**Decision:** (b). The history sent to the provider is the stored messages up to and including the last user message, so old answers never influence the new one.

**Why:** Up-front deletion makes a provider outage or an aborted stream lose the previous answer. Doing both writes in one commit keeps the conversation readable at every point. Verified live: a failed regenerate left the original user/assistant pair untouched.

**Revisit if:** the UI later allows editing the user message itself; that becomes a different operation with its own history semantics.

## 2026-11-10 — History is trimmed by a character budget with a visible notice

**Context:** Long conversations can exceed a model's context window, and the failure is a provider 400 that users cannot act on.

**Options:**
- (a) Token-count history per model with a tokenizer library.
- (b) Trim by characters using a conservative characters-per-token assumption.
- (c) Let providers reject oversized requests.

**Decision:** (b). `HISTORY_MAX_CHARS` defaults to 24,000 characters (roughly 6,000 tokens); the system prompt is always kept, the most recent messages are kept, and the response's routing metadata carries "N older messages omitted…" so the UI shows a notice.

**Why:** A tokenizer per provider adds dependencies and drifts with model updates; a character budget with a wide safety margin is predictable and works across every catalog model. The notice keeps the truncation honest instead of silently losing context.

**Revisit if:** models with small context windows join the catalog, or token-accurate budgeting becomes necessary for cost control.

## 2026-11-10 — Account deletion uses ordered bulk deletes, not ORM cascades

**Context:** Deleting an account must remove provider keys, conversations, and messages. The models do not declare database-level cascades.

**Options:**
- (a) Add `ondelete="CASCADE"` to the foreign keys and let the database handle it.
- (b) Issue explicit deletes in dependency order (messages → conversations → keys → user) inside one transaction, after re-checking the password.

**Decision:** (b). A wrong password returns 400 and deletes nothing. On success the auth cookies are cleared in the response.

**Why:** Changing foreign keys needs another migration and a destructive-schema review; explicit deletes make the wipe auditable in one place and keep the same behavior on SQLite tests and Postgres. Password re-authentication prevents a stolen session from destroying the account and its keys.

**Revisit if:** more user-owned tables are added; the delete list must grow with them, and a test should assert every new table is covered.

