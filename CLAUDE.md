# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Agent-Puter is a fully autonomous AI consulting agency ("business in a box"). Clients describe projects via a chat interface, receive AI-generated proposals with fixed pricing, and a swarm of specialized LLM agents executes the work autonomously. Payment is split: 20% deposit before work, 80% after client approves a live demo.

## Development Commands

### Backend

```bash
# Install dependencies
uv sync

# Run backend (port 9999)
uv run agent-puter
# or directly:
uvicorn agent_puter.swarm.main:app --host 0.0.0.0 --port 9999 --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev        # port 3000
npm run build      # TypeScript check + production build
npm run lint       # ESLint
```

### Full Stack (Docker)

```bash
docker compose up --build -d           # Full stack (ports 3000 + 9999)
docker compose -f docker-compose.backend.yml up --build -d  # Backend only
```

### Stripe Webhooks (local testing)

```bash
stripe listen --forward-to localhost:9999/api/payments/webhook
```

## Architecture

### Three-Component Structure

- **`src/agent_puter/swarm/`** — Python backend: 6 specialized agents + REST API
- **`frontend/`** — Next.js 16 client portal (React 19, TypeScript, Stripe)
- **Docker** — Multi-stage builds for containerized deployment

### Agent Swarm (`src/agent_puter/swarm/`)

Each agent follows the same pattern: `make_model()` → `pydantic_ai.Agent` with `@agent.tool_plain` tools → `.to_a2a()` ASGI app.

| Agent | URL mount | Role |
|-------|-----------|------|
| CEO | `/` | Orchestration, budget allocation, final approval |
| Sales | `/sales` | Client intake, project brief creation |
| PM | `/pm` | Task decomposition, agent assignment |
| Engineer | `/engineer` | Code generation and testing |
| Researcher | `/researcher` | Web research, document summarization |
| QA | `/qa` | Output review, PASS/FAIL verdicts |

All inter-agent calls use the **A2A protocol** (HTTP via `fasta2a.A2AClient`), not direct Python calls. This enables independent scaling and monitoring.

**`base_agent.py`** — `make_model()` creates a `LiteLLMModel` from `PUTER_MODEL`, `PUTER_AUTH_TOKEN`, `PUTER_API_BASE` env vars. All agents use this.

**`agency.py`** — `Agency` class owns the autonomous business loop. `_call_agent(base_url, prompt)` sends A2A messages and parses responses.

**`main.py`** — Starlette app mounts all 6 agent A2A apps as sub-applications, registers REST API routes, handles CORS. Lifespan context initializes all `TaskManager` instances.

### REST API (`src/agent_puter/api/`)

- **`_store.py`** — In-memory `sessions` and `projects` dicts. **Data resets on restart** — production should replace with Puter KV or PostgreSQL.
- **`consultation.py`** — `/api/consult/*`: session management, Sales Agent chat
- **`projects.py`** — `/api/projects/*`: project status, proposal retrieval, demo gating
- **`payments.py`** — `/api/payments/*`: Stripe PaymentIntents (20% deposit, 80% final), webhook handler

### Frontend (`frontend/`)

- **`lib/api.ts`** — Typed REST client wrapping all backend endpoints
- **`app/consult/page.tsx`** — Two-phase chat: intro form → message loop → auto-completes to `/proposal/{id}`
- **`app/status/[id]/page.tsx`** — Polls `GET /api/projects/{id}` for real-time task progress

### Data Flow

1. Client chats with Sales Agent (direct `.run()` calls, not A2A)
2. `POST /api/consult/{id}/complete` triggers `Agency.handle_client_request()`
3. Agency orchestrates: CEO → PM → (Engineer/Researcher) → QA → CEO approval (all via A2A)
4. Client pays 20% deposit via Stripe → can view demo
5. Client pays 80% final → project delivered

### Configuration

Copy `.env.example` to `.env`. Key variables:
- `PUTER_AUTH_TOKEN`, `PUTER_API_BASE`, `PUTER_MODEL` — LLM provider (defaults to Puter.js free inference)
- `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET` — Stripe payments
- `NEXT_PUBLIC_API_URL` — Frontend → backend URL (default: `http://localhost:9999`)

### Next.js Version Note

This project uses **Next.js 16**, which has breaking changes from earlier versions. Before modifying frontend code, read the relevant guide in `frontend/node_modules/next/dist/docs/`.
