<div align="center">

<img width="80" src="https://em-content.zobj.net/source/apple/391/high-voltage_26a1.png" alt="logo" />

# Agent-Puter

**AI Agency Business in a Box**

*A fully autonomous AI consulting agency — from brief to delivery — powered by a swarm of specialized LLM agents, a Starlette REST API, and a Next.js client portal with Stripe payments.*

[![Python](https://img.shields.io/badge/Python-3.14+-3776ab?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Next.js](https://img.shields.io/badge/Next.js-16-black?style=flat-square&logo=next.js)](https://nextjs.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-violet?style=flat-square)](LICENSE)
[![uv](https://img.shields.io/badge/package%20manager-uv-orange?style=flat-square)](https://github.com/astral-sh/uv)

</div>

---

## What is Agent-Puter?

Agent-Puter is a **self-contained, production-ready AI consulting agency** you can run on your own server. A client visits the portal, describes their project in plain English, receives an AI-generated proposal with a fixed price, pays a 20% deposit, and the agent swarm autonomously does the work — research, engineering, QA — then hands over a live demo. The client reviews and pays the 80% balance. You collect revenue without writing a single line of project code yourself.

```
Client visits portal
      │
      ▼
/consult  ←── Sales Agent (live AI chat, scopes the project)
      │
      ▼
/proposal ←── Proposal (problem/solution, plan, ETA, fixed price)
      │
      ▼
/pay/deposit ←── Stripe — 20% deposit
      │
      ▼  ← Agent Swarm kicks off autonomously ─────────────────────────┐
      │                                                                  │
      │  CEO ──► PM ──► Engineer / Researcher ──► QA ──► CEO approves  │
      │                                                                  │
      ◄──────────────────────────────────────────────────────────────────┘
      │
      ▼
/demo  ←── Live demo (iframe or link)
      │
      ▼
/pay/final ←── Stripe — 80% balance → full delivery
      │
      ▼
/status ←── Real-time progress tracker (auto-refreshes)
```

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│  frontend/          Next.js 16  (port 3000)      │
│  ├── /                Landing page               │
│  ├── /consult         AI consultation chat       │
│  ├── /proposal/[id]   Proposal viewer            │
│  ├── /pay/[id]/deposit  Stripe 20% deposit       │
│  ├── /pay/[id]/final    Stripe 80% balance       │
│  ├── /demo/[id]       Demo viewer (gated)        │
│  └── /status/[id]     Live progress tracker      │
│                                                  │
│  lib/api.ts           Typed REST API client      │
└─────────────────────┬───────────────────────────┘
                      │  REST / JSON
                      ▼
┌─────────────────────────────────────────────────┐
│  src/agent_puter/swarm/   Starlette  (port 9999) │
│                                                  │
│  ── Client API ──────────────────────────────── │
│  POST /api/consult/start                         │
│  POST /api/consult/{id}/message                  │
│  GET  /api/consult/{id}                          │
│  POST /api/consult/{id}/complete                 │
│  GET  /api/projects/{id}                         │
│  GET  /api/projects/{id}/proposal                │
│  POST /api/projects/{id}/demo-url                │
│  GET  /api/projects/{id}/demo                    │
│  POST /api/payments/deposit                      │
│  POST /api/payments/final                        │
│  POST /api/payments/webhook                      │
│  GET  /api/payments/{id}/status                  │
│                                                  │
│  ── Agent A2A Endpoints ─────────────────────── │
│  /          CEO   (root A2A + docs)              │
│  /sales/*   Sales Agent                          │
│  /pm/*      Project Manager                      │
│  /researcher/* Researcher                        │
│  /engineer/*   Engineer                          │
│  /qa/*         QA Agent                          │
└─────────────────────────────────────────────────┘
```

---

## The Agent Swarm

| Agent | Role | Key Tools |
|---|---|---|
| 🧠 **CEO** | Strategic goals, token budgets, final approval | `allocate_budget`, `approve_delivery` |
| 💼 **Sales** | Client intake, scope clarification, project brief | `create_project_brief`, `send_proposal` |
| 📋 **PM** | Task decomposition, milestone tracking | `create_task`, `update_task_status` |
| 🔬 **Researcher** | Web research, document summarization | `web_search`, `summarize_document` |
| 🛠️ **Engineer** | Code generation, file I/O, test execution | `write_file`, `read_file`, `run_command` |
| ✅ **QA** | Output review, standards enforcement | `review_output`, `check_standards` |

All agents are built on the same pattern, this is a must for the LiteLLMModel from pydantic-ai-litellm to work with Puter.js if you arent using Puter.js you can alter the pattern to fit your needs. **NOTE**  pydantic-ai-litellm already handles the OpenAI tool spec conversion for you, so if you are not using an OpenAI compatible API you dont have to worry about the tool spec conversion as its automatically handled. This is the main reason for choosing this method of integrating LiteLLM with pydantic-ai, over the native method from the pydantic-ai team.:

```python
from pydantic_ai import Agent
from dotenv import load_dotenv
from pydantic_ai_litellm import LiteLLMModel
import os
import asyncio

load_dotenv()

async def main():
    """This is the main function that will be called by the Puter agent."""

model = LiteLLMModel(
    model_name=os.getenv("PUTER_MODEL"),
    api_key=os.getenv("PUTER_AUTH_TOKEN"),
    api_base=os.getenv("PUTER_API_BASE"),
    custom_llm_provider="openai"
)

agent = Agent(
    model=model,
    instructions='Be helpful!'
)

@agent.tool_plain
def get_weather(city: str) -> str:
    """Get weather for a city."""
    return f"Weather in {city}: Sunny, 72°F"

@agent.tool_plain  
def calculator(expression: str) -> str:
    """Evaluate a math expression."""
    return str(eval(expression))

# Each agent owns its A2A ASGI app — called inside the agent file itself.
# main.py imports and mounts these; it does NOT call .to_a2a() itself.
app = agent.to_a2a(name="My Agent", url="http://localhost:9999/myagent",
                   description="What this agent does.")

# --- Inter-agent communication uses A2AClient (fasta2a) ---
# agency.py dispatches ALL agent calls via HTTP, never via .run() directly.
from fasta2a.client import A2AClient

async def call_pm(prompt: str) -> str:
    client = A2AClient(base_url="http://localhost:9999/pm")
    response = await client.send_message(message={
        "role": "user", "kind": "message",
        "messageId": "<uuid>",
        "parts": [{"kind": "text", "text": prompt}],
    })
    # result is Task.status.message.parts or Message.parts
    ...
```

### Agency Loop

All inter-agent calls go through the **A2A protocol** via `fasta2a.client.A2AClient`.
No direct `.run()` calls — every agent is addressed by its mounted HTTP URL.

```
Client request
  └─► Sales Agent          (A2A → POST /sales/)
        └─► CEO Agent       (A2A → POST /)
              └─► PM Agent  (A2A → POST /pm/)
                    └─► For each task:
                          Engineer or Researcher  (A2A → POST /engineer/ or /researcher/)
                            └─► QA Agent         (A2A → POST /qa/)
                                  ├─ PASS → next task
                                  └─ FAIL → retry (max 5) → CEO escalates (A2A → POST /)
                    └─► CEO approves delivery     (A2A → POST /)
```

---

## Tech Stack

### Backend

| Library | Purpose |
|---|---|
| [`pydantic-ai`](https://github.com/pydantic/pydantic-ai) | Agent framework with type-safe tool definitions |
| [`litellm`](https://github.com/BerriAI/litellm) | Universal LLM gateway (OpenAI, Gemini, Anthropic, Puter, …) |
| [`pydantic-ai-litellm`](https://github.com/mochow13/pydantic-ai-litellm) | LiteLLMModel for integrating LiteLLM with pydantic-ai plus bridges the gap between pydantic-ai and puter.js |
| [`fasta2a`](https://github.com/pydantic/pydantic-ai) | Pydantic's very own implementation of the Agent-to-Agent (A2A) protocol for inter-agent HTTP |
| [`starlette`](https://www.starlette.io) | Lightweight ASGI framework for the REST API |
| [`uvicorn`](https://www.uvicorn.org) | ASGI server |
| [`stripe`](https://stripe.com/docs/api) | Stripe SDK for PaymentIntents and webhooks |
| [`puter-python-sdk`](https://puter.com) | Puter cloud platform integration (AI) |

### Frontend

| Library | Purpose |
|---|---|
| [Next.js 16](https://nextjs.org) | React app router, SSR, API proxy rewrites |
| [`@stripe/react-stripe-js`](https://stripe.com/docs/stripe-js) | Stripe Elements embedded payment forms |
| [`lucide-react`](https://lucide.dev) | Icon library |
| Tailwind CSS | Design system — dark navy + violet, glassmorphism cards |

---

## Quick Start

### Prerequisites

- [uv](https://github.com/astral-sh/uv) — Python package manager
- Node.js ≥ 20 and npm (use [nvm](https://github.com/nvm-sh/nvm))
- A [Stripe](https://stripe.com) account (test keys work fine)
- A FREE puter.js Auth Token to take advantage of Puter's free inference

### 1. Clone & install

```bash
git clone https://github.com/vizionik25/agent-puter.git
cd agent-puter
uv sync
```

### 2. Configure environment

Create a `.env` file in the project root:

```env
# LLM — use Puter's free inference:
PUTER_AUTH_TOKEN=your-puterjs-token
# obtain your token here: https://puter.com/dashboard#account
# you can refer to https://docs.puter.com/playground/ai-list-model-providers/ for the full
# list of models to use
# but I recomend to stay well away from Gemini 3 Pro models, they are not very good at 
# following instructions and are prone to hallucinations. I have had the best results with 
# Claude Sonnet 4.5, 4.6, 4.7 and Opus 4.7. Most model providers still use the OpenAI API
# formatwhich is the reason for 'openai/' in the model name and in the url.
PUTER_MODEL=openai/claude-sonnet-4-5
PUTER_API_BASE=https://api.puter.com/puterai/openai/v1

## Or if you perfer to use another provider just change the model and api base to match your
## provider or another OpenAI compatible API.

# Stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Frontend
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...
NEXT_PUBLIC_API_URL=http://localhost:9999
```

### 3. Start the backend (agent swarm + API)

```bash
uv run agent-puter
# → http://localhost:9999
# → http://localhost:9999/docs  (CEO Agent interactive docs)
# → http://localhost:9999/health
```

Or directly with uvicorn:

```bash
uvicorn agent_puter.swarm.main:app --host 0.0.0.0 --port 9999 --reload
```

### 4. Start the frontend

```bash
cd frontend
npm install   # first time only
npm run dev
# → http://localhost:3000
```

### 5. Configure Stripe webhook (local dev)

```bash
# Install Stripe CLI: https://stripe.com/docs/stripe-cli
stripe listen --forward-to http://localhost:9999/api/payments/webhook
```

---

## Project Structure

```
agent-puter/
├── src/agent_puter/
│   ├── __init__.py              Entry point
│   ├── agent-logic-example.py                 Single-agent example (reference)
│   └── swarm/
│       ├── main.py              Starlette app — mounts all agents + API
│       ├── server.py            uvicorn launcher
│       ├── agency.py            Agency orchestrator (business loop)
│       ├── models.py            Pydantic data models (Project, Proposal, Task, …)
│       ├── base_agent.py        LiteLLMModel factory (shared by all agents)
│       ├── ceo_agent.py         CEO Agent
│       ├── sales_agent.py       Sales & Intake Agent
│       ├── pm_agent.py          Project Manager Agent
│       ├── researcher_agent.py  Researcher Agent
│       ├── engineer_agent.py    Engineer Agent
│       ├── qa_agent.py          QA Agent
│       └── api/
│           ├── __init__.py      Aggregates all API routes
│           ├── _store.py        In-memory session/project store
│           ├── consultation.py  /api/consult/* routes
│           ├── projects.py      /api/projects/* routes
│           └── payments.py      /api/payments/* routes (Stripe)
│
├── frontend/                    Next.js 16 client portal
│   ├── app/
│   │   ├── layout.tsx           Root layout + nav
│   │   ├── globals.css          Design system (dark navy + violet)
│   │   ├── page.tsx             Landing page
│   │   ├── consult/page.tsx     AI consultation chat
│   │   ├── proposal/[id]/       Proposal viewer
│   │   ├── pay/[id]/deposit/    Stripe 20% deposit
│   │   ├── pay/[id]/final/      Stripe 80% balance
│   │   ├── demo/[id]/           Demo viewer (gated)
│   │   └── status/[id]/         Live progress tracker
│   ├── lib/api.ts               Typed REST API client
│   └── next.config.ts           API proxy → localhost:9999
│
├── pyproject.toml
├── .env                         ← create this (not committed)
└── README.md
```

---

## API Reference

### Consultation

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/consult/start` | Start a session. Body: `{client_name, client_email, initial_message}`. Returns `{session_id, reply, status}` |
| `POST` | `/api/consult/{id}/message` | Send a follow-up message. Body: `{message}`. Returns `{reply, status, project_id?}` |
| `GET` | `/api/consult/{id}` | Fetch full session transcript |
| `POST` | `/api/consult/{id}/complete` | **Required** — marks session complete, kicks off agency loop, creates Project + Proposal. Returns `{session_id, project_id, status}` |

### Projects

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/projects/{id}` | Project status, tasks, payment flags |
| `GET` | `/api/projects/{id}/proposal` | Full proposal (pricing, plan, deliverables) |
| `POST` | `/api/projects/{id}/demo-url` | Admin: set demo URL. Body: `{demo_url}` |
| `GET` | `/api/projects/{id}/demo` | Client: fetch demo URL (requires deposit paid) |

### Payments (Stripe)

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/payments/deposit` | Create 20% PaymentIntent. Returns `client_secret` |
| `POST` | `/api/payments/final` | Create 80% PaymentIntent (requires deposit paid) |
| `POST` | `/api/payments/webhook` | Stripe webhook handler (`payment_intent.succeeded`) |
| `GET` | `/api/payments/{id}/status` | `{deposit_paid, final_paid, …}` |

### Agent A2A Endpoints

Each agent exposes the full [A2A protocol](https://github.com/pydantic/pydantic-ai):

| Path | Agent |
|---|---|
| `/` or `/ceo/` | CEO Agent |
| `/sales/` | Sales Agent |
| `/pm/` | Project Manager |
| `/researcher/` | Researcher |
| `/engineer/` | Engineer |
| `/qa/` | QA Agent |

Interactive docs for each agent: `/docs`, `/sales/docs`, `/pm/docs`, etc.

---

## Payment Flow

```
Client                     Frontend              Backend              Stripe
  │                            │                    │                   │
  ├── fills consult form ──►  POST /api/consult/start                   │
  │                            │◄── session_id ─────┤                   │
  │   (chat with Sales Agent)  │                    │                   │
  ├── POST /api/consult/{id}/complete               │                   │
  │                            │  agency loop runs  │                   │
  │                            │◄── project_id ─────┤                   │
  │                            │                    │                   │
  ├── visits /proposal/{id} ──► GET /api/projects/{id}/proposal          │
  │                            │◄── Proposal ───────┤                   │
  │                            │                    │                   │
  ├── clicks "Pay Deposit" ──► POST /api/payments/deposit               │
  │                            │◄── client_secret ──┤─CreateIntent─────►│
  │                            │                    │                   │
  ├── enters card ────────────► stripe.confirmPayment()                 │
  │                            │                    │◄── webhook ───────┤
  │                            │                    │  deposit_paid=True │
  │                            │                    │                   │
  ├── reviews demo ───────────► GET /api/projects/{id}/demo             │
  │                            │                    │                   │
  ├── pays balance ───────────► POST /api/payments/final                │
  │                            │◄── client_secret ──┤─CreateIntent─────►│
  │                            │                    │◄── webhook ───────┤
  │                            │                    │  final_paid=True  │
  │◄── receives delivery ──────┤                    │                   │
```

---

## Customization

### Swap LLMs

Edit `src/agent_puter/swarm/base_agent.py` — uses `litellm` format:

```python
# OpenAI
PUTER_MODEL=gpt-4o

# Gemini via litellm
PUTER_MODEL=gemini/gemini-2.0-flash

# Anthropic
PUTER_MODEL=claude-3-5-sonnet-20241022

# Puter (free inference)
PUTER_AUTH_TOKEN=...
PUTER_MODEL=gpt-4o-mini
```

### Add a new agent

1. Copy `sales_agent.py` as a template
2. Define your system prompt and tools
3. At the bottom of your new file, call `.to_a2a()` directly:
   ```python
   from .ceo_agent import BASE_URL
   my_app = my_agent.to_a2a(name="My Agent", url=f"{BASE_URL}/myagent",
                             description="What this agent does.")
   ```
4. In `main.py`, import your app and mount it:
   ```python
   from .my_agent import my_agent, my_app as _my_app
   # then in routes:
   Mount("/myagent", app=_my_app)
   ```
5. Add to `_AGENT_URLS` in `agency.py` so the orchestrator can dispatch to it via `A2AClient`:
   ```python
   "myagent": f"{BASE_URL}/myagent",
   ```
6. Add to `Agency._execute_task()` role mapping if it should be assignable to tasks

### Persist data

The default in-memory store (`api/_store.py`) is intentionally simple. For production:
- Replace `_store.sessions` / `_store.projects` with Puter KV, Redis, or a database
- `AgencyDeps.puter_token` is already wired for Puter KV integration

---

## Development

```bash
# Install deps
uv sync

# Run backend with auto-reload
uvicorn agent_puter.swarm.main:app --reload --port 9999

# Run frontend
cd frontend && npm run dev

# Type-check frontend
cd frontend && npm run build

# Stripe webhook forwarding (local dev)
stripe listen --forward-to localhost:9999/api/payments/webhook
```

---

## Roadmap

- [ ] **Puter KV persistence** — replace in-memory store with durable Puter cloud KV
- [ ] **Admin dashboard** — manage projects, set demo URLs, view agent logs
- [ ] **Email notifications** — notify clients when proposal is ready / demo is live
- [ ] **Streaming chat** — SSE-based streaming responses in the consult interface
- [ ] **Multi-tenancy** — agency owner accounts with separate project namespaces
- [ ] **LLM cost tracking** — per-project token usage and cost reporting
- [ ] **Automated delivery** — Engineer agent deploys to a subdomain of your url for the demo automatically
- [ ] **Integrate with a2a_mcp_gateway** — Integrate MCP Functionality for tool usage

---

## License

MIT © 2026 Charles Nichols — [vizionikmedia.com](https://vizionikmedia.com)
