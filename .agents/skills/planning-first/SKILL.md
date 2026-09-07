---
name: planning-first
description: Use before implementing any new feature, endpoint, module, or non-trivial code change in the Alloyd project. Produces a short written plan — steps, affected files, and alternative approaches considered — before code is written, to prevent unplanned "vibe coded" implementation.
---

# Planning First

## When this applies

Any task that adds a new feature, endpoint, module, schema change, or touches more than one
file with related logic. Skip this for genuinely trivial changes (typo fixes, copy changes,
formatting) — this is for anything where there's more than one reasonable way to build it.

## What to produce before writing code

A short plan, posted in the chat/agent panel (not buried in a file), covering:

1. **Goal** — one sentence: what this change accomplishes and why it's needed now, tied
   back to the locked v1 scope in AGENTS.md.
2. **Approach** — the steps you'll take, in order, and which files/modules are affected.
3. **Alternatives considered** — if there was a real fork in the road (e.g. "extend the
   existing router config" vs. "add a new routing layer"), name the option not taken and
   the one-line reason. If there genuinely was only one reasonable approach, say so —
   don't invent a fake alternative to fill this section.
4. **Scope check** — explicitly confirm this stays inside locked v1 scope, or flag that it
   doesn't and needs a human decision before proceeding.

If a step in the plan surfaces a decision with real, lasting tradeoffs (schema shape,
provider integration pattern, auth approach), hand that specific decision to the
`decision-log` skill rather than just picking one silently.

## What "done planning" looks like

The plan is short — a few bullet points, not an essay. The bar is "a teammate could review
this in 30 seconds and know if it's the right shape," not exhaustive documentation. Once
the plan is stated, proceed to implementation in the same turn — this isn't a separate
approval gate, it's a forcing function to think before typing.

## Anti-pattern this exists to prevent

Jumping straight from a task description to generated code with no stated reasoning,
producing a plausible-looking feature that doesn't fit the existing router/schema/auth
patterns, or duplicates logic that already exists elsewhere in the codebase.
