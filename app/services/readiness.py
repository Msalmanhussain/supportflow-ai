"""Database connectivity and Alembic migration readiness checks."""

from dataclasses import dataclass
from pathlib import Path

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.engine import Engine


@dataclass(frozen=True)
class ReadinessResult:
    ready: bool
    database: str
    migrations: str
    detail: str | None = None


def _alembic_config() -> Config:
    root = Path(__file__).resolve().parents[2]
    return Config(str(root / "alembic.ini"))


def check_readiness(engine: Engine) -> ReadinessResult:
    """Verify DB connectivity and that the schema is at Alembic head."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            script = ScriptDirectory.from_config(_alembic_config())
            heads = set(script.get_heads())
            context = MigrationContext.configure(connection)
            current = set(context.get_current_heads())

            if not heads:
                return ReadinessResult(
                    ready=False,
                    database="ok",
                    migrations="missing",
                    detail="No Alembic migration heads found in the repository.",
                )
            if current != heads:
                return ReadinessResult(
                    ready=False,
                    database="ok",
                    migrations="pending",
                    detail=(
                        f"Database revision(s) {sorted(current) or ['(none)']} "
                        f"do not match head(s) {sorted(heads)}."
                    ),
                )
            return ReadinessResult(
                ready=True,
                database="ok",
                migrations="current",
                detail=None,
            )
    except Exception as exc:  # noqa: BLE001 — surface as readiness failure
        return ReadinessResult(
            ready=False,
            database="unavailable",
            migrations="unknown",
            detail=str(exc.__class__.__name__),
        )
