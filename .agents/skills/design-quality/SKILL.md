---
name: design-quality
description: Use for any UI, component, or styling work in the Alloyd project. Enforces a defined type and spacing scale, consistent design tokens, and deliberate visual choices instead of default unstyled component libraries or inconsistent ad-hoc Tailwind classes.
---

# Design Quality

## When this applies

Any time a screen, component, or layout is being built or restyled — the chat UI, the
onboarding/key-setup flow, the skill picker, settings, anything user-facing.

## Baseline requirements

- **Design tokens, not ad-hoc values.** Colors, spacing, and type sizes come from a single
  defined scale (a `tokens.css`/Tailwind config, not one-off hex codes or arbitrary
  `px` values sprinkled through components). If the token file doesn't exist yet, creating
  it is the first step of the first UI task, not something to skip.
- **Deliberate typography.** Pick a type scale (e.g. a modular scale) and stick to it —
  not whatever size looks fine in the moment. Headings, body text, and UI labels should
  each map to a consistent size/weight from the scale.
- **Consistent spacing rhythm.** Use a spacing scale (e.g. 4px/8px increments) for margins,
  padding, and gaps — not arbitrary values that don't line up across components.
  Inconsistent spacing is the single fastest way a UI reads as unpolished.
- **Intentional, not default.** Don't ship the out-of-the-box look of a component library
  or default Tailwind styling untouched. A chat UI is a crowded space (ChatGPT, Claude,
  Gemini, Poe, T3.chat) — looking like an unstyled clone undermines the "real product, not
  a college project" goal directly.
- **States, not just the happy path.** Loading, empty, error, and disabled states need the
  same visual care as the primary state — a chat UI spends a lot of time in "waiting on a
  model response" and that state matters as much as the final message render.

## What to avoid

Grabbing whatever spacing/color "looks about right" per-component without a shared scale,
leaving default shadcn/ui or Tailwind starter styling unmodified, and treating visual
polish as a final pass instead of part of building each component.
