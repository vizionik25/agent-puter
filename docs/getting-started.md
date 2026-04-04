# Getting Started

---

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| [uv](https://github.com/astral-sh/uv) | latest | Python package manager |
| Python | ≥ 3.14 | Managed by uv automatically |
| Node.js | ≥ 20 | Required for frontend only |
| [Stripe CLI](https://stripe.com/docs/stripe-cli) | latest | Required for local webhook testing |

You also need:
- A free [Puter.com](https://puter.com) account for the LLM token (or any OpenAI-compatible API)
- A [Stripe](https://stripe.com) account (test mode keys work)

---

## Installation

### From PyPI (backend only)

```bash
uv tool install agent-puter
```

This puts `agent-puter` on your PATH as a CLI command. The frontend must be set up separately (see below).

### From source (full monorepo)

```bash
git clone https://github.com/vizionik25/agent-puter.git
cd agent-puter
uv sync
```

---

## Configuration

Copy `.env.example` to `.env` and fill in the values:

```bash
cp .env.example .env
```

**Required values:**

```env
# LLM via Puter (free inference)
PUTER_AUTH_TOKEN=your-puter-session-token
PUTER_MODEL=openai/claude-sonnet-4-5
PUTER_API_BASE=https://api.puter.com/puterai/openai/v1

# Stripe (test keys work)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Frontend → backend URL
NEXT_PUBLIC_API_URL=http://localhost:9999
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...
```

**Getting a Puter token:**
1. Sign in at [puter.com](https://puter.com)
2. Open [puter.com/dashboard#account](https://puter.com/dashboard#account)
3. Copy your session token

**Supported models:**
See [docs.puter.com/playground/ai-list-model-providers](https://docs.puter.com/playground/ai-list-model-providers/) for the full model list. Claude Sonnet 4.5/4.6 and Opus 4.7 are recommended. Most providers use the OpenAI format, hence the `openai/` prefix.

**Using a different LLM provider:**  
Set `PUTER_MODEL`, `PUTER_AUTH_TOKEN`, and `PUTER_API_BASE` to match your provider (any OpenAI-compatible endpoint works). To use Anthropic directly, edit `src/agent_puter/swarm/base_agent.py:make_model()`.

---

## Running Locally

### Backend

```bash
# From source
uv run agent-puter

# Or with uvicorn directly (supports --reload)
uvicorn agent_puter.swarm.main:app --host 0.0.0.0 --port 9999 --reload
```

The backend starts at `http://localhost:9999`. Interactive agent docs are at:
- `http://localhost:9999/docs` (CEO)
- `http://localhost:9999/sales/docs`
- `http://localhost:9999/pm/docs`
- `http://localhost:9999/product-manager/docs`
- `http://localhost:9999/researcher/docs`
- `http://localhost:9999/engineer/docs`
- `http://localhost:9999/qa/docs`

### Frontend

**Option A — standalone frontend repo:**

```bash
git clone https://github.com/vizionik25/agent-puter-frontend.git
cd agent-puter-frontend
npm install
npm run dev
```

**Option B — from the monorepo:**

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:3000`.

### Stripe webhook (required for payments)

In a third terminal:

```bash
stripe listen --forward-to http://localhost:9999/api/payments/webhook
```

Copy the webhook signing secret it prints and set `STRIPE_WEBHOOK_SECRET=whsec_...` in `.env`, then restart the backend.

---

## Running with Docker

Docker is the recommended path for production. All services run in minimal, non-root images.

### Full stack (frontend + backend)

```bash
cp .env.example .env  # fill in all values first
docker compose up --build -d
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend | http://localhost:9999 |

> `NEXT_PUBLIC_API_URL` is set to `http://backend:9999` (internal Docker network) automatically by `docker-compose.yml`. Do not override this for full-stack mode.

### Backend only

```bash
docker compose -f docker-compose.backend.yml up --build -d
```

Point the frontend at the backend's public URL via `NEXT_PUBLIC_API_URL`.

### Frontend only

```bash
cd frontend
NEXT_PUBLIC_API_URL=https://api.yourdomain.com \
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_... \
docker compose up --build -d
```

### Useful Docker commands

```bash
docker compose logs -f backend      # tail backend logs
docker compose logs -f frontend     # tail frontend logs
docker compose up --build -d        # rebuild and restart after code changes
docker compose down                 # stop all services
docker compose down -v              # stop and remove volumes
```

---

## Verifying the Setup

Once both services are running:

1. Open `http://localhost:3000` — landing page should load.
2. Click **Start Consultation** and fill in your name, email, and a project description.
3. Chat with the Sales Agent until it acknowledges your requirements.
4. The session auto-completes and redirects you to `/proposal/{id}`.
5. Click **Pay Deposit** — use Stripe test card `4242 4242 4242 4242`, any future date, any CVC.
6. Check `http://localhost:9999/health` for a JSON listing of all agents.

---

## Development Workflow

```bash
# Backend with hot reload
uvicorn agent_puter.swarm.main:app --reload --port 9999

# Frontend dev server
cd frontend && npm run dev

# Type-check frontend (no emit)
cd frontend && npm run build

# Lint frontend
cd frontend && npm run lint
```

There is no backend test suite in the current codebase. Functional testing goes through the full UI flow or directly against the REST endpoints.

---

## Switching LLM Providers

All agents share `src/agent_puter/swarm/base_agent.py`. Changing the provider means updating `make_model()` once:

```python
# Anthropic native (no Puter)
return LiteLLMModel(
    model_name="claude-3-5-sonnet-20241022",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
)

# OpenAI
return LiteLLMModel(
    model_name="gpt-4o",
    api_key=os.getenv("OPENAI_API_KEY"),
)

# Any OpenAI-compatible endpoint
return LiteLLMModel(
    model_name="openai/my-model",
    api_key=os.getenv("MY_API_KEY"),
    api_base=os.getenv("MY_API_BASE"),
    custom_llm_provider="openai",
)
```

`pydantic-ai-litellm` handles tool schema conversion automatically regardless of provider.

---

## Persisting Data

`api/_store.py` uses plain in-memory dicts — all sessions and projects are lost on restart. For production, replace the two dicts with calls to your preferred store:

```python
# api/_store.py
import redis  # or your DB client

sessions: dict[str, ConsultSession] = {}   # replace with Redis/Postgres
projects: dict[str, Project] = {}          # replace with Redis/Postgres
```

Puter KV, Redis, and PostgreSQL are all viable options; the rest of the codebase only reads from and writes to these two dicts.
