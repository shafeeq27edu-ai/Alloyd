---
name: product-thinking
description: Approach features by starting with the user problem and ensuring they strengthen the core product loop.
---

# Product Thinking

## Start with the user problem
Before implementing a feature, ask:
- What problem does this solve?
- When would the user encounter that problem?
- How do they solve it today?
- Is Alloyd actually improving that workflow?

## Core Product Loop
The Alloyd V1 loop is:
1. User has a task
2. Opens one interface
3. Selects a skill or sends a message
4. Alloyd selects an appropriate model
5. User can override the decision
6. User receives a reliable response
7. User continues working without switching tabs

Every feature should strengthen this loop.

## UX Principles
- **Reduce decisions**: The router should reduce unnecessary model-selection friction.
- **Preserve control**: Users can always manually override the model.
- **Explain automation**: Automatic routing should never feel mysterious.
- **Recover gracefully**: Provider failures should provide useful next actions.
- **Keep context visible**: The user should understand active provider, active model, selected skill, routing reason, and conversation state.

## Product Decision Test
Before adding something, ask:
*If this feature disappeared, would daily use become meaningfully worse?*
If the answer is no, it probably does not belong in V1.

## Dogfooding Rule
Real usage beats assumptions.

Whenever the builder switches to another AI product during normal work, capture:
- what task was being performed
- why Alloyd was not sufficient
- whether the problem is UX, reliability, routing, provider availability, or missing capability

These observations should guide future work.
