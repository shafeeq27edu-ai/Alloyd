# Alloyd Dependency Security Hardening — Report

## Summary

All three P0/P1 dependency replacements from the audit plan have been implemented and verified.

## Changes Made

### 1. `python-jose[cryptography]` → `PyJWT` (P0)

| | Before | After |
|---|---|---|
| **Package** | `python-jose[cryptography]` | `PyJWT` |
| **Import** | `from jose import JWTError, jwt` | `import jwt` |
| **Exception** | `JWTError` | `jwt.InvalidTokenError` |

**Files changed:**
- `requirements.txt` — dependency swap
- `security.py` — `import jwt`
- `deps.py` — `import jwt`, exception class

**Why:** `python-jose` is unmaintained with no security patches. `PyJWT` is the actively maintained standard.

**Verified:** JWT `encode` → `decode` round-trip confirmed. `HS256` algorithm, `sub` claim, `exp` claim all work identically.

---

### 2. `passlib[bcrypt]` → raw `bcrypt` (P0)

| | Before | After |
|---|---|---|
| **Package** | `passlib[bcrypt]` | `bcrypt` |
| **Hash** | `CryptContext(schemes=["bcrypt"]).hash()` | `bcrypt.hashpw()` |
| **Verify** | `CryptContext.verify()` | `bcrypt.checkpw()` |

**Files changed:**
- `requirements.txt` — dependency swap
- `security.py` — direct `bcrypt` usage with `str`/`bytes` handling

**Why:** `passlib` is unmaintained and crashes with `bcrypt>=4.0` on modern Python due to removed `_bcrypt` internals.

**Hash compatibility:** Both `passlib` and raw `bcrypt` produce/consume standard `$2b$` bcrypt hashes. Existing user password hashes in the database will continue to verify correctly. No user lockouts.

**Verified:** Hash round-trip (create + verify) confirmed. Wrong-password rejection confirmed. Existing-hash-format compatibility confirmed.

---

### 3. `google-generativeai` → `google-genai` (P1)

| | Before | After |
|---|---|---|
| **Package** | `google-generativeai` | `google-genai` (v2.25.0) |
| **Import** | `import google.generativeai as genai` | `from google import genai` |
| **Client** | `genai.configure(api_key=...)` | `genai.Client(api_key=...)` |
| **Non-streaming** | `model.generate_content_async()` | `client.aio.models.generate_content()` |
| **Streaming** | `model.generate_content_async(stream=True)` | `client.aio.models.generate_content_stream()` |
| **Message parts** | `"parts": [text]` | `"parts": [{"text": text}]` |
| **Errors** | `google.api_core.exceptions.*` | `google.genai.errors.APIError` (with `.code`) |

**Files changed:**
- `requirements.txt` — dependency swap
- `gemini_adapter.py` — full SDK migration

**Why:** `google-generativeai` is deprecated by Google. The new `google-genai` SDK is the recommended replacement.

**Verified:** Module imports cleanly. Adapter conforms to `BaseProviderAdapter` interface.

---

## Verification Summary

| Test | Result |
|---|---|
| `security.py` imports | ✅ OK |
| `deps.py` imports | ✅ OK |
| `gemini_adapter.py` imports | ✅ OK |
| bcrypt hash round-trip | ✅ OK |
| bcrypt wrong-password rejection | ✅ OK |
| bcrypt existing-hash compatibility | ✅ OK |
| JWT encode → decode round-trip | ✅ OK |
| JWT sub claim preservation | ✅ OK |
| FastAPI app boot (`from app.main import app`) | ✅ OK |
| No remaining `jose` imports | ✅ Confirmed |
| No remaining `passlib` imports | ✅ Confirmed |
| No remaining `google.generativeai` imports | ✅ Confirmed |

## What Was NOT Changed

- No database schema changes
- No migration files generated
- No encryption architecture changes (Fernet unchanged)
- No provider behavior changes
- No frontend changes
- No authentication flow changes
- No major-version dependency upgrades beyond the three targeted replacements

## Recommended Manual Verification

Before considering this fully complete, test the following in a running instance:

1. **Login** with an existing user account (verifies bcrypt hash compat with real DB data)
2. **Register** a new user (verifies new hash generation)
3. **Access a protected endpoint** after login (verifies JWT creation + validation)
4. **Send a Gemini chat message** (verifies the new SDK streaming works end-to-end)
