---
name: architecture-guardian
description: Protect Alloyd from architectural drift.
---

# Architecture Guardian

## Purpose
Protect Alloyd from architectural drift.

As the project grows, avoid solving similar problems in multiple inconsistent ways.
Before introducing a new abstraction or structural pattern, check whether the project already has an appropriate place for that responsibility.

## When this applies
Use when:
- creating a new service
- creating a new provider integration
- adding a database model
- introducing a shared abstraction
- adding middleware
- adding caching
- changing request/response architecture
- creating a new application layer
- refactoring multiple modules

## Required checks
Before implementation:
- Search for an existing pattern solving a similar problem.
- Identify the correct architectural layer for the new logic.
- Avoid duplicating responsibilities across modules.
- Prefer extending an existing clean pattern over inventing a new one.
- Do not introduce abstraction unless at least one real current requirement needs it.

## Architecture boundaries
Keep responsibilities clear:
- **API layer** → request validation and response handling
- **Service layer** → business logic
- **Provider layer** → provider-specific API communication
- **Database layer** → persistence
- **Router** → deterministic model selection
- **Frontend** → presentation and user interaction

Do not allow business logic to spread randomly between these layers.

## Questions to ask
Before adding a new abstraction:
- Does something equivalent already exist?
- Does this solve a current problem or a hypothetical future problem?
- Can the existing architecture be extended cleanly?
- Will another developer know where to find this logic?
- Does this reduce complexity or merely move it around?

## Anti-patterns
Avoid:
- creating a service for a one-line operation
- generic abstractions with only one implementation
- multiple patterns for the same responsibility
- provider SDK calls inside API routes
- database queries scattered across unrelated modules
- frontend logic depending on provider internals
- "future-proofing" without a real current need

The goal is not maximum abstraction.
The goal is consistent, understandable architecture.
