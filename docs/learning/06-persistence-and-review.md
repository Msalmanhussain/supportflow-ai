# Learning note — Phase 3.1 persistence and human review

Study this after the Phase 3.1 stop report.

## Goal

Persist every successfully generated support draft and let a **local single-operator** review queue edit, approve, or reject it. Classification remains advisory. Prompt injection is **not** solved. Nothing is sent.

## Schema

Migration: `20261021_0002` (`alembic/versions/20261021_0002_create_support_requests_and_events.py`)

### `support_requests`

| Column | Notes |
|--------|--------|
| `id` | UUID PK |
| `idempotency_key` | Unique client key |
| `idempotency_payload_hash` | SHA-256 of canonical message+email JSON |
| `message`, `customer_email` | Original synthetic inputs |
| `classification_*` | Intent / order_id / model review flag |
| `outcome`, `draft_original`, `draft_current` | Workflow + editable draft |
| `sources_snapshot` | JSONB verbatim policy citations |
| `model_id`, `prompt_version` | e.g. `qwen3:1.7b`, `classification_v1` |
| `review_status` | `pending_review` \| `approved` \| `rejected` |
| `requires_human_review` | Always true (workflow requirement) |
| `revision` | Optimistic concurrency integer |
| `reviewed_text` | Exact text stored on approve |
| `created_at` / `updated_at` | Timezone-aware |

### `support_review_events`

Append-only: `action`, `revision`, `note?`, `created_at`. **No reviewer identity** (documented limitation).

## Idempotency

Header: `Idempotency-Key` (required, ≤128 chars).

| Case | Behaviour |
|------|-----------|
| Same key + same payload | Return existing row (no duplicate) |
| Same key + different payload | **409** `idempotency_key_conflict` |
| Concurrent same key | Unique constraint; losers reload winner |
| Model failure then retry | Safe — nothing persisted on failure |
| DB race mid-insert | IntegrityError → reload matching payload |

## Transaction boundaries

1. Short session: idempotency lookup → **close**.
2. Inference / generation with **no** DB session.
3. New session: insert request + `created` event → commit.
4. Review mutations: atomic `UPDATE … WHERE id AND revision AND pending_review`.

Failed generation is never stored as a completed draft.

## Concurrency

- Edits / approve / reject require `expected_revision`.
- Stale revision → **409** `stale_revision` (reload).
- Concurrent decisions: one **200**, one **409**.
- Approved/rejected requests are read-only.

## API surface

- `POST /api/v1/demo/support-drafts` (+ Idempotency-Key) → persisted response fields
- `GET /api/v1/demo/support-requests?status=&page=&page_size=`
- `GET /api/v1/demo/support-requests/{id}`
- `PATCH …/draft`, `POST …/approve`, `POST …/reject`

## Frontend

- `/requests` list + filters
- `/requests/[id]` edit / save / approve / reject
- Proxies under `frontend/src/app/api/support-requests/**`
- Approve blocked while editor has unsaved changes
- Copy: “Approval records a local review decision. Nothing is sent.”

## Files

| Path | Role |
|------|------|
| `app/models/support_request.py` | ORM |
| `app/services/support_request_persistence.py` | Persist + review |
| `app/api/routes/support_requests.py` | Review HTTP |
| `app/api/routes/support_drafts.py` | Create + persist |
| `tests/test_support_requests.py` | Persistence/concurrency tests |
