"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app import __version__
from app.api.routes import (
    classifications,
    health,
    orders,
    support_drafts,
    support_requests,
)
from app.config import get_settings
from app.schemas.errors import ErrorBody
from app.services.ollama_client import get_ollama_client

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    await get_ollama_client().aclose()


app = FastAPI(
    title=settings.app_name,
    version=__version__,
    lifespan=lifespan,
    description=(
        "SupportFlow AI — synthetic order lookup, local classification, "
        "keyword-grounded fictional policy drafts, and template replies.\n\n"
        "**Limitations:** Email matching is a demo ownership check only, "
        "not production identity verification. Order tracking is simulated "
        "and must never be described as live courier tracking. The model "
        "classifies only; application code retrieves facts/policy sections "
        "and renders drafts. Policy text is fictional demo content (not legal "
        "advice). Keyword retrieval is not semantic search. Every draft "
        "requires human approval before any send (send is not implemented). "
        "Successful drafts are persisted for a local single-operator review "
        "queue (no authenticated reviewer identity). "
        "Classification is advisory, never authorization. "
        "AI availability is not required for `/ready`."
    ),
)

app.include_router(health.router)
app.include_router(orders.router)
app.include_router(classifications.router)
app.include_router(support_drafts.router)
app.include_router(support_requests.router)


@app.middleware("http")
async def no_store_mutable_demo_routes(request: Request, call_next):
    """Prevent stale list/detail caches for review workflows."""
    response = await call_next(request)
    path = request.url.path
    if "/support-requests" in path or "/support-drafts" in path:
        response.headers["Cache-Control"] = "no-store, max-age=0"
    return response


def _serialize_validation_errors(errors: list) -> list[dict]:
    """Make Pydantic error dicts JSON-safe (ctx may contain Exception instances)."""
    serialized: list[dict] = []
    for error in errors:
        item = {key: value for key, value in error.items() if key != "ctx"}
        ctx = error.get("ctx")
        if isinstance(ctx, dict):
            item["ctx"] = {
                key: value if isinstance(value, (str, int, float, bool, type(None))) else str(value)
                for key, value in ctx.items()
            }
        serialized.append(item)
    return serialized


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Return a consistent validation error envelope."""
    return JSONResponse(
        status_code=422,
        content={
            "detail": ErrorBody(
                code="validation_error",
                message="Request validation failed.",
            ).model_dump(),
            "errors": _serialize_validation_errors(exc.errors()),
        },
    )
