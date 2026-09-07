---
name: debugging-systematically
description: Do not patch symptoms blindly. Find the failure mechanism first.
---

# Systematic Debugging

## Rule
Do not patch symptoms blindly. Find the failure mechanism first.

## Debugging Process

### Step 1 — Reproduce
Confirm the problem reliably.
Document:
- expected behavior
- actual behavior
- exact error
- conditions required to reproduce

### Step 2 — Localize
Determine where the failure occurs:
- frontend
- API boundary
- backend service
- database
- provider adapter
- external provider

Do not investigate the entire system at once.

### Step 3 — Gather evidence
Inspect:
- relevant logs
- request/response status
- stack traces internally
- database state where relevant
- configuration presence
- recent changes

**Never expose secrets while debugging.**

### Step 4 — Form a hypothesis
State:
*The likely root cause is X because evidence Y indicates Z.*

Avoid making multiple unrelated changes simultaneously.

### Step 5 — Apply the smallest fix
Fix the identified cause.
Do not rewrite unrelated modules.

### Step 6 — Verify
Confirm:
- original issue is resolved
- no regression was introduced
- failure behavior is still handled properly

## Debugging Anti-patterns
Never:
- randomly rewrite working modules
- add multiple speculative fixes at once
- suppress errors without understanding them
- catch broad exceptions just to make errors disappear
- change architecture because of one bug
- assume the latest edited file caused the issue without evidence

The goal is not to make the error disappear.
The goal is to understand and remove its cause.
