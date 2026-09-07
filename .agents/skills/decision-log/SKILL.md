---
name: decision-log
description: Use whenever a task in the Alloyd project involves a real architectural or design decision with more than one reasonable option — schema design, router logic, auth approach, provider integration pattern, or similar. Records the options considered and the reasoning behind the choice in docs/decisions/, in a lightweight ADR-style format.
---

# Decision Log

## When this applies

Not every choice needs this — most day-to-day implementation decisions don't. This
applies specifically when:

- There were genuinely 2+ reasonable approaches, not just one obvious path
- The choice will be expensive to reverse later (schema shape, auth model, how the
  router config is structured, how provider credentials are stored)
- A future contributor (including future-you) would reasonably ask "why did we do it this
  way?"

## What to record

Append an entry to `docs/decisions/LOG.md` (create it if it doesn't exist) in this format:

```
## [YYYY-MM-DD] <short decision title>

**Context:** What problem/task prompted this decision.

**Options considered:**
- Option A — one-line description, one-line tradeoff
- Option B — one-line description, one-line tradeoff

**Decision:** Which option, in one sentence.

**Why:** 1-3 sentences on the actual reasoning — not "it seemed better" but the specific
factor that tipped it (e.g. "keeps the router config in one file, matching AGENTS.md's
requirement that it stay easy to edit during testing").

**Revisit if:** What would change (scale, new requirement, provider change) that should
trigger reconsidering this.
```

Keep each entry short — a few lines per section, not a design doc. The goal is a fast
"why" lookup, not exhaustive documentation.

## What NOT to log here

Routine implementation choices with no real alternative, formatting/style choices already
covered by AGENTS.md, or anything already decided and locked in the v1 spec (re-litigating
locked scope belongs in a conversation with the human, not a new log entry).
