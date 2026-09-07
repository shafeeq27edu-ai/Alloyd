---
name: scope-guardian
description: Does this change directly help Alloyd reach its V1 definition of done?
---

# Scope Guardian

## Core Question
Does this change directly help Alloyd reach its V1 definition of done?
If not, question whether it belongs now.

## V1 Decision Filter
Evaluate every significant addition:

### 1. Core Value
Does it improve:
- unified AI access
- provider reliability
- routing
- manual control
- reusable prompt skills
- security
- daily usability

### 2. Urgency
Is it required now?
Or can it wait until real users expose the need?

### 3. Complexity
Does the feature introduce:
- new infrastructure
- new dependencies
- new security risks
- operational burden
- significant maintenance cost

### 4. Evidence
Is this being added because of:
- real user need
- actual dogfooding pain
- required V1 functionality
or simply because it sounds useful?

## Default Behavior
When uncertain: **Defer.**

A smaller finished product is more valuable than a larger unfinished platform.

## Explicit V1 Red Flags
Flag these immediately:
- agents
- tool calling
- RAG
- vector databases
- payments
- autonomous workflows
- multi-model scoring
- usage billing
- credit monitoring
- automatic provider switching
unless the human explicitly changes the V1 scope.

## Success Metric
Do not optimize for feature count.
Optimize for:
*How often can the user complete real AI tasks inside Alloyd without opening another provider interface?*
