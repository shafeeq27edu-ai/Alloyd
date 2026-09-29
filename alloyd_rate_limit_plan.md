# Alloyd Rate Limit Plan

## 1. Existing Architecture
- **Framework**: FastAPI backend with Next.js frontend.
- **Database**: PostgreSQL (Supabase) via SQLAlchemy.
- **Authentication**: JWT cookies (HttpOnly), CSRF tokens.
- **Endpoints of Interest**:
  - `POST /api/auth/register` (Unauthenticated)
  - `POST /api/auth/token` (Login, Unauthenticated)
  - `POST /api/chat/` (Authenticated via `get_current_user`, streaming SSE)
- **Infrastructure**: No current Redis or Memcached configuration is present in `main.py` or `config.py`.

## 2. Threat Model
- **Login**: Protect against password brute forcing, credential stuffing, and repeated invalid authentication attempts.
- **Registration**: Protect against automated account creation and registration flooding.
- **Chat**: Protect against automated message spam, accidental rapid-fire submissions, and API/provider abuse (excessive concurrent generations).

## 3. Rate Limiting Architecture Choice
**Chosen Architecture**: In-memory application process limiter using a custom lightweight FastAPI dependency utilizing an in-memory dictionary tracking timestamps.
**Why**: Redis is not currently part of the active V1 runtime architecture. Introducing Redis solely for rate limiting violates the "simplest reliable solution" directive and complicates the local development and deployment model.
**Known Limitation**: An in-memory limiter is local to the backend process. If Alloyd is horizontally scaled to multiple backend instances without sticky sessions or a centralized cache, the rate limits will apply per instance, effectively multiplying the allowed limit by the number of instances. It also resets on server restart.

## 4. Limits and Keys
- **Login**:
  - **Limit**: 5 requests per 1 minute.
  - **Key**: Client IP Address + Email Address (to prevent targeted account lockouts while stopping brute force on a single account). If IP-only, one user could lock out others.
- **Registration**:
  - **Limit**: 3 requests per 1 hour.
  - **Key**: Client IP Address.
- **Chat**:
  - **Limit**: 15 requests per 1 minute (to allow normal conversation but stop runaway loops or scripts).
  - **Key**: Authenticated User ID (since this is an authenticated endpoint).

## 5. HTTP Behavior
- Rejected requests will return HTTP status `429 Too Many Requests`.
- The response will include a `Retry-After` header if possible.
- For chat, the 429 response will be returned *before* the SSE stream (`StreamingResponse`) is initiated and *before* any provider API calls are made.

## 6. Configuration
The following variables will be added to `config.py` with safe defaults:
- `LOGIN_RATE_LIMIT`: "5"
- `LOGIN_RATE_WINDOW`: "60"
- `REGISTRATION_RATE_LIMIT`: "3"
- `REGISTRATION_RATE_WINDOW`: "3600"
- `CHAT_RATE_LIMIT`: "15"
- `CHAT_RATE_WINDOW`: "60"

## 7. Implementation Steps
1. Add a rate-limiting mechanism (a custom sliding-window or token-bucket in-memory dict is straightforward and avoids adding extra dependencies).
2. Integrate the limiter into `auth.py` for `/register` and `/token`.
3. Integrate the limiter into `chat.py` for `/chat/`.
4. Add configuration settings to `config.py`.
5. Update tests to verify rate limiting behaves as expected (HTTP 429, headers, etc.).
6. Generate final report `alloyd_rate_limit_security_report.md`.
