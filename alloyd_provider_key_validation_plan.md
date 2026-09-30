# Alloyd Provider Key Validation Plan

## 1. Current Key Lifecycle
1. Frontend (`src/app/settings/page.tsx`) submits `provider_name` and `key` via a POST request to `/api/keys`.
2. Backend (`app/api/keys.py`) receives the request in `add_provider_key`.
3. It immediately encrypts the key using `app.core.encryption.encrypt_key`.
4. It persists the encrypted key (or updates the existing one) to the Supabase PostgreSQL database using SQLAlchemy.
5. It returns a success message to the frontend.
**There is currently zero validation of the key before encryption and persistence.**

## 2. Current Implementation Files
- Frontend UI: `frontend/src/app/settings/page.tsx`
- API Endpoint: `backend/app/api/keys.py` (`add_provider_key`)
- Provider Adapters: `backend/app/providers/*.py` (`groq_adapter.py`, `gemini_adapter.py`, `anthropic_adapter.py`)
- Error Mapping: `backend/app/core/errors.py`
- Database Models: `backend/app/db/models.py` (`ProviderKey`)

## 3. Provider Validation Strategy

We will introduce an `async def validate_key(self, api_key: str) -> None:` method to `BaseProviderAdapter` and implement it in each provider.

| Provider | Validation Call | Expected Cost | Failure Mapping | Expected Success |
|----------|-----------------|---------------|-----------------|------------------|
| Groq | `client.models.list()` | $0 (Metadata) | `groq.AuthenticationError` → `INVALID_API_KEY` | Returns list of models silently |
| Anthropic | `client.models.list()` | $0 (Metadata) | `AuthenticationError` → `INVALID_API_KEY` | Returns list of models silently |
| Gemini | `client.aio.models.get(name='models/gemini-1.5-flash')` (or list) | $0 (Metadata) | `APIError` 403 / `API_KEY_INVALID` → `INVALID_API_KEY` | Returns model info silently |

*Each provider will use its existing `_map_error()` abstraction to catch SDK-specific errors and raise a normalized `ProviderError`.*

## 4. Safe Save Flow
**Current flow:** Encrypt → Store.
**Proposed flow:** Validate → Encrypt → Store.

By performing the lightweight API request *first*, an invalid key will raise an exception and immediately short-circuit the request. The database is never updated with an invalid key, preventing bad state.

## 5. Safe Replacement Flow
Because validation occurs *before* database interaction, an existing, valid credential will remain safely untouched in the database if a user attempts to replace it with a newly provided, invalid credential. The database transaction will only initiate and commit if the new key passes the live validation check.

## 6. Error Handling
When `adapter.validate_key()` raises a `ProviderError`, `keys.py` will catch it and map it to a user-facing HTTP response:
- `ErrorCode.INVALID_API_KEY`: 400 Bad Request, message: "Invalid API key. Check the key and try again."
- `ErrorCode.RATE_LIMIT`: 429 Too Many Requests, message: "Provider rate limit reached. Try again later."
- `ErrorCode.PROVIDER_UNAVAILABLE` / `ErrorCode.TIMEOUT`: 502 Bad Gateway / 504 Gateway Timeout, message: "Provider is temporarily unavailable. Could not verify the key right now."

*Transient provider outages will NOT be falsely reported as an invalid key to the user.*

## 7. API Contract
The existing `POST /api/keys` response contract will remain largely the same for success.
For failures, it will return a standard FastAPI `HTTPException` format:
```json
{
  "detail": "Invalid API key. Check the key and try again."
}
```
Raw provider errors, stack traces, and API keys will be strictly excluded from the response payload.

## 8. Frontend UX
The settings UI (`settings/page.tsx`) already uses a toast notification system.
We will update it to map the specific HTTP error statuses from the backend:
- 400: `addToast("Invalid API key. Check the key and try again.", "error")`
- 429: `addToast("Provider rate limit reached. Try again later.", "error")`
- 500/502/504: `addToast("Could not verify the key right now.", "error")`
- 200/201: `addToast("Key saved successfully", "success")`

## 9. Database / Transaction Behavior
No database schema changes are required. The SQLAlchemy transaction (`await db.commit()`) will only trigger after `validate_key` has successfully returned. This ensures atomic isolation where the database state is never dirtied by an invalid key. Concurrency is handled naturally because we update the key in place without intermediate deletions.

## 10. Security Considerations
- **No logging:** Provider validation errors must be caught and normalized without logging the raw input key.
- **Exceptions:** `ProviderError` does not attach the raw API key to its payload.
- **Database:** Only the ciphertext from `encrypt_key` is persisted.
- **Rate limiting interaction:** Key validation is synchronous and bounded to explicit user interaction on the settings page. It will inherently benefit from the existing generic API rate limiting applied to the `/api/keys` endpoint, preventing abuse. 

## 11. Test Plan
- **Mocking:** Provider validation methods in `MockAdapter` will be updated to echo success/failure based on the mock key (e.g., `"invalid"`, `"timeout"`).
- **Security Check:** Ensure exceptions during validation do not leak the key into `pytest` output or logs.
- **Replacement Test:** 
  1. Store a valid key.
  2. Attempt to add an invalid key. Assert 400 response.
  3. Query the database to ensure the original valid key remains.
- **Success Test:** Store a valid key and ensure it fully persists.

## 12. Files Expected to Change
- `backend/app/providers/base.py` (Add abstract `validate_key`)
- `backend/app/providers/groq_adapter.py`
- `backend/app/providers/gemini_adapter.py`
- `backend/app/providers/anthropic_adapter.py`
- `backend/app/api/keys.py` (Execute validation in `add_provider_key`)
- `frontend/src/app/settings/page.tsx` (Handle specific error statuses)
- `backend/tests/test_keys.py` (Add replacement & validation test coverage)
- `backend/tests/conftest.py` (Update `MockAdapter` with `validate_key`)

## 13. P0 / P1 / P2
- **P0**: Implementing synchronous `validate_key` via metadata endpoints across all 3 providers.
- **P0**: Safe Save / Safe Replacement flow in `keys.py`.
- **P1**: Accurate UX error mapping on the frontend.
- **P2**: Additional database transaction hardening if concurrency edge cases arise (not currently expected).

## 14. Risks and Compatibility Concerns
- **SDK Drift:** If Anthropic or Groq changes their SDK's `models.list()` behavior, the validation might falsely flag valid keys. We rely on standard metadata endpoints to minimize this risk.
- **Local Dev:** Automated tests must rely on `MockAdapter` to prevent breaking developers without active provider subscriptions.

## 15. Implementation Order
1. Define abstract `validate_key` in `BaseProviderAdapter`.
2. Implement `validate_key` in `MockAdapter`, `GroqAdapter`, `GeminiAdapter`, and `AnthropicAdapter`.
3. Update `add_provider_key` in `keys.py` to call `validate_key` before encryption.
4. Update frontend `settings/page.tsx` to handle the new specific API error responses.
5. Update `test_keys.py` to assert correct replacement and error behavior.

## 16. V1 Scope Check
- We are NOT implementing asynchronous Celery validation tasks.
- We are NOT implementing ongoing background key health polling.
- We are NOT implementing rate limiting per-provider key.
- We are NOT changing the underlying database schema.
