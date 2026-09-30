# Alloyd Security Headers + Password Policy Plan

## 1. Current Implementation
- **Security Headers**: Neither the FastAPI backend nor the Next.js frontend currently implements HTTP security headers (e.g., CSP, HSTS, X-Frame-Options). The `next.config.ts` is empty, and `main.py` only configures CORS.
- **Password Policy**:
  - The frontend enforces a minimum password length of 6 characters in `login/page.tsx`.
  - The backend (`api/auth.py`) does **not** enforce any password length or complexity rules during registration.
  - Passwords are not normalized before hashing.
- **Password Hashing**: The backend uses the modern `bcrypt` library (v4.1.2) directly via `bcrypt.hashpw()` and `bcrypt.checkpw()`. `passlib` is completely avoided, which is excellent given its unmaintained status.
- **Authentication**: JWTs are stored in HttpOnly cookies with `samesite="lax"` and `secure=not settings.DEBUG`. CSRF protection is implemented.

## 2. Security Header Audit

| Header | Current State | Risk | Recommendation |
|--------|---------------|------|----------------|
| Content-Security-Policy (CSP) | Missing | XSS / Data exfiltration | Add to frontend. Restrict to 'self' with specific allowances for Next.js hydration and SSE connections. |
| Strict-Transport-Security (HSTS) | Missing | HTTPS downgrade attacks | Add to backend and frontend (production only) with max-age=31536000. No preload for V1. |
| X-Content-Type-Options | Missing | MIME-type confusion | Add `nosniff` to all backend and frontend responses. |
| Referrer-Policy | Missing | URL/Referrer leakage | Add `strict-origin-when-cross-origin` to all responses. |
| Permissions-Policy | Missing | Abuse of browser features | Add restricting camera, microphone, geolocation, etc., to `()`. |
| X-Frame-Options | Missing | Clickjacking | Add `DENY` to prevent embedding in iframes. |

## 3. CSP Analysis
Alloyd is a Next.js application that streams chat via Server-Sent Events (SSE) and uses the Geist font from `next/font/google`. 
Proposed V1 CSP strategy (via Next.js `next.config.ts` headers):
- `default-src 'self';`
- `script-src 'self' 'unsafe-inline' 'unsafe-eval';` (Required for Next.js dev/hydration in V1 without complex strict nonce setup)
- `style-src 'self' 'unsafe-inline';` (Required for Next.js built-in CSS/Tailwind)
- `img-src 'self' data:;` (Allows inline SVGs like the Next.js logo if needed)
- `font-src 'self';` (Geist is self-hosted by `next/font`)
- `connect-src 'self' http://localhost:8000;` (Needs explicit backend URL allowance for SSE and fetch, tailored per environment)
- `frame-ancestors 'none';` (Prevents clickjacking)
- `base-uri 'self';`
- `object-src 'none';`

This provides a strong defense-in-depth layer against XSS while keeping V1 implementation simple and avoiding Next.js nonce overhead.

## 4. HSTS Analysis
- **Development**: HSTS must remain disabled locally (when `DEBUG=True` or `NODE_ENV=development`) to prevent browsers from locking `localhost` to HTTPS, which would break the local dev environment.
- **Production**: Should be enabled with `max-age=31536000; includeSubDomains`. The `preload` directive should be omitted because Alloyd does not need to be hardcoded into browser HSTS preload lists for V1, and doing so makes it very difficult to revert if there is an infrastructure mistake.

## 5. Password Policy Audit
- **Current Validation**: Frontend checks for length >= 6. Backend blindly accepts any string length (including empty strings if the frontend is bypassed).
- **Hashing**: The backend securely hashes passwords using `bcrypt` and salt generation. Passwords do not appear in logs or error messages.
- **Normalization**: Passwords are not trimmed or normalized, meaning leading/trailing spaces are hashed as part of the password.
- **Compatibility**: Bcrypt natively truncates inputs longer than 72 bytes. This isn't currently checked, meaning a 100-character password and its first 72 characters would evaluate equally.

## 6. Recommended Password Policy
- **Minimum Length**: 12 characters (enforced strongly on the backend, mirrored on the frontend).
- **Maximum Length**: 72 characters (to prevent arbitrary length bcrypt hashing DOS and align with bcrypt's 72-byte truncation limit).
- **Allowed Characters**: All characters allowed. No forced complexity (uppercase/lowercase/numbers) as length is a better security control and matches modern NIST guidelines.
- **Normalization**: Do not trim spaces; treat all characters as valid password input, but ensure the backend validates the raw byte length.
- **Hashing Approach**: Continue using the current `bcrypt` direct implementation. No changes needed to the library.

## 7. Authentication Compatibility
- **Cookies**: The security headers do not interfere with the existing HttpOnly, SameSite=Lax, and Secure cookie settings.
- **CSRF & CORS**: The proposed CSP `connect-src` must mirror the allowed CORS origins and API base URLs so that CSRF tokens and fetch requests are not blocked by the browser.
- **JWT**: JWTs remain securely stored in cookies. No tokens are exposed to JavaScript, aligning with the new CSP.

## 8. Test Plan
- **Security Headers**:
  - Write a test in `test_auth.py` or a new `test_security.py` to assert that `X-Content-Type-Options`, `X-Frame-Options`, and `Referrer-Policy` are present in API responses.
  - Assert that HSTS is omitted when `DEBUG=True`.
- **Password Policy**:
  - Add backend tests in `test_auth.py`:
    - Registration with 11-character password → 422/400 rejected.
    - Registration with 12-character password → accepted.
    - Registration with 73-character password → 422/400 rejected.
- **Authentication Regression**:
  - Run existing test suite to ensure login, registration, and logout flows still pass with the new password requirements.

## 9. Files Expected to Change
- `frontend/next.config.ts`: To inject HTTP security headers (CSP, HSTS, X-Frame-Options, Permissions-Policy, Referrer-Policy, X-Content-Type-Options) for frontend routes.
- `frontend/src/app/login/page.tsx`: To update the frontend validation to require 12 characters and show appropriate error messages.
- `backend/app/main.py`: To add a simple middleware or Starlette `SecureHeaders` equivalent for applying headers to API responses.
- `backend/app/api/auth.py` & `backend/app/db/models.py` (or Pydantic schemas): To enforce `min_length=12` and `max_length=72` on the `UserCreate` schema.
- `backend/tests/test_auth.py` & `backend/tests/conftest.py`: To add the new password boundary tests and update test fixtures to use 12+ char passwords.

## 10. Risk / Compatibility Notes
- **CSP Breakage**: If `connect-src` is misconfigured, SSE chat streaming will fail silently in the browser. It must dynamically match `API_BASE_URL`.
- **User Disruption**: Any existing users with passwords under 12 characters will still be able to log in (because login doesn't validate constraints, only registration does).

## 11. Implementation Order
1. Update backend Pydantic schemas to enforce password length rules.
2. Update backend test fixtures (`conftest.py` user passwords) to be >= 12 characters.
3. Update backend tests to verify password constraints.
4. Update frontend login component to match the new password constraints.
5. Apply security header middleware to the FastAPI backend.
6. Apply `next.config.ts` security headers to the frontend.

## 12. V1 Scope Check
- **P0**: Backend password length validation (min 12, max 72).
- **P0**: Basic security headers (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`).
- **P1**: Frontend CSP and Permissions-Policy.
- **P1**: HSTS configuration.
- **Out of scope**: Complex CSP nonces, WAF, password complexity rules, forcing password resets for existing users, SSO, WebAuthn.

## 13. Final Recommendation
The audit found that while the cryptographic choices (bcrypt, JWTs, HttpOnly cookies, Fernet) are solid, the application is missing basic transport/browser security headers and backend password length enforcement. Implementing the proposed P0 and P1 changes will close these gaps effectively without over-engineering or breaking the V1 scope.
