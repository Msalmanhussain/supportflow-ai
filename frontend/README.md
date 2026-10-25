# SupportFlow AI — frontend (Phase 1.3)

Minimal Next.js (App Router + TypeScript) page for synthetic order lookup.

## Prerequisites

- Node.js 18.18+ (developed with Node 22 LTS)
- Phase 1.2 FastAPI + PostgreSQL running (`http://127.0.0.1:8000`)

## Configuration

```bash
cp .env.example .env.local
# FASTAPI_BASE_URL is server-only (no NEXT_PUBLIC_ prefix)
```

## Commands

```bash
cd frontend
npm install
npm run typecheck
npm run build
npm run dev
```

Open [http://127.0.0.1:3000](http://127.0.0.1:3000).

## Architecture

Browser → `POST /api/order-lookups` (Next.js server route) → FastAPI `POST /api/v1/demo/order-lookups` → PostgreSQL.

Order lookup logic stays in FastAPI. This app only proxies and displays results.
