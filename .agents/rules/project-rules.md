# Project Rules

## 1. Core Engineering Principles

These principles apply to every implementation decision.

### 1. Build the simplest correct solution
Do not introduce complexity unless the current V1 requirement actually needs it.

Prefer:
- simple architecture over clever architecture
- explicit logic over hidden magic
- small modules over large abstractions
- deterministic behavior over unpredictable automation
- existing patterns over creating new patterns

Avoid speculative architecture.
Do not build infrastructure for hypothetical future requirements.

### 2. Understand before modifying
Before changing existing code:
- Inspect the relevant files.
- Search for existing patterns or utilities.
- Understand how the current system works.
- Identify the smallest correct change.
- Implement without breaking unrelated functionality.

Never blindly rewrite a file without understanding its current role.

### 3. Plan before implementing non-trivial work
Use the `planning-first` skill for:
- new features
- new endpoints
- schema changes
- provider integrations
- routing changes
- authentication changes
- modules touching multiple files
- significant refactors

Do not create a long planning document.
The goal is a short implementation plan that makes the architecture clear before coding.

### 4. Do not silently make major decisions
If multiple reasonable architectural approaches exist, use the `decision-log` skill.

This applies especially to:
- database schema decisions
- authentication architecture
- API key encryption
- provider abstraction
- router design
- streaming architecture
- state management
- persistence patterns

Do not repeatedly revisit decisions already locked in the V1 specification.

## 2. Locked V1 Scope

All implementation must remain inside the following V1 scope unless explicitly changed by the human.

### Included
**Chat**
- unified multi-provider chat interface
- persistent conversations
- streaming responses
- manual model selection
- provider/model visibility
- routing explanation

**Provider Support**
Initial providers:
- Gemini
- Groq
- OpenAI or Anthropic

All provider integrations must follow a shared provider abstraction.

**Routing**
- rule-based routing only
- deterministic category-to-model mapping
- centralized configuration
- transparent routing explanation
- manual override always takes priority

**Skills**
Skills are prompt-template presets.
Each skill:
- has a defined purpose
- injects a tuned system prompt
- maps to a task category
- uses the router

Initial product skills:
- Code Review
- Explain Code
- Summarization
- Writing
- Brainstorming
- Research Analysis

No multi-step agents in V1.

**Security**
- BYOK only
- encrypted API key storage
- real authentication
- secure sessions
- secrets never exposed to the client

## 3. Explicitly Forbidden in V1

Do not implement, scaffold, or silently prepare infrastructure for:
- multi-agent workflows
- LangGraph orchestration
- agent chains
- autonomous agents
- web-search tools
- code execution tools
- RAG
- vector databases
- output-scoring routers
- multi-model comparison
- automatic provider switching based on credits
- payment systems
- Stripe
- consumer-account login automation
- provider browser automation
- consumer session cookies
- speculative V2 infrastructure

If a requested task requires one of these, stop and flag the scope conflict.
Do not "just prepare the architecture for later."

## 13. Scope Protection

Feature requests must be checked against the locked V1 scope.

Before implementation, ask:
- Does this directly improve the core V1 loop?
- Is it required for daily use?
- Does it introduce major complexity?
- Can it be deferred without hurting usability?

If the feature does not clearly belong in V1, flag it instead of silently implementing it.
The project wins by finishing, not by accumulating features.

## 14. Definition of Done

A feature is not done when:
- the code compiles
- the UI renders
- one happy-path test passes

A feature is done when:
- It satisfies the intended user problem.
- It stays within V1 scope.
- It follows the existing architecture.
- Errors are handled properly.
- Secrets remain secure.
- The UI handles relevant states.
- It has been verified.
- Important decisions are documented.
- The implementation does not introduce unnecessary complexity.

For anything touching the core chat loop:
It should be used in a realistic workflow, not just tested artificially.
