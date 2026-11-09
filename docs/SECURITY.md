# Alloyd Security Model

Status: Phase 3 complete (2026-11-09). This documents what is protected, how, and what is explicitly not.

## Assets

- Provider API keys supplied by users (BYOK).
- User credentials and session tokens.
- Conversation content.
- Server secrets: `SECRET_KEY`, `ENCRYPTION_KEY`, `PREVIOUS_ENCRYPTION_KEY`, `DATABASE_URL`.

## Controls

### Authentication and sessions

- Passwords are bcrypt-hashed; minimum 12 characters, maximum 72 bytes.
- The JWT (HS256, 7-day expiry) lives only in an HttpOnly, `SameSite=Lax` cookie and is never returned in a response body. `Secure` is set unless `DEBUG=true`.
- Every state-changing endpoint requires a double-submit CSRF token (`csrf_token` cookie plus `X-CSRF-Token` header) and an `Origin`/`Referer` from the CORS allowlist. This includes login, register, logout, key changes, chat, and conversation deletion.
- Login is rate limited per IP and email; registration per IP.

### Authorization

- Every key, conversation, and message query filters on the authenticated `user_id`. Missing or foreign resources return 404, not 403, to avoid confirming existence.
- User identity comes only from the verified JWT; IDs from request bodies are never trusted.

### Provider keys

- Keys are validated against the provider from the backend, then encrypted with Fernet/MultiFernet before storage.
- The API returns only a masked hint; plaintext keys are decrypted in memory only for outbound provider calls and are never logged.
- Rotation is manual: `PREVIOUS_ENCRYPTION_KEY` decrypts old rows, `backend/scripts/rotate_keys.py` re-encrypts them with the active key. An end-to-end test covers this.

### Provider calls and errors

- Explicit SDK timeouts plus a first-chunk timeout on streams.
- Errors are normalized to `ProviderError`; callers receive safe messages, never stack traces or raw provider payloads.
- Auto mode falls back only on retryable errors and `MODEL_UNAVAILABLE`. Manual mode never falls back. `INVALID_API_KEY` and `BAD_REQUEST` never trigger fallback.

### Transport and browser headers

- CORS is an explicit allowlist with credentials enabled.
- Backend responses set `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, and HSTS when `DEBUG=false`.
- The Next.js layer sets CSP (`default-src 'self'`, `frame-ancestors 'none'`, `object-src 'none'`, `form-action 'self'`) and `Permissions-Policy`. Production drops `unsafe-eval`; `connect-src` is `'self'` plus the origin of `NEXT_PUBLIC_API_BASE_URL` at build time.

### Input and resource limits

- Bodies above `MAX_REQUEST_BYTES` (default 1 MB) are rejected with 413.
- Chat messages are 1–20,000 characters; provider names ≤32, model IDs ≤64, conversation IDs ≤64, provider keys ≤512.
- Login, registration, and chat have per-IP rate limits.

### Proxy trust

- `X-Forwarded-For` is honored only when the direct socket peer matches `TRUSTED_PROXIES` (comma-separated IPs/CIDRs, default empty). Otherwise the peer address is used.
- Without a configured proxy, a spoofed `X-Forwarded-For` cannot escape rate limiting.

### Logging

- Logs never contain provider keys, message content, DSNs, or ciphertext.
- `rotate_keys.py` prints counts and row IDs only; database connection failures print the exception class only.

## Known limitations

- Rate limiting is in-memory and per process. Multiple workers need a shared store (Phase 4+).
- No MFA, email verification, password reset, or account lockout beyond rate limits.
- Conversation content is stored in plaintext in Postgres; database access control is the boundary.
- CSP keeps `unsafe-inline` because Next.js uses inline bootstrap scripts. A nonce/hash policy is not implemented.
- `DEBUG=true` disables `Secure` cookies and HSTS. It must be false outside local HTTP development.
- Key rotation is a manual, operator-run script with a maintenance window.
- There is no audit trail for provider-key access.
- Key validation necessarily sends the supplied key to the provider.
- `gitleaks` is not installed; Phase 6 adds it to CI. Current scans are pattern-based and print paths only.

## Verification

Run these from the repository root. All scans use `-l` so a potential secret is never echoed to the terminal.

```bash
# High-confidence credential patterns in the tracked tree
git grep -lE 'sk-[A-Za-z0-9]{20,}|gsk_[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_-]{30,}|eyJ[A-Za-z0-9_-]{20,}\.' -- . ':!frontend/package-lock.json' ':!backend/venv'

# Same patterns across all history (prints commit:path)
for c in $(git rev-list --all); do
  git grep -lE 'sk-[A-Za-z0-9]{20,}|gsk_[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_-]{30,}|eyJ[A-Za-z0-9_-]{20,}\.' "$c" -- . ':!frontend/package-lock.json' ':!backend/venv' 2>/dev/null
done | sort -u

# Test suite
cd backend && ./.venv/Scripts/python.exe -m pytest -q
```

Expected tree hits are limited to documented placeholder DSNs in `.env.example` and `tests/test_config.py`; history should be empty.

### Verification record (2026-11-09)

- Secret scan of the tracked tree and of every commit in `git rev-list --all`: 0 hits.
- Backend suite: 103 passed. The captured pytest log contains 0 credential-pattern hits and 0 DSN-shaped strings.
- Cookie flags observed on a live login over plain HTTP with `DEBUG` off: `access_token` = `HttpOnly; Secure; SameSite=lax; Path=/; Max-Age=604800`; the response body contains no token. `csrf_token` = `HttpOnly; Path=/; SameSite=lax; Secure`.
- Headers observed live: backend sends `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, and HSTS; Next.js sends the CSP (dev keeps `unsafe-eval`, the production build drops it) and `Permissions-Policy`.
- CSRF and origin on `POST /api/auth/logout`: valid token with `Origin: https://evil.example` → 403; missing token → 403; valid token with an allowed origin → 200.
- Real providers, exercised through the running app so stored keys are never exposed: Groq `openai/gpt-oss-120b` and `openai/gpt-oss-20b` in Manual mode, and Auto routing, each streamed a `done` event and replied exactly `OK`; the reply was stored once. Gemini and Anthropic: NOT RUN (no keys configured).

Known limitations not covered by the record above remain as listed.

## Production checklist

- `DEBUG=false`, strong `SECRET_KEY` and valid `ENCRYPTION_KEY` (startup refuses otherwise).
- `TRUSTED_PROXIES` set to the actual ingress proxy, not left open.
- `ALLOWED_ORIGINS` lists the exact frontend origin(s).
- `NEXT_PUBLIC_API_BASE_URL` set at build time so CSP `connect-src` includes the API origin.
- HTTPS terminated at the proxy; HSTS enabled.
