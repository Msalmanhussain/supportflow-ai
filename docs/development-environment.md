# Development environment assessment

**Assessed:** 2026-10-18 (Phase 1.1)
**Updated:** 2026-10-21 (Phase 2.3 policy retrieval **implemented**)
**Repo path:** `supportflow-ai/` (clone root)
**Git remote:** `https://github.com/Msalmanhussain/supportflow-ai.git`

## Hardware

| Item | Detected value |
|------|----------------|
| OS | macOS 15.7.7 (Build 24G720) |
| Architecture | `x86_64` (Intel) |
| CPU | Intel Core i7-8850H @ 2.60 GHz |
| Cores | 6 physical / 12 logical |
| RAM | **16 GB** |
| Disk | **~428 GB** available |

## Tools and services

| Tool / service | Status | Classification |
|----------------|--------|----------------|
| Git 2.39.5 | Installed | OK |
| Host Python 3.9.6 | Installed | Not used to run the API |
| Homebrew | Missing (optional) | Not required once Docker Desktop is installed |
| Docker CLI | **Installed** | Docker version **29.8.2** (`Docker.app` Resources/bin) |
| Docker Compose | **Installed** | **v5.6.0** |
| Docker daemon | **Running** | Server Version **29.8.2**, Docker Desktop |
| Node.js (system PATH) | **Missing** initially | Used user-local Node **22.20.0** at `~/.local/node-v22.20.0-darwin-x64` (no system overwrite) |
| npm | Via user-local Node | **10.9.3** |
| Ollama | **Installed** (user-local app, CLI 0.40.7) | Phase 2.1 — host inference; Docker uses `host.docker.internal` |
| Model `qwen3:1.7b` | **Pulled** (~1.4 GB Q4_K_M-class, Apache-2.0) | Digest `8f68893c685c3ddff2aa3fffce2aa60a30bb2da65ca488b61fff134a4d1730e7` |

### Docker verification (2026-10-18)

| Probe | Result |
|-------|--------|
| `docker --version` | 29.8.2 |
| `docker compose version` | v5.6.0 |
| `docker info` (Server) | Reachable |
| Phase 1.2 runtime sequence | **Passed** (see README verification table) |

Note: on this Mac the CLI may live under `/Applications/Docker.app/Contents/Resources/bin` until the shell PATH includes Docker’s symlink.

## Dependency pin re-verification (2026-10-18)

Checked against **PyPI** and **Docker Hub** (existence):

| Pin | Result |
|-----|--------|
| `fastapi==0.143.3` | Exists |
| `uvicorn[standard]==0.54.0` | Exists |
| `pydantic==2.14.1` / `pydantic-settings==2.16.0` | Exists |
| `SQLAlchemy==2.0.55` | Exists (2.0.x line; Alembic requires SQLAlchemy>=2.0) |
| `psycopg[binary]==3.3.6` | Exists |
| `alembic==1.20.0` | Exists |
| `pytest==9.1.1` / `httpx==0.28.1` / related | Exists |
| `python:3.12.15-slim-bookworm` | Exists on Docker Hub |
| `postgres:16.15-bookworm` | Exists on Docker Hub |

Runtime install of these pins inside a container was **not** executed (Docker blocked).

## Local model (Phase 2.1 — selected)

| Item | Choice |
|------|--------|
| Tag | `qwen3:1.7b` |
| Why | Fits 16 GB Intel CPU with Docker + Postgres; instruction model; Ollama JSON `format` + `think: false` |
| Docker note | Default `ollama serve` binds loopback only — use `OLLAMA_HOST=0.0.0.0:11434` for container access (see [ollama-macos-intel.md](ollama-macos-intel.md)). Do not publish the port on a public network. |

## Architecture reminder

Confirmed stack: Next.js + FastAPI + PostgreSQL + Ollama (host). Docker for API/DB. No Express; no n8n/Make.com; no paid cloud inference.
