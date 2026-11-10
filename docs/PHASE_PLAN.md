# Alloyd — Phased Execution Plan (ship-ready, not deployed)

Save as `docs/PHASE_PLAN.md`. Qoder executes **one phase at a time**. After each phase it stops, posts the gate report, and waits for the owner to reply `APPROVED PHASE N`. It never starts the next phase on its own.

## Operating protocol (every phase)

1. **Plan first.** Post a short plan (goal, approach, files, alternatives, scope check). Wait for approval if the phase is marked 🔒 (security, schema, or dependency changes).
2. **Branch per phase:** `phase-N-<name>`. Small commits, one logical change each. Tests pass before every commit.
3. **Scope discipline.** Only what is listed in the phase. Anything else goes into "Found but not done" in the gate report.
4. **Never print, cat, or echo `.env` values.** List key names only. Never commit secrets.
5. **Decision log.** Any real fork in the road gets an entry in `docs/decisions/LOG.md`.
6. **Ask before:** deleting data/files, rewriting git history, running migrations against the real database, adding dependencies, touching auth/encryption/key storage.
7. **Owner-only actions** (the agent must not do these): rotating real credentials, running anything with real API keys, changing git config, choosing an email provider or license, approving legal text.

### Gate report template (end of every phase)

- What changed (files, why) and the commit list
- Exact commands run and their exact results (tests / lint / build)
- Acceptance criteria: each one marked PASS / FAIL / NOT RUN, with evidence
- Found but not done (new risks, out-of-scope items)
- Risks introduced by this phase
- Proposed next step

**Hard rules:** if any acceptance criterion is FAIL or NOT RUN, the phase is not complete. Never claim something works unless it was run.

## Out of scope for ALL phases below

Payments/credits, agent workflows, tool calling, web search, RAG, code execution, automatic quota-based switching, multi-model comparison/scoring, new providers (GPT later), image generation (V2), skills marketplace/CRUD, **actual deployment**.

---

## Phase 0 — Orientation ✅ DONE
Read-only audit completed. Findings drive the phases below.

---

## Phase 1 — Baseline and guardrails 🔒
**Goal:** a trustworthy foundation: environment that runs, tests that execute, and guardrails that prevent another leak.

- Create a **fresh venv** from `requirements.txt` + new `requirements-dev.txt` (pytest, httpx, aiosqlite, etc.); add the missing `email-validator`. Run `pip check` and pytest. **Report first real test results before fixing anything.**
- Fix only what is needed to get a green baseline; list any failing tests honestly.
- Add to `AGENTS.md` (concise): the secrets rule and the essential security rules from `.agents/rules/*.md` (only `AGENTS.md` is auto-loaded).
- Add `.githooks/pre-commit` (blocks `.env`, key files, secret patterns, DSNs; prints file paths and rule names only, never values). Owner runs `git config core.hooksPath .githooks`.
- Retire stale docs: delete or mark superseded `docs/v1-audit.md` and `alloyd_v1_release_readiness.md`.
- After tests pass: propose (do not run) removal of stale packages (`python-jose`, `passlib`, `google-generativeai`) and the old venv.

**Acceptance:** fresh venv builds from requirements only; `pip check` clean; pytest result recorded (pass count / failures listed); frontend lint and build pass; hook blocks a test file named `.env`; `AGENTS.md` updated.

---

## Phase 2 — Make it actually work with real providers 🔒 ✅ CLOSED
**Status:** Closed 2026-11-08. The owner waived the smoke-script criterion; it remains NOT RUN (see `docs/decisions/LOG.md`).

**Goal:** correct behavior against real provider APIs. No new features.

1. **Single model catalog:** each adapter's `get_models()` is the only list; `ProviderRegistry.all_models()`, `fast_model(provider)`, `validate_catalog()`; router config validated against the catalog at startup; authenticated `GET /api/models`; frontend fetches it (remove hardcoded map in `page.tsx`); title generator picks a fast model from the catalog.
2. **Current model IDs** (Groq `llama-3.3-70b-versatile` / `llama-3.1-8b-instant`, Anthropic `claude-sonnet-5-5` / `claude-haiku-5-5`, Gemini `gemini-4-argon` / `gemini-3.8-flash`), re-verified against each provider's current docs before committing.
3. **Smoke script** `backend/scripts/smoke_providers.py`: reads keys from environment variables in the owner's terminal, validates each key, sends one tiny message per configured model, lists the provider's available models and warns if a catalog ID is missing, prints `provider/model: PASS|FAIL (ms)`, never prints keys. **The owner runs it, not the agent.**
4. **Error mapping:** timeout → `TIMEOUT` (retryable); 5xx → `PROVIDER_UNAVAILABLE` (retryable); 429 → `RATE_LIMIT` (retryable); 404 → `MODEL_UNAVAILABLE`; 401/403 → `INVALID_API_KEY`; 400/422 → `BAD_REQUEST`. Explicit SDK timeouts, plus a first-chunk timeout on streams.
5. **Fallback rules (decision logged):** Auto mode falls back on retryable errors **and** on `MODEL_UNAVAILABLE` (with a loud log warning). Never falls back on `INVALID_API_KEY` or `BAD_REQUEST`. Manual mode shows the error and never falls back.
6. **Gemini system prompts:** pass system messages as `system_instruction` in `send_message` and `stream_chat`, so skills work on Gemini.
7. **SSE:** backend headers (`Cache-Control: no-cache, no-transform`, `X-Accel-Buffering: no`, `Connection: keep-alive`); new `src/lib/sse.ts` that buffers across chunks, handles `\r\n`, multi-line `data:`, comments; replaces the per-chunk splitter; unit-tested.
8. **Defer image generation:** remove `IMAGE_GENERATION` from the category enum, classifier, router config, and frontend; image prompts route to GENERAL; decision-log entry marks it V2.
9. **Legacy rows at read time:** a conversation with an unknown/retired model or `mode=NULL` is treated as Auto with a visible notice (no migration yet).

**Acceptance:** new unit tests for status mapping, fallback rules, Gemini conversion, SSE parser, and catalog validation all pass; app refuses to start on an unknown model in `router_config.yaml`; owner's smoke-script output is all PASS (or failures are explained); lint and build pass.

---

## Phase 3 — Security re-audit and leftovers 🔒
**Goal:** close remaining security gaps. First re-audit what is already implemented (CSRF, rate limits, headers, password policy, Fernet rotation), then fix leftovers.

- Origin/CSRF check on login and register.
- Stop returning the JWT in the JSON response body (cookie only).
- Proxy-aware client IP (trust `X-Forwarded-For` only from configured trusted proxies).
- Production CSP: remove `unsafe-eval`, make connect-src env-driven (dev can differ).
- `DEBUG` defaults to off; app fails to start without `SECRET_KEY` and `ENCRYPTION_KEY` (no insecure defaults).
- `rotate_keys.py` and all error paths never print a DSN or secret.
- Message length limit; sanity limits on request sizes.
- Verify key rotation end to end with a test (decrypt with old key, re-encrypt with new).
- Add a short threat-model note in `docs/SECURITY.md` (what is protected, how, known limits).

**Acceptance:** tests for each fix; manual checks documented (cookie flags, headers); secret scan of tree and git history is clean; no secret-like value appears in logs during a test run.

---

## Phase 4 — Config and ship-readiness (without deploying) 🔒
**Status:** **APPROVED** — gate report in `docs/PHASE4_GATE_REPORT.md`; owner-delegated self-verification and approval recorded 2026-11-10.

**Goal:** the app can be deployed by changing config only.

- All environment-specific values from env vars (API base URL, CORS origins, cookie domain/secure flag, CSP origins); `.env.example` for backend **and** frontend; no hardcoded localhost in code.
- Works with the frontend and API on sibling subdomains of one domain (cookie/CORS/CSRF verified in a local two-host setup, for example via hosts-file entries).
- `/health` endpoint (and a readiness check that verifies the database), documented migration command, startup DB check.
- Dockerfiles for backend and frontend plus a `docker-compose.yml` that runs the stack locally like production (Postgres included).
- Pin Python and Node versions (one version each) and pin dependencies; handle the Supabase pooler + `asyncpg` prepared-statement setting if applicable.
- Structured logging with no keys and no message content.

**Acceptance:** `docker compose up` brings up the working stack from a clean clone using only `.env.example` values plus placeholders; health endpoint passes; login works across the two-host local setup.

---

## Phase 5 — Data integrity and chat completeness 🔒
**Status:** Gate report posted 2026-11-10 (`docs/PHASE5_GATE_REPORT.md`); awaiting `APPROVED PHASE 5`.
**Goal:** correct data handling and the chat basics real users expect.

- Persist the user message only after request validation and routing succeed (no partial conversations).
- History truncation/trimming to fit model context limits, with a visible notice; unit tests.
- Backfill migration for `conversations.mode=NULL` (reviewed by owner **before** running against any real database).
- Account deletion (wipes keys, conversations, messages) with confirmation and tests.
- Check which of these exist and add the missing ones: stop generating, regenerate, copy message, retry after a failed response, delete-conversation confirmation.
- Add the needed database indexes (`conversations.user_id`, `messages.conversation_id`).

**Acceptance:** tests for each; manual walkthrough recorded; migration tested on a scratch Postgres (from Phase 4's compose), not on the production database.

---

## Phase 6 — Quality gates
**Goal:** automated protection against regressions.

- GitHub Actions CI: backend tests, frontend lint, production build, secret scan (gitleaks), `pip-audit`, `npm audit` on every push/PR.
- Run the backend tests against **Postgres** in CI (production parity), not only SQLite.
- Playwright smoke test: register → add key (mock provider) → send message → switch model → delete conversation.
- Frontend unit tests for the SSE parser and API client.
- Manual pass on mobile viewport and Safari (cookies + SSE); record findings.

**Acceptance:** CI green on a clean branch; failing-test demonstration (break something on purpose, CI catches it, revert).

---

## Phase 7 — Measurement
**Goal:** evidence for future decisions, with no message content ever logged.

- Routing event per message: category, provider/model, auto vs manual, fallback fired, error code, latency.
- Token counts and estimated cost per message, shown in the UI.
- Labeled set of 50–100 representative prompts and a script that reports classifier accuracy.
- A simple `scripts/report_usage.py` summarizing the above.

**Acceptance:** events stored without content; cost display tested; classifier accuracy report produced.

---

## Phase 8 — Docs and legal drafts
**Goal:** a stranger can run it, and the docs match the code.

- Root `README.md` (setup, architecture, security model, how to run tests).
- `docs/ARCHITECTURE.md` generated from the real code.
- `docs/decisions/LOG.md` fully synced (removed LLM classifier, categories shipped, model catalog, fallback rules, SSE parser, image deferral).
- Draft privacy policy and terms of use (marked **DRAFT — owner review required**): what is stored, what is encrypted, keys only go to their own provider.
- License: owner chooses; agent adds it.

**Acceptance:** someone following the README from a fresh clone gets the app running (agent verifies in a clean directory); no doc contradicts the code.

---

## Phase 9 — Dogfood and release-candidate review
**Goal:** prove it works in real use before anyone else touches it.

- Owner uses Alloyd daily for one week for real work and keeps a running list of problems.
- Agent fixes only issues from that list (no new features), one small commit each.
- Final release-candidate audit by the agent: full checklist re-run against the repo, with evidence.
- Owner invites 3–5 developers for a cold test; observe onboarding (key setup is the highest-risk step).

**Acceptance:** one week of use with no silent failures; all P0 items closed; RC audit shows PASS with evidence.

---

## Deferred (do not start)

- **Deployment** — decided later, after Phase 9. Constraints are already handled in Phase 4: one parent domain, SSE-capable host, env-driven config.
- **V2, in this order:** usage tracking and quota-aware auto-switching → image generation as a proper category → Comparison Mode → GPT as a fourth provider → tool use/web search → Agent Mode → payments. Custom product skills come after V2.