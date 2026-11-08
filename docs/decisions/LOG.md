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
