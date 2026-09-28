# Alloyd CSRF Security Plan

## 1. Current Authentication Flow
- Authentication is handled via JWTs (`access_token`).
- Upon successful `/register` or `/token` (login), the backend generates a JWT and sets it in an HTTP-only cookie (`access_token`).
- Protected endpoints use the `get_current_user` dependency, which reads the `access_token` from the cookie (with a fallback to the `Authorization` header).
- The frontend `fetchWithAuth` utility automatically includes `credentials: "include"` to send cookies with every request.

## 2. Current Cookie Settings
- `httponly=True` (Prevents XSS from stealing the token).
- `secure=False` (Noted to be changed to True in production).
- `samesite="lax"` (Provides baseline CSRF protection in modern browsers).
- `max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60`.

## 3. Current CORS Settings
- Hardcoded to `allow_origins=["http://localhost:3000"]`.
- `allow_credentials=True`.
- `allow_methods=["*"]`, `allow_headers=["*"]`.

## 4. State-changing endpoints
The following authenticated endpoints modify state and require CSRF protection:
- `POST /api/chat/` (Creates conversation, saves messages, streams response).
- `POST /api/keys/` (Stores a provider key).
- `DELETE /api/keys/{provider_name}` (Deletes a provider key).
- `DELETE /api/conversations/{conversation_id}` (Deletes a conversation).
- `POST /api/auth/logout` (Deletes the session cookie).

## 5. CSRF Attack Surface
Since authentication relies on cookies that the browser automatically attaches to cross-origin requests (if SameSite allows), a malicious site could forge a POST/DELETE request (e.g., via a hidden form or fetch) to `http://localhost:8000/api/keys/` or `/api/chat/`. If the browser sends the `access_token` cookie, the backend would process the state-changing request as the authenticated user. While `samesite="lax"` prevents cross-site POSTs by default, relying solely on this is insufficient for defense in depth (e.g., older browsers, or scenarios where SameSite is weakened).

## 6. Proposed CSRF Strategy
**Defense in Depth: Double-Submit Cookie (HttpOnly) + Origin Validation**
1. **CSRF Token Generation:** 
   - We will introduce a new endpoint: `GET /api/auth/csrf`.
   - This endpoint will generate a cryptographically secure random token.
   - It will return the token in the JSON response body AND set a hashed/signed version of it in a new, separate **HttpOnly** cookie (`csrf_token`).
2. **Frontend Handling:**
   - The frontend's `fetchWithAuth` will lazily fetch the CSRF token before any state-changing request (POST, PUT, PATCH, DELETE) and store it in a module-level variable (memory only, not localStorage).
   - The token will be attached to the `X-CSRF-Token` HTTP header on these requests.
3. **Backend Validation:**
   - A new FastAPI dependency (`verify_csrf`) will be added to state-changing endpoints.
   - It will ensure the `X-CSRF-Token` header matches the value expected by the HttpOnly `csrf_token` cookie.
4. **Origin Validation (Extra Defense):**
   - The backend will strictly validate that the `Origin` or `Referer` headers match the configured CORS origins.

## 7. Why the strategy fits Alloyd
- The JWT cookie remains HttpOnly, preserving XSS protection for the primary credential.
- The CSRF token is independent of the authentication token.
- No new secrets are exposed in local/session storage (token lives in memory).
- It remains stateless on the backend (FastAPI does not need to store CSRF tokens in the DB or memory).
- It easily supports SSE (streaming) because the SSE endpoint is a standard `POST` request using `fetch`, allowing custom headers (`X-CSRF-Token`) to be attached.

## 8. Frontend changes required
- Modify `frontend/src/lib/api.ts` to maintain a local `csrfToken` variable.
- For `POST, PUT, PATCH, DELETE` methods, check if `csrfToken` exists. If not, fetch it from `GET /api/auth/csrf`.
- Append the `X-CSRF-Token: <token>` header to the outgoing fetch request.
- On 403 CSRF errors, clear the token and optionally retry.

## 9. Backend changes required
- Add `ALLOWED_ORIGINS` to `app/config.py` (read from environment, default to localhost).
- Create `GET /api/auth/csrf` to set the cookie and return the token.
- Create `verify_csrf` dependency in `app/api/deps.py` that:
  - Validates the Origin header.
  - Compares the `X-CSRF-Token` header to the `csrf_token` cookie.
- Apply `Depends(verify_csrf)` to `POST /api/chat/`, `POST /api/keys/`, `DELETE /api/keys/{name}`, `DELETE /api/conversations/{id}`, and `POST /api/auth/logout`.
- Ensure Explicit `SameSite=Lax` and configurable `secure` flag are maintained for all cookies.

## 10. Test strategy
- Update `test_auth.py`, `test_keys.py`, etc.
- Add test for `GET /api/auth/csrf`.
- Attempt a state-changing request without the `X-CSRF-Token` header -> expect 403.
- Attempt with an invalid token -> expect 403.
- Attempt with a missing or incorrect `Origin` header -> expect 403.
- Attempt with valid token and valid origin -> expect success.
- Ensure `GET /api/conversations/` does not require CSRF token.

## 11. SSE implications
- Since Alloyd's SSE implementation uses `POST /api/chat/` (and the frontend presumably uses `@microsoft/fetch-event-source` or standard `fetch` to read the stream), the frontend can easily attach custom headers (unlike native `EventSource` which only supports GET and no custom headers). 
- Thus, the CSRF token header will be sent correctly, and the backend CSRF dependency will run before the stream generator executes.

## 12. Compatibility concerns
- The Next.js frontend and FastAPI backend must agree on CORS and Cookie configurations for this to work cross-origin in development (`localhost:3000` vs `localhost:8000`).
- The `csrf_token` cookie must have the same `SameSite` and `secure` configurations as the `access_token` cookie.
