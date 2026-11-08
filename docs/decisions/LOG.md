# Decision Log

## 2026-11-08 — Phase 1 dependency baseline

**Context:** A fresh venv from `requirements.txt` failed because async SQLAlchemy needs `greenlet`; the file declared `sqlalchemy` without the `asyncio` extra. Dependencies are unpinned, so the fresh install resolved to newer majors than the previous venv (Anthropic 2.6, google-genai 3.0, bcrypt 5.0, SQLAlchemy 2.1).

**Options:**
- (a) Declare `sqlalchemy[asyncio]`, keep the current resolved versions.
- (b) Pin every dependency to the previous venv's versions.
- (c) Migrate code to current majors and pin.

**Decision:** (a) for Phase 1. Declare the extra, keep the fresh versions, and use the 48-test suite as the baseline. Real SDK compatibility is proven by the Phase 2 smoke script. Pinning or migration is revisited in Phase 4.

**Why:** The minimal change restores a trustworthy baseline without freezing stale SDKs. The tests mock provider SDKs, so they cannot prove real-provider compatibility either way.

**Revisit if:** the smoke script fails against current SDKs, a major upgrade breaks app code, or Phase 4 starts.

## 2026-11-08 — Single model catalog in adapters

**Context:** Model IDs were duplicated across adapters, `router_config.yaml`, `title_generator.py`, and `page.tsx`, and several were retired.

**Options:**
- (a) Keep per-layer lists and sync them manually.
- (b) Make each adapter's `get_models()` the only source; validate the router at startup and expose the catalog through an authenticated API.

**Decision:** (b). `ProviderRegistry.all_models()`, `has_model()`, and `fast_model()` read adapter definitions; `validate_catalog()` refuses startup on unknown providers/models; `GET /api/models` serves the catalog; the frontend and title generator consume it.

**Why:** One list removes drift. Startup validation turns a silent bad route into a fast failure, and the frontend can no longer offer retired IDs.

**Revisit if:** a provider needs per-account model availability or dynamic discovery.

## 2026-11-08 — Auto fallback on MODEL_UNAVAILABLE

**Context:** A retired model returns 404. Treating that as a hard failure leaves Auto mode stuck.

**Decision:** Auto mode falls back on retryable errors **and** `MODEL_UNAVAILABLE`, logging a loud warning. It never falls back on `INVALID_API_KEY` or `BAD_REQUEST`. Manual mode reports the error and never falls back.

**Why:** Fallback on 404 keeps Auto usable when a provider retires a model; auth and request-shape errors are user/config problems that another provider cannot fix. Manual mode must honor the user's explicit choice.

## 2026-11-08 — Buffered SSE parser

**Context:** The frontend split each network chunk on `\n`, so events split across chunks were dropped or corrupted.

**Options:**
- (a) Patch the page-local loop.
- (b) Add a small parser module with cross-chunk buffering and tests.

**Decision:** (b), `src/lib/sse.ts`. It handles CRLF, multi-line `data:`, comments, blank-line dispatch, and a final flush. Stream responses also send `Cache-Control: no-transform` and `X-Accel-Buffering: no`.

**Why:** SSE framing is easy to get subtly wrong; isolating it makes it unit-testable without browser plumbing.

## 2026-11-08 — Image generation deferred to V2

**Context:** `IMAGE_GENERATION` selected text models that cannot generate images, so the route always produced text or failed.

**Decision:** Remove the category from the router, classifier, config, and frontend. Image prompts classify as `GENERAL`. Reintroduce image generation in V2 as a proper capability with an image-capable model catalog.

**Why:** Shipping a category that cannot work is worse than routing those prompts to a model that can discuss them.
