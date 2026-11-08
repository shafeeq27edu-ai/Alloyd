# Alloyd — Project Operating Rules

## Project Identity
Alloyd is a real product being built for actual daily use, not a demo, tutorial project, or portfolio mockup.

Its purpose is to provide one unified interface for multiple AI models using a secure BYOK architecture, intelligent rule-based routing, manual model control, and reusable prompt-based skills.

The goal is not to build the most features.

The goal is to build a product that is:
- reliable
- secure
- fast
- understandable
- pleasant to use daily

The locked V1 definition of success is:
The builder and a small group of developers can use Alloyd for real work for at least one week without needing to constantly switch to separate AI provider interfaces.

## Final Skill Priority System
| Situation | Skill |
| :--- | :--- |
| New feature | `planning-first` |
| Architectural choice | `decision-log` + `architecture-guardian` |
| Any implementation | `credit-efficient-execution` |
| UI work | `design-quality` |
| Sensitive functionality | `security-review` |
| After implementation | `verification-first` |
| Bugs/errors | `debugging-systematically` |
| New feature idea | `scope-guardian` |
| UX/product decisions | `product-thinking` |

## Critical Rule
Never make the project appear complete when functionality has not been verified. Report uncertainty honestly.

This is extremely important when using coding agents. A polished summary saying "everything is implemented successfully" means nothing if the actual application hasn't been tested.

*(See `.agents/rules/` for detailed project, security, and implementation rules.)*

## Non-Negotiable Security
- Never print, `cat`, `echo`, or otherwise display values from any `.env` file. To inspect one, list key names only.
- BYOK only. Provider calls stay on the backend; never automate consumer logins, session reuse, or cookie extraction.
- Provider keys are encrypted at rest and never logged, returned by APIs, exposed to client JavaScript, or committed to git.
- Auth tokens stay in HttpOnly cookies, never localStorage/sessionStorage. Keep CSRF protection on every state-changing endpoint and never weaken CORS, cookie, or CSRF settings.
- Verify ownership server-side on every resource; never trust user IDs from the frontend.
- Never surface stack traces or raw provider errors. Return a safe, actionable message and log sanitized details only.
- No destructive database operations, migrations, or dependency changes without explicit approval.
