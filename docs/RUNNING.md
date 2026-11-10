# Running Alloyd

Two ways to run the stack: local dev servers, or the production-like Docker
compose stack. Both are driven by environment variables; no hostnames are
hardcoded in application code.

## Environment variables

Backend (`backend/app/config.py`):

| Variable | Purpose | Default |
| :--- | :--- | :--- |
| `DATABASE_URL` | Async SQLAlchemy URL (`postgresql+asyncpg://…` or `sqlite+aiosqlite:///…`) | required unless `DB_*` parts are set |
| `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` | Alternative to `DATABASE_URL`; the URL wins when both are present | — |
| `SECRET_KEY` | JWT signing key, at least 32 characters | required |
| `ENCRYPTION_KEY` | 32-byte url-safe base64 Fernet key | required |
| `PREVIOUS_ENCRYPTION_KEY` | Old Fernet key during rotation | empty |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Session lifetime | `10080` |
| `DEBUG` | Disables Secure cookies and HSTS when true | `false` |
| `ALLOWED_ORIGINS` | Exact browser origins allowed with credentials | `http://localhost:3000` |
| `COOKIE_DOMAIN` | Parent domain for auth cookies (sibling subdomains) | empty |
| `COOKIE_SECURE` | Force the Secure cookie flag; defaults to `not DEBUG` | derived |
| `TRUSTED_PROXIES` | IPs/CIDRs allowed to set `X-Forwarded-For` | empty |
| `MAX_REQUEST_BYTES` | Request body cap | `1000000` |
| `HISTORY_MAX_CHARS` | Character budget for conversation history sent to providers | `24000` |
| `LOG_LEVEL`, `LOG_FORMAT` | Structured logging (`json` or `text`) | `INFO`, `json` |
| `DB_DISABLE_PREPARED_STATEMENTS` | Disable asyncpg's statement cache for PgBouncer | `false` |
| `DB_CONNECT_TIMEOUT_SECONDS` | Readiness/startup probe timeout | `5` |
| `STARTUP_DB_CHECK_RETRIES`, `STARTUP_DB_CHECK_DELAY_SECONDS` | Startup database retry policy | `10`, `2` |

Frontend:

| Variable | Purpose | Default |
| :--- | :--- | :--- |
| `NEXT_PUBLIC_API_BASE_URL` | API origin including `/api`, baked into the client bundle | `http://localhost:8000/api` |
| `NEXT_ALLOWED_DEV_ORIGINS` | Extra dev-server hostnames (development only) | empty |

Copy `backend/.env.example` and `frontend/.env.example` and fill in real
values. Never commit `.env` files.

## Health and readiness

- `GET /health` — liveness; returns `{"status": "ok"}` without touching the database.
- `GET /ready` — readiness; runs `SELECT 1` and returns `200` or `503`.

The API also verifies the database during startup and retries according to
`STARTUP_DB_CHECK_RETRIES` / `STARTUP_DB_CHECK_DELAY_SECONDS` before giving up.

## Database migrations

The schema is owned by Alembic; the app never calls `create_all` at startup.

```bash
cd backend
alembic upgrade head          # apply migrations
alembic current               # show the applied revision
alembic revision --autogenerate -m "describe the change"
```

In Docker, migrations run as a one-shot `migrate` service before the API
starts. To re-run them manually:

```bash
docker compose run --rm migrate
```

## Docker compose

```bash
docker compose up --build
```

This starts Postgres, applies migrations, then starts the API and web app.
The compose file contains development-only defaults for `SECRET_KEY`,
`ENCRYPTION_KEY`, and the Postgres password. Override them through a root
`.env` file or your shell for anything beyond local use, and set
`COOKIE_SECURE=true` once the stack is behind HTTPS.

The stack listens on:

- web: `http://localhost:3000`
- API: `http://localhost:8000` (`/health`, `/ready`)
- Postgres: `127.0.0.1:5432`

If those host ports are taken, set `FRONTEND_PORT`, `BACKEND_PORT`, or
`POSTGRES_PORT`. When the API port changes, rebuild the frontend image with
the matching `NEXT_PUBLIC_API_BASE_URL`, because the URL is baked into the
client bundle at build time.

The API image runs uvicorn with `--no-access-log`; the request middleware
emits one JSON log line per request with a request ID, method, path, status,
and duration, and no bodies or headers.

## Sibling subdomains locally

`lvh.me` resolves to `127.0.0.1`, so a two-host setup needs no hosts-file edit:

```bash
# Backend
ALLOWED_ORIGINS=http://app.lvh.me:3000 \
COOKIE_DOMAIN=.lvh.me \
COOKIE_SECURE=false \
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```bash
# Frontend
NEXT_PUBLIC_API_BASE_URL=http://api.lvh.me:8000/api \
NEXT_ALLOWED_DEV_ORIGINS=app.lvh.me \
npm run dev
```

Then browse `http://app.lvh.me:3000`. The API sets `access_token` and
`csrf_token` with `Domain=.lvh.me`, so the browser sends them to both
`app.lvh.me` and `api.lvh.me`. `SameSite=Lax` is sufficient because both
hosts share the registrable domain.

For Docker compose, the same values work if you map the ports and browse
`http://app.lvh.me:3000` with the API at `http://api.lvh.me:8000`.

## Supabase pooler

Supabase's transaction pooler (port `6543`) does not keep server-side prepared
statements between transactions. The API detects `pooler.supabase.com` and
`:6543` URLs and disables asyncpg's statement cache automatically. For other
PgBouncer deployments set `DB_DISABLE_PREPARED_STATEMENTS=true` or use the
session pooler (port `5432`).

## Tests

```bash
cd backend
.venv/Scripts/python.exe -m pytest    # Windows
.venv/bin/python -m pytest            # macOS/Linux

cd frontend
npm test
npm run lint
npm run build
```
