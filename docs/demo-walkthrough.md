# Demo walkthrough (recording script)

Target length: **3–4 minutes**. Use synthetic data only.

## Setup before recording

1. Docker API/DB healthy: `curl http://127.0.0.1:8000/ready`
2. Ollama running with `qwen3:1.7b` (or acceptance fixture stack for a dry run)
3. Next.js: `cd frontend && npm run dev` → http://127.0.0.1:3000
4. Browser window ~1280×800; hide bookmarks bar

## Script

1. **Open home** — Say: “SupportFlow AI is a local portfolio demo. The model only classifies; templates write replies; nothing is sent.”
2. **Order status** — Message: `Where is order SF-1001?` Email: `alex.rivera@example.com`. Click **Generate draft**. Point at intent, outcome, human-approval notice.
3. **Open review** — Click **Open in review queue**. Show original message, draft, revision.
4. **Edit + approve** — Edit one sentence, show unsaved warning blocks Approve, Save, then Approve. Show “Approval records a local review decision. Nothing is sent.” and reviewed-text snapshot.
5. **Policy** — New draft: `What is your return window for unused items?` Show policy sources (document / version / section). Say: “Keyword retrieval, not semantic search; fictional demo policy.”
6. **Queue** — Open **Review queue**, filter Pending / Approved.
7. **Close** — “Local single-operator demo: no authentication, no outbound send, classification can be wrong so humans review every reply.”

## Do not claim

- Live courier tracking
- Real merchant/legal policy
- Prompt injection solved
- Production-ready auth or messaging
