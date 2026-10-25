# Learning note 02 — Next.js order lookup (Phase 1.3)

This note explains the **actual** Next.js frontend added under `frontend/`. It proxies to the existing FastAPI order lookup API and does **not** re-implement database or ownership logic.

## File responsibilities

| Path | Responsibility |
|------|----------------|
| `frontend/package.json` | Next.js 15 / React 19 deps and scripts (`dev`, `build`, `typecheck`) |
| `frontend/.env.example` | Documents server-only `FASTAPI_BASE_URL` |
| `frontend/.env.local` | Local server env (gitignored); points at FastAPI |
| `frontend/src/app/layout.tsx` | Root HTML shell + page metadata |
| `frontend/src/app/page.tsx` | Landing page: brand heading + form |
| `frontend/src/app/globals.css` | Minimal global styles (no UI framework) |
| `frontend/src/app/page.module.css` | Page layout styles |
| `frontend/src/components/OrderLookupForm.tsx` | Client form, loading/result states |
| `frontend/src/components/OrderLookupForm.module.css` | Form/result styles |
| `frontend/src/app/api/order-lookups/route.ts` | Thin server proxy to FastAPI |
| `frontend/src/lib/types.ts` | TypeScript shapes aligned with FastAPI schemas |
| Backend (unchanged) | `app/api/routes/orders.py`, `app/services/order_lookup.py`, Postgres |

## Request flow

```text
Browser (OrderLookupForm)
  → POST /api/order-lookups          (Next.js Route Handler, server-only)
  → POST {FASTAPI_BASE_URL}/api/v1/demo/order-lookups
  → FastAPI create_order_lookup
  → SQLAlchemy lookup_order
  → PostgreSQL orders ⨝ customers
  → JSON back through proxy
  → Browser renders success / not-found / validation / unavailable
```

### Why a server proxy?

- `FASTAPI_BASE_URL` stays **server-only** (no `NEXT_PUBLIC_` prefix).
- The browser never talks to FastAPI directly in this setup.
- Lookup rules remain in FastAPI; Next.js only forwards JSON and status codes.

### UI states

| State | When |
|-------|------|
| idle | Initial |
| loading | Request in flight (previous result cleared) |
| success | HTTP 200 + order payload (`is_simulated: true`) |
| validation | HTTP 422 from FastAPI (or bad JSON body) |
| not_found | HTTP 404 `order_not_found` |
| unavailable | Network failure / misconfigured `FASTAPI_BASE_URL` / HTTP 503 |

Null `courier` or `estimated_delivery` display as **Not available**.

## Startup (host Next.js + Docker FastAPI)

```bash
# Terminal A — backend (from repo root)
docker compose up -d db api

# Terminal B — frontend
cd frontend
cp .env.example .env.local   # if needed
npm install
npm run dev                  # http://127.0.0.1:3000
```

## What is not included

- No Ollama / AI prompts
- No chat UI, auth, Tailwind/UI kit
- No duplication of order ownership logic in Next.js
