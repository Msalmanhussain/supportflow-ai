# Learning note 01 — Backend foundation (Phase 1.2)

This note explains the **actual** SupportFlow AI backend as implemented in this repository. It does not invent runtime behaviour that has not been verified on this machine.

**Status labels used here**

| Label | Meaning |
|-------|---------|
| Implemented | Present in the repo |
| Verified | Successfully executed here |
| Blocked | Cannot run until Docker Desktop is installed |
| Planned | Future work |

Phase 1.2 code is **Implemented**. Container build, migrate, seed, API smoke tests, and pytest were **Verified** on 2026-10-18 (Docker 29.8.2; 10 pytest tests passed).

---

## A. Repository map

| Path | Responsibility |
|------|----------------|
| `README.md` | Project overview, run commands, honest verification status |
| `.env.example` | Documented placeholders (no real secrets) |
| `.env` | Local secrets (gitignored; never commit) |
| `.gitignore` / `.dockerignore` | Keep secrets and junk out of git/images |
| `requirements.txt` | Pinned Python dependencies for the API image |
| `pyproject.toml` | Project metadata + pytest config |
| `Dockerfile` | Python 3.12.15 image build for the API |
| `docker-compose.yml` | `db`, `api`, `migrate`, `seed`, `test` services |
| `docker/postgres/init-databases.sh` | Creates `supportflow_test` on first Postgres init |
| `scripts/generate_dev_env.sh` | Writes local `.env` with random credentials (does not print them) |
| `alembic.ini` + `alembic/` | Migration tooling and revision scripts |
| `alembic/versions/20260318_0001_*.py` | Initial `customers` + `orders` schema |
| `app/main.py` | FastAPI app factory, routers, validation error handler |
| `app/config.py` | `Settings` via pydantic-settings (`APP_ENV`, `DATABASE_URL`, …) |
| `app/database.py` | SQLAlchemy engine, `SessionLocal`, `get_db`, `reset_engine` |
| `app/models/customer.py` | ORM `Customer` (internal; not returned by lookup API) |
| `app/models/order.py` | ORM `Order` + `OrderStatus` enum |
| `app/schemas/order.py` | Request/response Pydantic models for lookup |
| `app/schemas/health.py` | Health/ready response models |
| `app/schemas/errors.py` | Shared error body shape |
| `app/api/routes/health.py` | `GET /health`, `GET /ready` |
| `app/api/routes/orders.py` | `POST /api/v1/demo/order-lookups` |
| `app/services/order_lookup.py` | DB query + demo ownership match |
| `app/services/readiness.py` | DB ping + Alembic head comparison |
| `app/seed/data.py` | Ten fictional orders / example.com customers |
| `app/seed/run.py` | Idempotent seeder (`python -m app.seed`) |
| `tests/` | Integration tests for health, lookup, seed (isolated test DB) |
| `docs/project-scope.md` | MVP scope and confirmed architecture |
| `docs/implementation-plan.md` | Phased plan with Implemented/Verified/Blocked/Planned |
| `docs/docker-desktop-macos-intel.md` | Manual Docker Desktop install steps |

---

## B. Startup flow

Nothing auto-migrates or auto-seeds when Python imports the app.

```text
[you] docker compose up -d db
        → Postgres starts
        → healthcheck: pg_isready (automatic)
        → init-databases.sh runs ONLY on first empty volume (automatic once)

[you] docker compose --profile tools run --rm migrate   # EXPLICIT
        → alembic upgrade head

[you] docker compose --profile tools run --rm seed      # EXPLICIT
        → python -m app.seed (refuses unless APP_ENV is development|test)

[you] docker compose up -d api
        → uvicorn app.main:app --host 0.0.0.0 --port 8000
        → published on host as 127.0.0.1:8000 only
```

| Step | Automatic? |
|------|------------|
| Postgres healthcheck | Yes (Compose) |
| Create `supportflow_test` | Yes, only on first DB data init |
| Alembic migrate | **No — explicit** |
| Seed | **No — explicit** |
| Start uvicorn | Yes once `api` service is up |

API container hostname for Postgres is the Compose service name `db`, not `localhost`.

---

## C. Health request flow

Trace of **`GET /health`** (process liveness only — does **not** touch the database).

1. HTTP request hits uvicorn → FastAPI `app` in `app/main.py`.
2. Router from `app/api/routes/health.py` matches `@router.get("/health")`.
3. Function `health()` runs:
   - `get_settings()` → reads cached `Settings` (`app_name`, …).
   - Builds `HealthResponse(status="ok", service=..., version=__version__)`.
4. FastAPI serializes the Pydantic model to JSON (`response_model=HealthResponse`).

```19:25:app/api/routes/health.py
def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=__version__,
    )
```

Contrast: **`GET /ready`** calls `check_readiness(database.engine)` in `app/services/readiness.py` (SQL `SELECT 1` + Alembic head vs current). Returns **503** when not ready.

---

## D. Order lookup flow

Endpoint: **`POST /api/v1/demo/order-lookups`**

**Important:** Email matching is a **demonstration ownership check only**, not production authentication.

1. **JSON body** → FastAPI parses into `OrderLookupRequest` (`app/schemas/order.py`).
   - Requires `order_id` and `customer_email` (`EmailStr`).
   - Validators strip/normalize (`order_id` strip; email lowercased).
2. Invalid body → `RequestValidationError` → handler in `app/main.py` → **422** with `code: validation_error`.
3. Route `create_order_lookup` in `app/api/routes/orders.py`:
   - `db: Session = Depends(get_db)` injects a SQLAlchemy session.
   - Calls `lookup_order(db, order_id=..., customer_email=...)`.
4. **`lookup_order`** (`app/services/order_lookup.py`):
   - `select(Order).join(Customer).where(Order.order_id == ...).where(func.lower(Customer.email) == ...)`.
   - Match → build `OrderLookupResponse` (public fields only + `is_simulated=True`).
   - No match (missing order **or** wrong email) → same `LookupResult(not_found=True)`.
5. Route raises `HTTPException(404)` with identical `order_not_found` detail for any not-found case.
6. Response serialization omits customer name, email, address, internal numeric `id`, and notes.

```31:47:app/services/order_lookup.py
def lookup_order(
    db: Session,
    *,
    order_id: str,
    customer_email: str,
) -> LookupResult:
    """Return order details only when order_id and customer_email both match."""
    stmt = (
        select(Order)
        .join(Customer)
        .where(Order.order_id == order_id)
        .where(func.lower(Customer.email) == customer_email.lower())
    )
    order = db.execute(stmt).scalar_one_or_none()
```

---

## E. Database lifecycle

| Concept | Where | Role |
|---------|-------|------|
| **Models** | `app/models/*.py` | Python classes describing tables for the ORM |
| **Migrations** | `alembic/versions/*.py` | Versioned SQL DDL applied by `alembic upgrade head` |
| **Seed data** | `app/seed/data.py` + `run.py` | Fictional rows; idempotent by `email` / `order_id` |
| **Persistent storage** | Compose volume `postgres_data` | Survives `docker compose down` (not `down -v`) |
| **Dev database** | `POSTGRES_DB` (e.g. `supportflow`) | Used by `api` / `migrate` / `seed` |
| **Test database** | `supportflow_test` | Used only by Compose `test` service / pytest |

Tests (`tests/conftest.py`):

- Assert `supportflow_test` appears in `DATABASE_URL`.
- May `DROP SCHEMA public CASCADE` **only** on that test database.
- **Never** reset the development database for tests.

---

## F. Configuration

Environment variables (see `.env.example`; real values live only in ignored `.env`):

| Variable | Purpose |
|----------|---------|
| `APP_ENV` | `development` \| `test` \| `production` (seeding allowed only for the first two) |
| `APP_NAME` | Service name shown in `/health` |
| `POSTGRES_*` | Credentials for the Postgres container |
| `DATABASE_URL` | SQLAlchemy URL (`postgresql+psycopg://…`) |

Networking:

| Caller | Postgres host | API URL from your Mac |
|--------|---------------|------------------------|
| API / migrate / seed containers | `db` (Compose DNS) | — |
| Browser/curl on host | (DB not published) | `http://127.0.0.1:8000` |

Ollama host-vs-container notes remain in `.env.example` for Phase 1.3+; unused now.

**Never commit or paste real passwords.**

---

## G. Code concepts used in these flows

### Imports and app wiring

```python
from fastapi import FastAPI
from app.api.routes import health, orders

app = FastAPI(...)
app.include_router(health.router)
app.include_router(orders.router)
```

### Decorators (routes)

```python
@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    ...
```

`@router.get` / `@router.post` register HTTP handlers. `response_model` controls OpenAPI and response filtering/serialization.

### Type annotations

```python
def create_order_lookup(
    payload: OrderLookupRequest,
    db: Session = Depends(get_db),
) -> OrderLookupResponse:
```

Annotations tell FastAPI how to parse bodies and document responses. Return type + `response_model` keep the public JSON shape tight.

### Dependency injection

`Depends(get_db)` asks FastAPI to call `get_db()`, yield a `Session`, and close it after the request (`app/database.py`).

### Database sessions

```python
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

One session per request in normal API use. Tests override `get_db` via `app.dependency_overrides`.

---

## H. AI status

**There is no model inference and no runtime AI prompt in this phase.**

- No Ollama client calls
- No classification prompts
- No draft-reply generation

Phase 1.2 is HTTP + PostgreSQL + synthetic data only. Local AI via Ollama is **Planned** (Phase 1.3+).

---

## I. Hands-on exercises

Do these **after** Docker works and the stack is up. Do **not** run exercises that intentionally break the app in shared environments without restoring afterward. The agent did **not** execute these (Docker blocked).

### Exercise 1 — Hit `/health` and read the JSON

1. Ensure API is running (`docker compose up -d api`).
2. Run: `curl -sS http://127.0.0.1:8000/health | python3 -m json.tool`
3. **Expected:** HTTP 200; `status` is `"ok"`; `version` is present; no database fields.
4. **Restore:** nothing to restore.

### Exercise 2 — Compare matching vs wrong-email lookup

1. POST matching `SF-1001` + `alex.rivera@example.com` (see README).
2. POST same `order_id` with `nobody@example.com`.
3. **Expected:** first returns 200 with `is_simulated: true`; second returns 404 `order_not_found`.
4. **Restore:** nothing to restore (read-only GETs/POSTs that do not mutate besides reads).

### Exercise 3 — Re-run seed and observe idempotency

1. `docker compose --profile tools run --rm seed` twice.
2. **Expected:** second run reports `orders_created=0` (or equivalent “already present” behaviour); no duplicate `order_id` rows.
3. **Restore:** nothing required; seeder is designed to be re-runnable. Do **not** delete Docker volumes.

---

## Comprehension check (after the health walkthrough below)

See the end of the review report in chat / README for three questions about `/health`.
