# Manual install: Ollama on Intel Mac (Phase 2.1+)

SupportFlow AI runs **Ollama on the Mac host** and FastAPI in Docker. This machine is **Intel x86_64** (i7-8850H, 16 GB RAM). Official Ollama macOS builds support Intel Macs; inference is expected to be **CPU-only** unless an experimental Vulkan path is explicitly enabled (not required for this project).

## Selected model

| Item | Value |
|------|--------|
| Tag | `qwen3:1.7b` |
| Quantization | Q4_K_M-class (~1.4 GB download) |
| License | Apache License 2.0 (Ollama library / Qwen) |
| Why | Fits 16 GB Intel CPU with Docker + Postgres concurrent; instruction-tuned; supports Ollama `format` JSON schema and `think: false` |
| Digest (this machine, after pull) | `8f68893c685c3ddff2aa3fffce2aa60a30bb2da65ca488b61fff134a4d1730e7` |

Verify after pull:

```bash
ollama show qwen3:1.7b
curl -sS http://127.0.0.1:11434/api/tags | python3 -m json.tool
```

Model weights live under Ollama’s host store (typically `~/.ollama`). They are **not** committed; `.gitignore` excludes `models/`, `*.gguf`, `.ollama/`, `ollama-models/`.

## Install steps (you must complete)

1. Download the official macOS app:
   [https://ollama.com/download](https://ollama.com/download)
   Direct zip:
   [https://ollama.com/download/Ollama-darwin.zip](https://ollama.com/download/Ollama-darwin.zip)
2. Unzip and drag **Ollama.app** into **Applications** (or a user Applications folder).
3. Launch **Ollama** from Applications (accept any first-run prompts / admin password yourself).
4. Confirm the local API:

```bash
export PATH="$HOME/Applications/Ollama.app/Contents/Resources:/Applications/Ollama.app/Contents/Resources:$PATH"
ollama --version
curl -sS http://127.0.0.1:11434/api/tags
```

5. Pull **one** project model only:

```bash
ollama pull qwen3:1.7b
```

## Docker Desktop networking — narrowest practical access

Compose already sets:

- `OLLAMA_BASE_URL=http://host.docker.internal:11434`
- `extra_hosts: host.docker.internal:host-gateway`

Official Docker Desktop guidance: containers reach host services via `host.docker.internal` ([Docker Desktop networking](https://docs.docker.com/desktop/features/networking/networking-how-tos/)).

### Preferred (narrow): Ollama on loopback only

Bind Ollama to **`127.0.0.1:11434`** (default, or explicit `OLLAMA_HOST=127.0.0.1:11434`). That keeps the API off LAN interfaces.

**Verified on this Mac (2026-10-21, Docker Desktop):** a container using `host.docker.internal:11434` received **HTTP 200** while Ollama listened only on `127.0.0.1:11434` (`lsof` showed `TCP 127.0.0.1:11434`). Prefer this configuration.

```bash
# Explicit loopback (narrowest practical for this project)
OLLAMA_HOST=127.0.0.1:11434 ollama serve

# Probe from a throwaway container (same pattern as Compose):
docker run --rm --add-host=host.docker.internal:host-gateway curlimages/curl:8.5.0 \
  -sS -o /dev/null -w "%{http_code}\n" --connect-timeout 3 \
  http://host.docker.internal:11434/api/tags
```

- If the container prints **`200`**, stay on loopback.
- If connection refused / `000`, Docker Desktop on that host/build is not reaching loopback via `host.docker.internal`. Only then consider the wider workaround below.

### Workaround (wider — avoid if loopback probe works): bind `0.0.0.0`

```bash
OLLAMA_HOST=0.0.0.0:11434 ollama serve
```

**Honest exposure note:** Binding `0.0.0.0:11434` makes Ollama listen on **all host interfaces**, including typical LAN addresses (for example Wi‑Fi/`en0`). **Absence of Docker/router port-forwarding does not prevent LAN access** — any device on the same network that can reach this Mac’s LAN IP on port 11434 may call the unauthenticated Ollama HTTP API. Do not claim “local only” while bound to `0.0.0.0`.

Earlier Phase 2.1 work sometimes used `0.0.0.0` when connectivity failed; re-check the loopback probe before keeping that bind.

Mitigations (manual; this project does **not** change host firewall rules automatically):

- Prefer the loopback path when the container probe succeeds.
- When `0.0.0.0` is required: use a trusted network only; consider macOS firewall / `pf` rules yourself; disconnect from untrusted LANs; stop `ollama serve` when idle.
- Alternatives (narrower than `0.0.0.0`, more ops work): run the API on the host instead of Docker for inference; or run Ollama in the same Compose network **without** publishing `11434` (architecture change; not the default for this repo).

Do **not** publish Ollama on a public cloud ingress or home-router WAN port forward.

## Out of scope

- Accepting licenses or admin prompts for you
- Using `sudo` or auto-editing firewall rules
- Downloading multiple/alternate cloud models
