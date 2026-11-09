# Phase 4 Gate Report — Config and ship-readiness

**Date:** 2026-11-09
**Branch:** `phase-4-ship-readiness`
**Status:** Complete; awaiting `APPROVED PHASE 4`.

## What changed

| Commit | Scope |
| :--- | :--- |
| `feat(config): scope cookies, readiness, and logging from the environment` | `COOKIE_DOMAIN` / `COOKIE_SECURE`, startup DB check with retries, `GET /ready` (`SELECT 1`), JSON request logs with request IDs, PgBouncer/asyncpg statement-cache handling, `DB_*` assembly, pinned Python dependencies, readiness and config tests |
| `build(frontend): pin dependencies and make runtime config explicit` | Exact dependency pins, Next.js 16.4.5, standalone output, committed `.env.example`, env-driven dev origins, production build guard for `NEXT_PUBLIC_API_BASE_URL` |
| `build: add pinned images and a Postgres compose stack` | Python 3.11.9 and Node 22.11.0 images (non-root), multi-stage standalone frontend, Postgres 16, one-shot `migrate` service, health checks, loopback-only published ports |
| `docs: record Phase 4 configuration decisions and evidence` | `docs/RUNNING.md`, security verification record, decision-log entries |

## Commands and results

| Command | Result |
| :--- | :--- |
| `pytest -q` (backend, `.venv`) | **110 passed**, 1 pre-existing Pydantic warning |
| `npm run lint` | clean |
| `npm run build` with `NEXT_PUBLIC_API_BASE_URL` | success (Next.js 16.4.5) |
| `npm run build` without `NEXT_PUBLIC_API_BASE_URL` | fails fast with a clear config error (intended) |
| `npm audit` | 0 critical, 0 high; 10 moderate in dev-only tooling |
| `docker compose config` | valid |
| Clean-clone `docker compose build` + `up -d` (no `.env`) | db, backend, frontend healthy |
| `GET /health`, `GET /ready` | 200, 200 |
| Stop Postgres → `/ready` → restart Postgres | 503 → 200 without restarting the API |
| Clean-clone register → login → `/auth/me` | 200, 200, 200 |
| Two-host browser login (`app.lvh.me:3001` → `api.lvh.me:8001`) | success; cookie `Domain=.lvh.me; HttpOnly; SameSite=lax`; `/auth/me` 200 |
| Cross-host CORS preflight-equivalent response | `Access-Control-Allow-Origin: http://app.lvh.me:3001`, credentials allowed |
| Running backend log scan (keys, `Bearer`, API-key fields, DSNs) | 0 hits |

## Acceptance criteria

| Criterion | Result | Evidence |
| :--- | :--- | :--- |
| Env-driven API URL, CORS, cookie domain/secure, CSP origins; `.env.example` for both apps | **PASS** | Backend and frontend examples; CORS/CSP/cookie values come from env. Production builds refuse to start without an API URL. Dev-only localhost fallbacks remain for running without env files; they are never used by the container build. |
| No production hardcoded localhost | **PASS** | `NEXT_PUBLIC_API_BASE_URL` is mandatory for production builds; compose passes it at build time. |
| Sibling-subdomain login works locally | **PASS** | Browser register/login on `app.lvh.me:3001` against `api.lvh.me:8001`; parent-domain cookie and authenticated request verified. |
| `/health`, DB readiness, documented migration command, startup DB check | **PASS** | `/health` (liveness), `/ready` (503/200 tested), `alembic upgrade head` documented and run by the compose `migrate` service, startup retries implemented. |
| Dockerfiles + compose with Postgres, production-like | **PASS** | Clean clone (no `.env`) brought the stack up healthy. Host ports 5432/8000/3000 were occupied or reserved on this Windows machine, so the run published 5433/8001/3001 and 5434/8002/3002; compose defaults to the standard ports. |
| Pinned Python/Node versions and dependencies; pooler handling | **PASS** | `.python-version` 3.11.9, `.nvmrc` 22.11.0, exact requirements and `package.json` versions, automatic statement-cache disable for Supabase/PgBouncer URLs. |
| Structured logging without keys or message content | **PASS** | JSON request lines with method/path/status/duration/request ID; no bodies or headers; uvicorn access log disabled in the image. |

## Found but not done

- Ten moderate `npm audit` findings remain in dev-only tooling (`eslint-config-next`'s TypeScript ESLint chain and `@tailwindcss/typography`). The suggested fixes are semver-major downgrades; Phase 6 owns dependency gating.
- Rate limiting is still in-memory and per process; a multi-replica deployment needs Redis or an equivalent store.
- Compose defaults contain development-only credentials. TLS termination, a real domain, and `COOKIE_SECURE=true` are deployment-time steps and were not exercised.
- Real-provider smoke inside the container: NOT RUN (no provider keys are supplied to the stack; keys are never baked into images). The Phase 2 Gemini/Anthropic smoke remains NOT RUN.
- A parent-domain cookie is visible to every subdomain of that parent. That is the tradeoff for one shared session across `app.` and `api.`.

## Risks introduced

- `DEBUG=false` with plain-HTTP compose still emits HSTS. Browsers ignore HSTS received over HTTP, but a local HTTPS proxy should be used if that matters.
- Changing `NEXT_PUBLIC_API_BASE_URL` requires rebuilding the frontend image because the value is inlined into the client bundle.
- Startup now refuses to serve traffic if the database never becomes reachable within the retry window. This is deliberate, but it makes a misconfigured `DATABASE_URL` a hard start failure.

## Proposed next step

Review and reply `APPROVED PHASE 4`, then start Phase 5 on `phase-5-data-integrity`.
