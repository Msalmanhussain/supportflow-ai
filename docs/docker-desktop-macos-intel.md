# Manual install: Docker Desktop for Intel Mac

Phase 1.2 requires **Docker Engine + Compose**. This machine had **no Homebrew** and **no Docker** at assessment time. The agent cannot accept Docker’s license or complete a graphical installer on your behalf.

## Recommended distribution

**Docker Desktop for Mac (Intel / AMD64)** — official build matching this `x86_64` Mac.

## Steps (you must complete these)

1. Open the official download page:
   [https://docs.docker.com/desktop/setup/install/mac-install/](https://docs.docker.com/desktop/setup/install/mac-install/)
2. Download **Docker Desktop for Mac – Intel Chip** (AMD64), not Apple Silicon.
   Direct DMG (Intel):
   [https://desktop.docker.com/mac/main/amd64/Docker.dmg](https://desktop.docker.com/mac/main/amd64/Docker.dmg)
3. Open the DMG and drag **Docker** to **Applications**.
4. Launch **Docker** from Applications.
5. Complete the first-run wizard:
   - Accept the **Docker Subscription Service Agreement** yourself if prompted.
   - Grant any **administrator** password prompts macOS shows for privileged helpers.
   - Allow requested **system permissions** (network, etc.) in System Settings if asked.
6. Wait until the menu-bar whale shows **Docker Desktop is running**.
7. Verify in Terminal:

```bash
docker --version
docker compose version
docker info
```

All three should succeed without connection errors.

## Optional: Homebrew (not required if Desktop DMG works)

Homebrew was **not** installed on this machine. Installing Homebrew also requires interactive steps and may prompt for an administrator password. Prefer the Docker Desktop DMG above unless you already use Homebrew.

## After Docker works

Return to the [README](../README.md) Phase 1.2 commands: generate `.env`, `docker compose build`, migrate, seed, run, and test.

## Out of scope for the agent

- Using `sudo`
- Accepting Docker license terms for you
- Changing macOS security settings
- Overwriting an existing Docker installation (none was present)
