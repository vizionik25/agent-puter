<div align="center">

<img width="80" src="https://em-content.zobj.net/source/apple/391/high-voltage_26a1.png" alt="logo" />

# Agent-Puter

**Autonomous AI Consulting Agency — Business in a Box**

*A fully autonomous AI consulting agency powered by a swarm of specialized LLM agents, a Starlette REST API, and a Next.js client portal with a subscription-credit billing model.*

[![Python](https://img.shields.io/badge/Python-3.14+-3776ab?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Next.js](https://img.shields.io/badge/Next.js-16-black?style=flat-square&logo=next.js)](https://nextjs.org)
[![PyPI](https://img.shields.io/pypi/v/agent-puter?style=flat-square&logo=pypi&logoColor=white&color=006dad)](https://pypi.org/project/agent-puter/)
[![License: MIT](https://img.shields.io/badge/License-MIT-violet?style=flat-square)](LICENSE)
[![uv](https://img.shields.io/badge/package%20manager-uv-orange?style=flat-square)](https://github.com/astral-sh/uv)

</div>

---

## What is Agent-Puter?

Agent-Puter is a self-contained, production-ready AI consulting agency platform. A client visits the portal, describes their project in plain English, receives an AI-generated proposal, and uses subscription credits to kick off the autonomous agent swarm. A team of specialized AI agents handles everything — research, engineering, QA — then delivers a live demo.

```
Client visits portal
      │
      ▼
/consult  ←── Sales Agent (live AI chat, scopes the project)
      │
      ▼
/proposal ←── Proposal (problem/solution, plan, ETA, credit cost)
      │
      ▼
Execute with credits ←── Deduct credits from subscription balance
      │
      ▼  ← Agent Swarm kicks off autonomously ──────────────────────┐
      │                                                               │
      │  CEO ──► PM ──► Engineer / Researcher ──► QA ──► CEO approves│
      │                                                               │
      ◄───────────────────────────────────────────────────────────────┘
      │
      ▼
/demo  ←── Auto-deployed sandbox delivery
      │
      ▼
/status ←── Real-time task progress tracker (auto-refreshes every 8s)
```

---

## Architecture

Three components, one `docker compose up`:

```
┌─────────────────────────────────────────────────┐
│  frontend/          Next.js 16  (port 3000)      │
│  ├── /                Landing page               │
│  ├── /consult         AI consultation chat (SSE) │
│  ├── /dashboard       User dashboard & projects  │
│  ├── /proposal/[id]   Proposal + credit CTA      │
│  ├── /billing         Subscription & credit mgmt │
│  ├── /demo/[id]       Sandbox demo viewer        │
│  └── /status/[id]     Live progress tracker      │
│                                                  │
│  lib/api.ts           Typed REST API client      │
│  lib/auth.ts          GitHub OAuth session       │
│  lib/billing.ts       Client-side billing mock   │
└─────────────────────┬───────────────────────────┘
                      │  REST / JSON
                      ▼
┌─────────────────────────────────────────────────┐
│  src/agent_puter/swarm/   Starlette  (port 9999) │
│                                                  │
│  ── Client API ──────────────────────────────── │
│  GET  /api/auth/github                           │
│  GET  /api/auth/callback                         │
│  GET  /api/auth/me                               │
│  POST /api/auth/logout                           │
│  POST /api/consult/start                         │
│  POST /api/consult/{id}/message                  │
│  POST /api/consult/{id}/stream      (SSE)        │
│  GET  /api/consult/{id}                          │
│  POST /api/consult/{id}/complete                 │
│  GET  /api/projects                              │
│  GET  /api/projects/{id}                         │
│  GET  /api/projects/{id}/proposal                │
│  POST /api/projects/{id}/demo-url                │
│  GET  /api/projects/{id}/demo                    │
│  GET  /api/projects/{id}/usage                   │
│  POST /api/projects/{id}/push-github             │
│  POST /api/payments/deposit                      │
│  POST /api/payments/final                        │
│  POST /api/payments/webhook                      │
│  GET  /api/payments/{id}/status                  │
│  GET  /api/admin/*   (X-Admin-Key required)      │
│                                                  │
│  ── Agent A2A Endpoints ─────────────────────── │
│  /              CEO Agent (root)                 │
│  /sales/*       Sales Agent                      │
│  /pm/*          Project Manager                  │
│  /product-manager/* Product Manager Agent        │
│  /researcher/*  Researcher                       │
│  /engineer/*    Engineer                         │
│  /qa/*          QA Agent                         │
│  /deliveries/*  Static sandbox files             │
└─────────────────────────────────────────────────┘
```

---

## The Agent Swarm

Seven specialized agents, each a self-contained A2A ASGI app:

| Agent | Mount | Role | Key Tools |
|---|---|---|---|
| CEO | `/` | Strategic goals, token budgets, final approval | `allocate_budget`, `approve_delivery`, `publish_goal` |
| Sales | `/sales` | Client intake, project brief creation | `create_project_brief`, `send_proposal` |
| PM | `/pm` | Task decomposition, milestone tracking | `create_task_list`, `update_task_status` |
| Product Manager | `/product-manager` | User stories, acceptance criteria | `write_user_stories`, `prioritize_features` |
| Researcher | `/researcher` | Web research, document summarization | `web_search`, `summarize_docs` |
| Engineer | `/engineer` | Code generation, file I/O, sandbox deploy | `write_file`, `read_file`, `run_tests`, `deploy_to_sandbox` |
| QA | `/qa` | Output review, PASS/FAIL verdicts | `review_output`, `check_standards` |

All inter-agent calls use the **A2A protocol** (HTTP via `fasta2a.A2AClient`). No direct Python `.run()` calls between agents — every agent is addressed only by its mounted HTTP URL.

---

## Subscription & Credit Model

Project execution is billed in credits drawn from a subscription balance. All billing state is managed client-side via `localStorage` (frontend mock — no backend billing calls).

### Plans

| Plan | Price | Credits / Month |
|---|---|---|
| Free | $0 | 0 — purchase credits to execute |
| Starter | $49/month | 30 |
| Pro | $149/month | 100 |
| Business | $399/month | 300 |

Credits roll over; they do not expire. Monthly grants accumulate on top of your existing balance.

### Credit Packs (paid plans only)

Top-up credits are available on Starter, Pro, and Business plans. The Free tier cannot purchase packs.

| Pack | Credits | Price |
|---|---|---|
| Starter pack | 10 | $12 |
| Standard pack | 30 | $32 |
| Power pack | 100 | $99 |

### Per-Million Token Pricing

Credits are calculated from the proposal's estimated hours using the same per-million-token structure as LLM providers:

| Token type | Rate |
|---|---|
| Input tokens | 3 credits / 1M tokens |
| Output tokens | 15 credits / 1M tokens |
| Throughput estimate | 75,000 tokens / hour of agent work |
| Input/output ratio | 70% input, 30% output |

Formula: `totalCredits = (inputTokens / 1M × 3) + (outputTokens / 1M × 15)`

---

## Quick Start

### Prerequisites

- [uv](https://github.com/astral-sh/uv) — Python package manager
- Node.js 20+ and npm
- A [Puter.js](https://puter.com) account for free LLM inference (or any OpenAI-compatible API)
- A [Stripe](https://stripe.com) account (test keys work fine)
- A [GitHub OAuth App](https://github.com/settings/developers) *(optional — required for the login button and GitHub delivery features)*

### 1. Clone and configure

```bash
git clone https://github.com/vizionik25/agent-puter.git
cd agent-puter
cp .env.example .env
# Edit .env: fill in PUTER_AUTH_TOKEN, PUTER_MODEL, PUTER_API_BASE,
#             Stripe keys, and (optional) GitHub OAuth vars
```

> **GitHub login (optional):** Create an OAuth App at [github.com/settings/developers](https://github.com/settings/developers). Set the callback URL to `http://localhost:3000/api/auth/callback`. Copy the client ID and secret into `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` in `.env`. Set `SESSION_SECRET` to any strong random string.

### 2. Start the backend

```bash
uv sync
uv run agent-puter
# → http://localhost:9999
# → http://localhost:9999/health   (swarm status)
# → http://localhost:9999/docs     (CEO agent interactive docs)
```

Or install from PyPI and run globally:

```bash
uv tool install agent-puter
agent-puter
```

### 3. Start the frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

### 4. (Optional) Stripe webhook for local testing

```bash
stripe listen --forward-to localhost:9999/api/payments/webhook
```

### Docker — full stack

```bash
cp .env.example .env   # fill in secrets
docker compose up --build -d
# Frontend: http://localhost:3000
# Backend:  http://localhost:9999
```

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `PUTER_AUTH_TOKEN` | Yes | — | Puter.js session token (used as LLM API key) |
| `PUTER_MODEL` | Yes | — | LiteLLM model string, e.g. `openai/claude-sonnet-4-5` |
| `PUTER_API_BASE` | Yes | — | LLM endpoint, e.g. `https://api.puter.com/puterai/openai/v1` |
| `STRIPE_SECRET_KEY` | No | — | Stripe secret key (`sk_test_...`) |
| `STRIPE_PUBLISHABLE_KEY` | No | — | Stripe publishable key (`pk_test_...`) |
| `STRIPE_WEBHOOK_SECRET` | No | — | Stripe webhook signing secret (`whsec_...`) |
| `NEXT_PUBLIC_API_URL` | No | `""` | Frontend → backend URL. Empty = relative `/api/*` (Docker). Set to `http://localhost:9999` for local dev. |
| `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` | No | — | Stripe publishable key for frontend Stripe Elements |
| `STORAGE_BACKEND` | No | `memory` | `memory`, `json_file`, or `puter_kv` |
| `STORAGE_PATH` | No | `./data/store.json` | Path for `json_file` backend |
| `PUTER_KV_BASE` | No | `https://api.puter.com/kv` | Override for `puter_kv` backend endpoint |
| `ADMIN_API_KEY` | No | — | Protects all `/api/admin/*` routes. Unset = admin disabled. |
| `AGENCY_API_KEYS` | No | — | Multi-tenancy: `key1:tenant1,key2:tenant2` |
| `SMTP_HOST` | No | — | SMTP server for email notifications |
| `SMTP_PORT` | No | `587` | SMTP port |
| `SMTP_USER` | No | — | SMTP login |
| `SMTP_PASS` | No | — | SMTP password or app password |
| `FROM_EMAIL` | No | `SMTP_USER` | Sender address for notifications |
| `FRONTEND_URL` | No | `http://localhost:3000` | Base URL for email action links |
| `GITHUB_CLIENT_ID` | No | — | GitHub OAuth App client ID. Required for GitHub login. |
| `GITHUB_CLIENT_SECRET` | No | — | GitHub OAuth App client secret. Required for GitHub login. |
| `SESSION_SECRET` | No | random | HMAC key for signing session tokens. Set to a strong random string in production. |
| `MCP_SERVER_URL` | No | — | MCP server URL; enables MCP tools on Researcher + Engineer |

---

## Project Structure

```
agent-puter/
├── src/agent_puter/
│   ├── __init__.py
│   ├── agent-logic-example.py       Single-agent reference example
│   └── swarm/
│       ├── main.py                  Starlette app — mounts agents + API
│       ├── server.py                uvicorn launcher
│       ├── agency.py                Agency orchestrator (business loop)
│       ├── models.py                Pydantic data models
│       ├── base_agent.py            LiteLLMModel factory
│       ├── middleware.py            Multi-tenancy (X-Agency-Key)
│       ├── notifications.py         SMTP email notifications
│       ├── ceo_agent.py
│       ├── sales_agent.py
│       ├── pm_agent.py
│       ├── product_manager_agent.py
│       ├── researcher_agent.py
│       ├── engineer_agent.py
│       ├── qa_agent.py
│       └── api/
│           ├── __init__.py          Aggregates all API routes
│           ├── _store.py            Legacy alias (delegates to store.py)
│           ├── store.py             Pluggable storage backends
│           ├── auth.py              /api/auth/* routes (GitHub OAuth)
│           ├── consultation.py      /api/consult/* routes
│           ├── github_delivery.py   Push deliverables to GitHub repo
│           ├── projects.py          /api/projects/* routes
│           ├── payments.py          /api/payments/* routes
│           └── admin.py             /api/admin/* routes
│
├── frontend/
│   ├── app/
│   │   ├── layout.tsx               Root layout + nav + UserMenu
│   │   ├── page.tsx                 Landing page
│   │   ├── consult/page.tsx         Consultation chat (SSE streaming)
│   │   ├── dashboard/page.tsx       User dashboard & project management
│   │   ├── proposal/[id]/page.tsx   Proposal + credit execution CTA
│   │   ├── billing/page.tsx         Subscription & credit management
│   │   ├── demo/[id]/page.tsx       Sandbox demo viewer
│   │   └── status/[id]/page.tsx     Real-time task progress
│   ├── components/
│   │   ├── UserMenu.tsx             GitHub auth nav menu + dropdown
│   │   └── MockStripeModal.tsx      Simulated payment modal
│   ├── lib/
│   │   ├── api.ts                   Typed REST client
│   │   ├── auth.ts                  GitHub OAuth session helpers
│   │   └── billing.ts               Client-side billing (localStorage)
│   └── next.config.ts               Standalone output mode
│
├── Dockerfile                       Backend multi-stage build
├── frontend/Dockerfile              Frontend multi-stage build (Node 22)
├── docker-compose.yml               Full stack
├── docker-compose.backend.yml       Backend only
├── pyproject.toml
└── .env.example
```

---

## Docs

- [Architecture](docs/architecture.md) — system design, agent communication, data flow, storage
- [API Reference](docs/api-reference.md) — every endpoint with request/response tables
- [Getting Started](docs/getting-started.md) — local dev setup, first consultation walkthrough
- [Deployment](docs/deployment.md) — Docker Compose, environment reference, Stripe production

---

## License

MIT © 2026 Charles Nichols — [vizionikmedia.com](https://vizionikmedia.com)
