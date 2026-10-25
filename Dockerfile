# SupportFlow AI API — Python 3.12 (pinned, not latest)
FROM python:3.12.15-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTEST_ADDOPTS="-o cache_dir=/tmp/pytest_cache"

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 1000 appuser \
    && useradd --system --uid 1000 --gid appuser --create-home appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app
COPY tests ./tests
COPY pyproject.toml .
# app/prompts and app/policy_docs are included via COPY app (fixed app-owned paths).

RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# Secrets must come from runtime env / Compose — not baked into the image.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
