# Alloyd

One workspace for several AI providers, with your own API keys. Alloyd routes
each message to a model by task type, lets you override the choice, and streams
the answer in a chat UI with saved history.

- **BYOK only.** You add provider keys in Settings. The backend validates,
  encrypts, and stores them; they never reach the browser after entry.
- **Providers:** Groq, Google Gemini, and Anthropic Claude.
- **Routing:** Auto mode classifies each message (coding, research, writing,
  planning/decision, general) and picks a model from `backend/router_config.yaml`.
  Manual mode uses exactly the model you pick.
- **Skills:** `@reviewer`, `@explainer`, `@summarizer`, `@writer`,
  `@brainstormer`, `@researcher` prepend a system prompt.
- **Measurement:** every provider attempt records a content-free usage row
  (route, status, tokens, latency, cost) that you can aggregate.

Alloyd is pre-release software: Phases 6–8 await owner approval, and it has
not been deployed yet. See [Project status](#project-status).

## Requirements

Either:

- **Docker** with Compose v2 — the fastest path, no local Python/Node needed; or
- **Python 3.11**, **Node.js 22.11**, and **PostgreSQL 16** for local dev.

You also need an API key from at least one supported provider. No keys are
included in the repository.

## Quick start (Docker)

```bash
git clone https://github.com/shafeeq27edu-ai/Alloyd.git
cd Alloyd
docker compose up --build
```

Open <http://localhost:3000>, choose **Register**, and use a password of at
least 12 characters. Then open **Settings**, select a provider, paste its key,
and save it. Alloyd validates the key by calling the provider once; after that
you can start a conversation.

The stack runs PostgreSQL, a one-shot Alembic migration, the API on
<http://localhost:8000> (`/health`, `/ready`), and the web app on port 3000.

The compose file ships **development-only** defaults for `SECRET_KEY`,
`ENCRYPTION_KEY`, and the database password. Override them through a root
`.env` file or your shell before any real use — see
[`docs/RUNNING.md`](docs/RUNNING.md#docker-compose).

If a port is already taken, set `POSTGRES_PORT`, `BACKEND_PORT`, or
`FRONTEND_PORT`. When the API port changes, also set
`NEXT_PUBLIC_API_BASE_URL=http://localhost:<port>/api`, because the browser URL
is baked into the frontend build.

```bash
docker compose down      # stop
docker compose down -v   # stop and delete the database volume
```

## Local development without Docker

The database can be the compose Postgres or any PostgreSQL 16 instance. SQLite
also works for single-user local runs (`sqlite+aiosqlite:///./alloyd.db`); the
migrations apply cleanly, but Postgres is the supported production-like path
and what CI tests against.

**1. Database (Postgres in Docker):**

```bash
docker compose up -d db
```

If host port 5432 is busy on your machine (Windows often reserves it), publish
another port and use it in the URL below:

```bash
POSTGRES_PORT=5435 docker compose up -d db
# DATABASE_URL=postgresql+asyncpg://alloyd:alloyd_dev_password@127.0.0.1:5435/alloyd
```

**2. Backend:**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env              # Windows: copy .env.example .env
```

Fill in `DATABASE_URL`, `SECRET_KEY` (32+ characters), and `ENCRYPTION_KEY`
(a 32-byte url-safe base64 Fernet key) in `backend/.env`. Generate them with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Then apply the schema and start the API:

```bash
alembic upgrade head
uvicorn app.main:app --reload
```

`alembic.ini` and the app both read `backend/.env`, so run these from
`backend/`. The API refuses to start if `router_config.yaml` names a provider or
model that is not in the adapter catalog, or if the secrets are placeholders.

**3. Frontend (second terminal):**

```bash
cd frontend
npm ci
npm run dev
```

`NEXT_PUBLIC_API_BASE_URL` defaults to `http://localhost:8000/api` and the
backend allows `http://localhost:3000` by default, so no extra configuration is
needed for a same-host setup. All variables are documented in
[`docs/RUNNING.md`](docs/RUNNING.md#environment-variables).

## How a message flows

```
Browser (Next.js)  ──POST /api/chat──▶  FastAPI
      ▲                                  │  1. auth cookie + CSRF check
      │                                  │  2. classify + route (auto)
      │  SSE: routing, message,          │  3. decrypt the user's provider key
      │       usage, done | error        │  4. write conversation + user message
      └──────────────────────────────────┘  5. stream from the provider
                                             └─▶ fallback once, auto mode only
```

Nothing is written to the database until routing and key resolution succeed, so
a failed request never leaves an empty conversation. Details, including the
fallback rules and the usage-event schema, are in
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Security model

- Provider keys are encrypted at rest with Fernet, returned only as a mask, and
  never logged or sent to the client after entry.
- Sessions are HttpOnly, `SameSite=Lax` cookies; no token is stored in
  `localStorage`. Every state-changing request requires a double-submit CSRF
  token and an allowlisted `Origin`.
- Every key, conversation, message, and usage row is filtered by the
  authenticated user on the server. Foreign resources return 404, not 403.
- Errors are normalized; users never see stack traces or raw provider payloads.
- Usage events store routing metadata and counts, never prompts or answers.

Known limitations — in-memory rate limiting, no MFA or password reset,
plaintext conversation content at rest, no cost figures until `PRICING_JSON` is
configured — are listed in [`docs/SECURITY.md`](docs/SECURITY.md#known-limitations).

## Tests

```bash
# Backend (from backend/, virtualenv active)
python -m pytest

# The same suite on Postgres, as CI runs it
TEST_DATABASE_URL=postgresql+asyncpg://alloyd:alloyd_dev_password@127.0.0.1:5435/alloyd_test \
  python -m pytest

# Frontend (from frontend/)
npm test            # SSE parser, API client, usage formatting
npm run lint
npm run build       # requires NEXT_PUBLIC_API_BASE_URL
npm run test:e2e    # Playwright smoke against the running stack
```

`TEST_DATABASE_URL` must point at a disposable database: the suite creates and
drops tables. The end-to-end suite needs the compose stack running with
`ENABLE_MOCK_PROVIDER=true`; the exact command is in
[`docs/RUNNING.md`](docs/RUNNING.md#end-to-end-smoke-test).

GitHub Actions runs four jobs on every push and pull request: a gitleaks secret
scan, the backend suite against Postgres, frontend lint/tests/audit/build, and
the Compose + Playwright E2E job.

## Measurement scripts

```bash
cd backend
python scripts/report_usage.py --days 7   # routing, tokens, latency, cost
python scripts/evaluate_classifier.py     # accuracy on the labeled prompt set
```

Costs come only from operator-supplied prices (`PRICING_JSON`, USD per million
tokens). Without them the UI shows tokens and no dollar amount. Current
classifier accuracy and its weak spots are recorded in
[`docs/CLASSIFIER_ACCURACY.md`](docs/CLASSIFIER_ACCURACY.md).

## Project docs

| Document | Contents |
| :--- | :--- |
| [`docs/RUNNING.md`](docs/RUNNING.md) | Every environment variable, compose, migrations, sibling subdomains, E2E |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Modules, request lifecycle, data model, frontend, tests |
| [`docs/SECURITY.md`](docs/SECURITY.md) | Threat model, controls, limitations, production checklist |
| [`docs/PHASE_PLAN.md`](docs/PHASE_PLAN.md) | Phase ledger and verification records |
| [`docs/decisions/LOG.md`](docs/decisions/LOG.md) | Architecture decision records |
| [`docs/CLASSIFIER_ACCURACY.md`](docs/CLASSIFIER_ACCURACY.md) | Labeled-set results and failure patterns |
| [`docs/legal/`](docs/legal/) | Draft privacy policy and terms of use (**owner review required**) |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Workflow, rules, commit style |

## Project status

Alloyd V1 succeeds when the builder and a few developers use it for real work
for a week without switching back to provider web UIs.

Phases 1–8 are implemented and verified; owner approval for Phases 6, 7, and 8
is still pending. Phase 9 is one week of dogfooding followed by a
release-candidate audit. Deployment is deliberately deferred until after that.

## License

MIT — see [`LICENSE`](LICENSE). The copyright line reads "Alloyd contributors";
the owner can replace it with a legal name without changing the license terms.
