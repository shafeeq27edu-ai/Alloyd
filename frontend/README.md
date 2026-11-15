# Alloyd frontend

Next.js 16 (App Router) chat UI for [Alloyd](../README.md). It talks to the
FastAPI backend over SSE and keeps the session in HttpOnly cookies.

## Run it

The supported setup (including the API and database) is in the
[root README](../README.md). For a frontend-only dev server against an already
running API:

```bash
npm ci
npm run dev        # http://localhost:3000
```

`NEXT_PUBLIC_API_BASE_URL` defaults to `http://localhost:8000/api`. It is baked
into the bundle at build time, so a production build needs it set:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api npm run build
```

## Checks

```bash
npm test           # SSE parser, API client, usage formatting
npm run lint
npm run test:e2e   # needs the compose stack; see docs/RUNNING.md
```

Architecture notes: [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md). Only the
backend calls providers; the browser never receives provider keys.
