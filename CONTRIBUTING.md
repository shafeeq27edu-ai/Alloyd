# Contributing to Alloyd

## 1. Project Overview

Alloyd is a multi-provider AI chat workspace built on a BYOK (Bring Your Own Key) architecture. It supports Groq, Google Gemini, and Anthropic Claude through deterministic model routing, provider fallback, and reusable prompt-based skills.

**Stack:** Next.js frontend, FastAPI backend, Supabase PostgreSQL, SQLAlchemy + Alembic, JWT authentication, Fernet-encrypted provider keys.

## 2. Development Philosophy

Every change follows this workflow:

```
Plan → Implement → Test → Audit → Fix → Re-test → Commit
```

- Write a short plan before non-trivial changes.
- Keep changes small and reviewable.
- Test before committing.
- Never declare a feature complete without verification.

## 3. Repository Structure

```
alloyd/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI route handlers (auth, keys, chat, conversations)
│   │   ├── core/         # Security, encryption, rate limiting, errors
│   │   ├── db/           # SQLAlchemy models and database config
│   │   └── providers/    # Provider adapters (Groq, Gemini, Anthropic)
│   ├── alembic/          # Database migrations
│   ├── tests/            # Backend test suite
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── app/          # Next.js pages (chat, login, settings)
│   │   ├── components/   # Reusable UI components
│   │   └── lib/          # API client and utilities
│   └── package.json
└── docs/                 # Project documentation
```

## 4. Local Development

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env            # then fill in your values
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Database Migrations

```bash
cd backend
alembic upgrade head            # apply migrations
alembic revision --autogenerate -m "description"   # create a new migration
```

## 5. Environment Variables

Use a local `.env` file in the `backend/` directory. **Never commit `.env` files.**

See `backend/.env.example` for the required variables:

- `DATABASE_URL` — PostgreSQL connection string
- `SECRET_KEY` — JWT signing secret
- `ENCRYPTION_KEY` — Fernet key for provider API key encryption
- `ACCESS_TOKEN_EXPIRE_MINUTES` — Session duration

Provider API keys are configured per-user through the application UI, not through environment variables.

## 6. Testing

### Backend Tests

```bash
cd backend
python -m pytest
```

### Frontend Lint

```bash
cd frontend
npm run lint
```

### Frontend Production Build

```bash
cd frontend
npm run build
```

Run all three before submitting changes.

## 7. Security Rules

- **Never** commit secrets, API keys, or credentials.
- **Never** log provider API keys in application code.
- **Never** expose decrypted provider keys in API responses, exceptions, or error messages.
- **Never** store authentication tokens in `localStorage`.
- Provider keys must remain Fernet-encrypted at rest in the database.
- **Never** include real API keys in pull requests or issues.
- Maintain user data isolation — users must only access their own data.

## 8. Pull Requests

- Keep changes focused on a single concern.
- Use descriptive commit messages.
- Include tests for behavioral changes.
- Run lint and build before submitting.
- Explain security-sensitive changes explicitly.

## 9. Commit Guidelines

Use conventional-style commit messages:

```
feat: add provider key validation
fix: preserve conversation ownership on delete
docs: update contributing guide
test: add password boundary tests
refactor: extract validation into schema
```

Keep the subject line concise. Add a body for non-obvious context.

## 10. Reporting Bugs

A useful bug report includes:

- Steps to reproduce the issue
- Expected behavior
- Actual behavior
- Relevant environment (OS, browser, Node/Python version)
- Logs with **all secrets and API keys removed**

**Do not paste API keys, passwords, or credentials in bug reports.**

## 11. Security Issues

Do not post credentials, API keys, or detailed vulnerability information in public GitHub issues.

If you discover a security vulnerability, report it responsibly and ensure your report contains no secrets or sensitive credentials.

## 12. Scope

Alloyd V1 is intentionally focused. Contributions should avoid introducing unnecessary infrastructure, unplanned dependencies, or feature creep.

Before proposing a significant change, open an issue to discuss the approach. Small, well-tested improvements are preferred over large speculative features.
