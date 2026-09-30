# Alloyd Security Headers + Password Policy Report

## 1. Changes Implemented
Successfully implemented the planned security hardening. The backend now strictly enforces password lengths natively using byte limits to respect bcrypt boundaries. API responses and frontend pages now correctly include a defense-in-depth layer of standard security headers.

## 2. Password Policy
- **Minimum:** 12 characters (enforced via Pydantic validator on `UserCreate` schema).
- **Maximum byte length:** 72 UTF-8 bytes (enforced strictly to align with bcrypt's underlying truncation limit, preventing long password DOS vulnerabilities and truncation collisions).
- **Hashing behavior:** Remains exactly the same. We continue to use the secure `bcrypt` library directly. Passwords are never logged or returned in API responses.
- **Frontend validation:** Updated `login/page.tsx` to require 12 characters, mirroring the backend policy for smooth UX.

## 3. Security Headers

| Header | Configuration | Purpose |
|--------|---------------|---------|
| X-Content-Type-Options | `nosniff` | Prevents MIME-sniffing attacks on all responses. |
| X-Frame-Options | `DENY` | Explicitly blocks the application from being embedded in iframes to prevent clickjacking. |
| Referrer-Policy | `strict-origin-when-cross-origin` | Minimizes URL leakage while preserving origin context. |
| Strict-Transport-Security | `max-age=31536000; includeSubDomains` | Forces HTTPS in production only. |
| Content-Security-Policy | Next.js specific | Mitigates XSS and restricts resource loading. |
| Permissions-Policy | `camera=(), microphone=(), geolocation=()` | Blocks abuse of sensitive browser features. |

## 4. CSP
The CSP is injected via `next.config.ts`:
- **script sources:** `'self' 'unsafe-inline' 'unsafe-eval'` (Needed for Next.js app router hydration during V1 without complex strict nonces).
- **style sources:** `'self' 'unsafe-inline'` (Needed for Tailwind and Next.js built-in CSS).
- **image sources:** `'self' data:` (Allows internal images and simple SVGs).
- **font sources:** `'self'` (Geist font is loaded directly from Next.js).
- **connect sources:** `'self' http://localhost:8000 ${process.env.NEXT_PUBLIC_API_BASE_URL}`. This permits normal Fetch requests and SSE streaming, while remaining environment-aware for local dev and production.
- **SSE compatibility:** Supported explicitly through the `connect-src` backend origin allowance.
- **development vs production:** The API URL is dynamic, ensuring local dev uses `localhost:8000` while production utilizes `NEXT_PUBLIC_API_BASE_URL`.

## 5. HSTS
HSTS is applied on both the FastAPI backend and Next.js frontend, but is **environment-aware**. It only emits the header `Strict-Transport-Security: max-age=31536000; includeSubDomains` when `DEBUG=False` (backend) or `NODE_ENV='production'` (frontend). Preloading was intentionally omitted for V1 to prevent irrevocable lock-in.

## 6. Permissions Policy
A minimal `Permissions-Policy` header was added to the Next.js config:
`camera=(), microphone=(), geolocation=()`
Since Alloyd uses none of these, they are safely explicitly denied.

## 7. Tests
All tests passed successfully.
- Pytest run: `46 passed, 1 warning in 28.11s`
- NPM Build: `Compiled successfully in 20.7s`
- NPM Lint: `0 errors`

Explicit tests were added to `test_auth.py` and successfully validated:
- 11-character password → rejected (422)
- 12-character password → accepted (200)
- >12-character password → accepted (200)
- Exceeding 72 UTF-8 bytes (via 73 ASCII chars) → rejected (422)
- Exceeding 72 UTF-8 bytes (via multibyte emojis near boundary) → rejected (422)

## 8. Manual QA
The following was verified based on the automated test suite execution and logical checks:
1. Registration with >= 12 chars succeeds.
2. Registration with < 12 chars or > 72 bytes fails cleanly.
3. Login works successfully (verified via tests).
4. Authenticated requests succeed (verified via tests).
5. All legacy test fixtures were migrated from `"password"` to `"test-password-123"` and still work.

## 9. Security Verification
- No secrets were added or hardcoded.
- No tokens were moved to `localStorage` (JWT architecture remains untouched).
- No passwords are logged.
- No wildcard CORS or wildcard CSP domains were introduced unnecessarily (limited to `self` or explicit API URLs).
- Existing CSRF implementations and dependencies remain untouched.

## 10. Files Changed
- `backend/app/api/auth.py`
- `backend/app/main.py`
- `backend/tests/conftest.py`
- `backend/tests/test_auth.py`
- `backend/tests/test_rate_limit.py`
- `frontend/next.config.ts`
- `frontend/src/app/login/page.tsx`

## 11. Known Limitations
- The Next.js CSP relies on `'unsafe-inline'` for scripts and styles to maintain a simple V1 architecture. Removing this would require a complex nonce-generation pipeline.
- Existing users with passwords under 12 characters are implicitly grandfathered in for login, as validation only occurs on registration.

## 12. Scope Check
Unrelated V2 work (e.g., password reset, 2FA, new databases, dependency upgrades) was explicitly NOT added. The changes were kept exclusively to the narrow security hardening requested.

## 13. Final Status

PASS
