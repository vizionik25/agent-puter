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

### Required values

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
See [docs.puter.com/playground/ai-list-model-providers](https://docs.puter.com/playground/ai-list-model-providers/) for the full model list. Claude Sonnet 4.5/4.6 and Opus 4.6 are recommended. Most providers use the OpenAI format, hence the `openai/` prefix.

**Using a different LLM provider:**  
Set `PUTER_MODEL`, `PUTER_AUTH_TOKEN`, and `PUTER_API_BASE` to match your provider (any OpenAI-compatible endpoint works). To use Anthropic directly, edit `src/agent_puter/swarm/base_agent.py:make_model()`.

---

### Storage backend

By default, all data is in-memory and lost on restart. To persist:

```env
# JSON file — good for single-instance dev/staging
STORAGE_BACKEND=json_file
STORAGE_PATH=./data/store.json

# Puter cloud KV — uses your PUTER_AUTH_TOKEN above
STORAGE_BACKEND=puter_kv
PUTER_KV_BASE=https://api.puter.com/kv   # optional override
```

The `json_file` backend writes atomically — safe to `Ctrl-C` mid-request. The `puter_kv` backend persists across machines and deployments using the same Puter account.

---

### Admin dashboard

```env
# Protect all /api/admin/* routes with a shared secret
ADMIN_API_KEY=change-me-in-production
```

Set this to a strong random string. The Next.js admin page at `/admin` will prompt for this key. Leave unset to disable admin routes entirely (returns `503`).

---

### Email notifications

All fields are optional — notifications are silently skipped when unset.

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@example.com
SMTP_PASS=your-app-password    # Gmail: use an App Password, not your account password
FROM_EMAIL=noreply@yourdomain.com
FRONTEND_URL=http://localhost:3000
```

Emails are sent at three lifecycle points:
- Proposal ready → `session.client_email`
- Demo ready → `project.client_id`
- Delivery complete → `project.client_id`

---

### Multi-tenancy

```env
# Comma-separated key:tenant pairs
AGENCY_API_KEYS=secretkey1:acme,secretkey2:contoso
```

Clients send `X-Agency-Key: secretkey1` (or `Authorization: Bearer secretkey1`). All their sessions and projects are scoped to tenant `"acme"` and won't appear in other tenants' lists. Requests without a valid key land in `"default"`.

---

### MCP integration

```env
# Attach an MCP server to the Researcher and Engineer agents
MCP_SERVER_URL=http://localhost:3100/mcp
```

When set, both agents gain the MCP server's tools with the `mcp_` prefix — enabling real web browsing, database access, or any custom tools your MCP server exposes. Leave blank to run without MCP (agents use their built-in placeholder tools).

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
3. Chat with the Sales Agent until it acknowledges your requirements. The chat auto-completes and redirects to `/proposal/{id}`.
4. The proposal page shows the execution credit cost. If your credit balance is sufficient, click **Execute Project** to deduct credits and start the agent swarm.
5. You are redirected to `/status/{id}` which polls every 8 seconds and shows task-by-task progress.
6. When all tasks are `done` and the project reaches `delivered`, a **View Demo** link appears.
7. Check `http://localhost:9999/health` for a JSON listing of all agents and feature flags.
8. Open `http://localhost:3000/billing` to manage your subscription plan and credit balance.
9. Open `http://localhost:3000/admin` (if `ADMIN_API_KEY` is set) to see the admin dashboard.

---

## Admin Dashboard

The admin interface lives at `/admin` in the frontend. Enter your `ADMIN_API_KEY` to log in.

- **Projects list** — all projects with status, payment flags, LLM cost, and task progress
- **Project detail** — task outputs, QA feedback, cost breakdown, demo URL setter, log tail
- **Sessions list** — all consultation sessions with message counts
- **Log viewer** — last 500 server events filterable by project

To set a demo URL manually (for projects that deployed outside the sandbox):

```bash
curl -X POST http://localhost:9999/api/admin/projects/{id}/demo-url \
  -H "X-Admin-Key: your-admin-key" \
  -H "Content-Type: application/json" \
  -d '{"demo_url": "https://example.com/demo"}'
```

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
    model_name="claude-sonnet-4-6",
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

By default, `STORAGE_BACKEND=memory` — all data resets on restart. Switch to a durable backend by setting `STORAGE_BACKEND` in `.env`:

```env
# Local file (survives restarts, single-instance only)
STORAGE_BACKEND=json_file
STORAGE_PATH=./data/store.json

# Puter cloud KV (works across deployments)
STORAGE_BACKEND=puter_kv
```

For multi-instance production deployments, use `puter_kv` or implement a custom `AbstractStore` subclass in `api/store.py` backed by Redis, PostgreSQL, or any other store.
