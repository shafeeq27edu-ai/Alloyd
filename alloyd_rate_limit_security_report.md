# Alloyd Rate Limiting Security Report

## 1. Chosen Architecture
Implemented an `InMemoryRateLimiter` utilizing `fastapi` dependencies and `asyncio.Lock()`.
- **Reasoning**: Satisfies the V1 simple requirements and avoids introducing a Redis dependency.
- **Algorithm**: Fixed sliding-window using in-memory timestamps per key.

## 2. Limits and Keys
### LOGIN
- **Limit**: 5 requests
- **Window**: 60 seconds
- **Key**: `login:{IP}:{Email}`
- **Reasoning**: Protects an account from brute-force while ensuring one IP doesn't lock out other legitimate users attempting to log in.

### REGISTRATION
- **Limit**: 3 requests
- **Window**: 3600 seconds (1 hour)
- **Key**: `register:{IP}`
- **Reasoning**: Throttles automated mass account creation from a single source.

### CHAT
- **Limit**: 15 requests
- **Window**: 60 seconds
- **Key**: `chat:{UserID}`
- **Reasoning**: Authenticated limit that prevents user-level API abuse and spamming, applied prior to expensive provider requests. 

## 3. Configuration
The limits are configurable via `app.config.settings` (can be overridden via `.env`):
- `LOGIN_RATE_LIMIT` (default: 5)
- `LOGIN_RATE_WINDOW` (default: 60)
- `REGISTRATION_RATE_LIMIT` (default: 3)
- `REGISTRATION_RATE_WINDOW` (default: 3600)
- `CHAT_RATE_LIMIT` (default: 15)
- `CHAT_RATE_WINDOW` (default: 60)

## 4. HTTP and SSE Behavior
- Rate limited requests immediately receive an `HTTP 429 Too Many Requests` response.
- A `Retry-After` header is included with the estimated wait time in seconds.
- **Provider Protection**: For chat requests, the 429 is returned *before* the SSE `StreamingResponse` begins, and *before* the provider is invoked, preventing resource drain.

## 5. Failure Behavior & Limitations
- **Process Restart**: Memory is cleared, resetting all limits.
- **Multiple Workers**: With Uvicorn/Gunicorn running multiple workers, each worker maintains its own memory space. Limits will effectively multiply by the number of workers.
- **Multiple Instances**: Horizontal scaling will similarly multiply limits unless a shared store like Redis is introduced. The current abstraction (`check_rate_limit`) is easily replaceable for a shared backend in the future.

## 6. Testing & Regression
- **Tests**: Added `tests/test_rate_limit.py` verifying all constraints, correct 429 responses, isolation, and headers.
- **Regression**: `pytest` passed, validating existing CSRF and chat tests.
- **Frontend**: Linting and building passed without regressions. 

## 7. Files Changed
- `backend/app/core/rate_limit.py` (added)
- `backend/app/config.py` (updated)
- `backend/app/api/auth.py` (updated)
- `backend/app/api/chat.py` (updated)
- `backend/tests/test_rate_limit.py` (added)

## 8. Final Status
🟢 RATE LIMITING COMPLETE
