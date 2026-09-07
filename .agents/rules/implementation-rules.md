# Implementation Rules

## 5. Provider Architecture Rules

All providers must follow one shared abstraction.
Do not scatter provider SDK calls throughout services or API routes.

The architecture should be:
`Router -> Provider Registry -> Provider Adapter -> Provider API`

Each provider implementation must handle:
- authentication failure
- invalid API key
- timeout
- rate limits
- insufficient credits/quota
- provider outage
- malformed responses

Provider-specific responses must be normalized before reaching the frontend.
The frontend should not need to understand provider SDK differences.

## 6. Router Rules

The V1 router is intentionally simple.
It is deterministic and rule-based.

Routing priority:
1. Manual model override
2. Skill-defined category
3. Rule-based task detection
4. Default fallback model

All routing rules must live in one discoverable configuration.
Do not scatter routing decisions throughout the codebase.

The router must return:
- selected provider
- selected model
- routing reason
- whether the decision was manual or automatic

The user must be able to understand why a model was selected.

## 7. Product Skill Rules

Product skills and Antigravity development skills are different things.

**Product Skills**
Product skills are user-facing prompt presets.
They must remain simple.

A product skill:
`Input -> Inject System Prompt -> Assign Task Category -> Router -> Model Response`

No:
- tool calling
- autonomous planning
- multi-step execution
- background agents
in V1.

## 8. Code Quality Rules

Every implementation should prioritize:
- readability
- maintainability
- predictable behavior
- clear naming
- minimal duplication
- small focused functions
- explicit error handling

Avoid:
- unnecessary abstractions
- deeply nested conditionals
- giant utility files
- duplicate business logic
- magic constants scattered through the codebase
- dead code
- unused dependencies
- premature optimization

Before creating new code, check whether an equivalent implementation already exists.

## 9. Testing and Verification Rules

Code compiling does not mean the feature works.
Every meaningful feature must be verified.

Verification should include, where relevant:
- happy path
- invalid input
- provider failure
- authentication failure
- empty state
- loading state
- error state
- persistence behavior
- regression risk

For critical backend logic:
- add automated tests where practical

For UI flows:
- verify the actual user journey

For provider integrations:
- test with realistic provider responses and failure scenarios

Never claim something is working unless it has actually been verified.

## 10. Debugging Rules

When something breaks:
Do not immediately rewrite code.

Follow this process:
1. Reproduce the problem.
2. Identify the exact failure point.
3. Inspect logs and relevant data.
4. Form a hypothesis.
5. Test the smallest possible fix.
6. Verify the original failure is resolved.
7. Check for regressions.

Avoid random trial-and-error patches.
If the root cause is unknown, investigate before changing architecture.

## 11. UI and UX Rules

All UI work must use the `design-quality` skill.
The product should feel intentional, not assembled from default components.

Every major interface must account for:
- loading
- empty
- error
- disabled
- success
- mobile/responsive behavior where applicable

Prioritize clarity over decoration.

The user should always understand:
- what model is active
- why it was selected
- how to override it
- what is currently happening
- what went wrong if something fails

Do not hide important system behavior behind unnecessary abstraction.

## 12. Credit-Efficient Execution

Use the `credit-efficient-execution` skill by default.

Important habits:
- do not re-read unchanged files
- search before generating duplicate code
- prefer targeted edits
- batch related changes
- avoid unnecessary explanations
- avoid speculative implementation
- do not regenerate working code

Use tools and tokens deliberately.

## 15. Final Agent Behavior

The agent should behave like a careful senior engineer working on a product that will actually be used.

Before coding:
- understand
- inspect
- plan

While coding:
- follow existing architecture
- minimize complexity
- protect security
- stay within scope

After coding:
- verify
- test failures
- check regressions
- report what changed clearly

Do not optimize for producing the most code.
Optimize for producing the correct product.
