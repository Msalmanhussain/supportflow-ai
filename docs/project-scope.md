# Project scope — SupportFlow AI (MVP)

## Purpose

Build a **portfolio** demonstration of local AI customer-support automation: classify requests, retrieve synthetic store data, draft replies, and require human approval before any customer-facing send.

## Confirmed product architecture

| Layer | Choice |
|-------|--------|
| Frontend | **Next.js + TypeScript** (Phase 1.3 in `frontend/`) |
| Backend | **Python + FastAPI** (Phase 1.2) |
| Database | **PostgreSQL** |
| Local AI (later) | **Ollama** with downloadable free model weights |
| Dev infrastructure | **Docker Compose** for API/DB; Next.js on the host for Phase 1.3 |

Explicitly **not** part of the initial implementation:

- No separate Express backend
- No **n8n** or **Make.com** dependency
- No paid AI APIs or cloud inference

Early Phase 1.1 notes mentioned n8n as a candidate orchestrator; the confirmed architecture above **supersedes** that for the initial build. History is preserved in older commits/docs wording only where noted as outdated.

## Other confirmed decisions

- Initial business data: **synthetic** orders and store policies.
- Customer replies require **human approval**.
- Never claim simulated order tracking is **live courier tracking**.

## In scope (MVP)

1. **Order-status enquiries** — answer using synthetic order records only, after ownership verification.
2. **Policy questions** — answer from synthetic store policy content (retrieval planned in later phases).
3. **Missing-information handling** — detect incomplete requests and draft clarifying questions.
4. **Refund-request escalation** — classify refund intent and escalate; do **not** process refunds.

## Explicitly out of scope (MVP)

- Actual refunds, chargebacks, or payment mutations
- Real courier / carrier API integrations
- Automatic sending of messages to external channels without a human approval step
- Production multi-tenant SaaS, billing, or real PII pipelines

## Access control for order data

Knowing an **order ID alone must not authorize access**.

Before exposing order details, the system must verify **customer ownership** using at least one additional factor tied to the synthetic customer record (for Phase 1.2: matching `customer_email`).

**Documentation note:** Email matching in Phase 1.2 is a **demonstration ownership check only**, not production authentication or identity verification.

## Data policy (development)

- Use **only synthetic** customer, order, and policy data during development and demos.
- Do not import real customer databases or production exports into this project.

## Honesty in demos and copy

- Label data and tracking as **simulated** where relevant.
- Do not present portfolio results as production courier tracking or live retail operations.

## Success criteria for MVP (target; not yet met)

- Local stack can classify a small set of request types.
- Verified order-status and policy flows produce **draft** replies.
- Refund intents escalate without executing refunds.
- A human must approve before a reply is treated as sendable.
- Documentation states what is simulated vs. live.
