---
name: credit-efficient-execution
description: Use as a default working habit for all Alloyd project tasks to minimize wasted tool calls and token usage — applies to file reading, editing, and multi-step tasks. Favors targeted diffs over full-file rewrites, avoids re-reading unchanged files, and batches related changes.
---

# Credit-Efficient Execution

## Core habits

- **Don't re-read a file you already have current content for.** If a file was read or
  written earlier in this session and hasn't been touched since, use what's already known
  instead of re-viewing it.
- **Prefer targeted edits over full-file rewrites.** When changing part of an existing
  file, edit only the relevant section rather than regenerating the whole file — full
  rewrites cost more and introduce more risk of accidentally reverting unrelated changes.
- **Batch related changes.** If a task touches 3 files that are all part of one logical
  change (e.g. adding a provider: config + client wrapper + router entry), do them
  together in one pass rather than as separate round-trips with the human in between,
  unless a decision point genuinely requires a pause.
- **Check before generating.** Before writing new code for something that sounds like it
  might already exist in the codebase (a utility, a similar endpoint, a shared component),
  search/check first. Duplicated logic costs credits twice — once to generate, again later
  to reconcile.
- **Don't scaffold beyond what was asked.** Building speculative extension points for
  deferred v2 features (auto-switching, tool-calling skills, payments) costs credits now
  for a shape that may not even fit the eventual real requirements. Build what v1 needs.
- **Match verbosity to the task.** A config change or small fix doesn't need a paragraph
  of explanation; a genuine architectural change does. Long explanations for small changes
  waste tokens without adding clarity.

## Why this matters here specifically

Alloyd's own product thesis is "use credits effectively across models" — the build process
should hold itself to the same standard rather than being wasteful with the very resource
the product is meant to help users conserve.
