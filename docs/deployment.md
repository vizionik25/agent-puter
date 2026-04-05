# Deployment

---

## Docker Compose (recommended)

Three Docker Compose configurations are provided:

| File | Use case |
|------|----------|
| `docker-compose.yml` | Full stack: backend + frontend on one machine |
| `docker-compose.backend.yml` | Backend only |
| `frontend/docker-compose.yml` | Frontend only |

### Full Stack

Runs both the Python backend (port 9999) and the Next.js frontend (port 3000) on a shared bridge network (`agent_net`). The frontend container waits for the backend health-check before starting.

```bash
cp .env.example .env
# Fill in PUTER_AUTH_TOKEN, PUTER_MODEL, PUTER_API_BASE, STRIPE_* keys,
# and (optional) GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, SESSION_SECRET
docker compose up --build -d
```

| URL | Service |
|-----|---------|
| `http://localhost:3000` | Frontend |
| `http://localhost:9999` | Backend API |
| `http://localhost:9999/health` | Swarm health + feature flags |
| `http://localhost:9999/docs` | CEO Agent interactive docs |

In full-stack Docker mode, `NEXT_PUBLIC_API_URL` is intentionally set to `""` (empty string) so the browser sends all `/api/*` fetches relative to its own origin (`localhost:3000`). Next.js proxies these to the backend via the `API_URL=http://backend:9999` server-side environment variable.

### Backend Only

```bash
docker compose -f docker-compose.backend.yml up --build -d
```

Set `NEXT_PUBLIC_API_URL=https://api.yourdomain.com` in your frontend deployment so `lib/api.ts` prepends the correct base URL.

### Frontend Only

```bash
cd frontend
NEXT_PUBLIC_API_URL=https://api.yourdomain.com \
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_... \
docker compose up --build -d
```

### Common Docker commands

```bash
# View logs
docker compose logs -f backend
docker compose logs -f frontend

# Rebuild after code changes
docker compose up --build -d

# Stop all services
docker compose down

# Stop and remove volumes
docker compose down -v
```

---

## Docker Image Details

### Backend — `Dockerfile`

Multi-stage build:

1. **Builder** (`ghcr.io/astral-sh/uv:python3.14-bookworm-slim`) — installs dependencies with `uv sync --frozen`, then copies source and installs the project.
2. **Runtime** (`python:3.14-slim-bookworm`) — copies only `/app` from the builder. Runs as a non-root `app` user (uid 999).

Entrypoint:
```
python -m uvicorn agent_puter.swarm.main:app --host 0.0.0.0 --port 9999 --proxy-headers
```

`--proxy-headers` enables proper IP forwarding when behind a reverse proxy (nginx, Caddy, etc.).

### Frontend — `frontend/Dockerfile`

Three-stage build:

1. **deps** (`node:22-slim`) — `npm ci --omit=dev` with package manifests only.
2. **builder** (`node:22-slim`) — full source + `npm run build` → `output:standalone`.
3. **runtime** (`node:22-slim`) — copies `.next/standalone`, `.next/static`, and `public/`. Runs as a non-root `nextjs` user.

`NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` are injected as build `ARG`s because Next.js embeds them at build time. They must be set before `docker compose up --build`.

---

## Environment Variables Reference

### Required

| Variable | Description |
|----------|-------------|
| `PUTER_AUTH_TOKEN` | Puter.js session token. Used as the LLM API key. Obtain from [puter.com/dashboard#account](https://puter.com/dashboard#account). |
| `PUTER_MODEL` | LiteLLM model string, e.g. `openai/claude-sonnet-4-5`. See [puter.com model list](https://docs.puter.com/playground/ai-list-model-providers/). |
| `PUTER_API_BASE` | LLM endpoint. Puter default: `https://api.puter.com/puterai/openai/v1`. |

### Stripe (optional)

Only needed if you want to use the legacy deposit/final payment flow via `/api/payments/*`.

| Variable | Description |
|----------|-------------|
| `STRIPE_SECRET_KEY` | Backend Stripe secret key (`sk_test_...` or `sk_live_...`). |
| `STRIPE_PUBLISHABLE_KEY` | Stripe publishable key — used in backend metadata. |
| `STRIPE_WEBHOOK_SECRET` | Webhook signing secret (`whsec_...`). Obtained from Stripe CLI or dashboard. |
| `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` | Stripe publishable key for frontend Stripe Elements. |

### Frontend / Networking

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `""` | Base URL prepended to all `/api/*` fetches. Empty = relative (Docker full-stack). Set to `http://localhost:9999` for local dev. **Must be set before building the frontend image.** |
| `API_URL` | — | Server-side rewrite target. Set to `http://backend:9999` in Docker. Not embedded by Next.js. |

### Storage

| Variable | Default | Description |
|----------|---------|-------------|
| `STORAGE_BACKEND` | `memory` | `memory`, `json_file`, or `puter_kv`. |
| `STORAGE_PATH` | `./data/store.json` | File path for `json_file` backend. |
| `PUTER_KV_BASE` | `https://api.puter.com/kv` | Override for `puter_kv` API endpoint. |

### Admin

| Variable | Default | Description |
|----------|---------|-------------|
| `ADMIN_API_KEY` | — | Protects all `/api/admin/*` routes. Unset disables admin (returns 503). Use a strong random value in production. |

### Multi-tenancy

| Variable | Description |
|----------|-------------|
| `AGENCY_API_KEYS` | Comma-separated `key:tenant` pairs. E.g. `key1:acme,key2:contoso`. Requests with `X-Agency-Key: key1` are scoped to tenant `"acme"`. |

### Email Notifications

All fields are optional. Notifications are silently skipped when unset.

| Variable | Default | Description |
|----------|---------|-------------|
| `SMTP_HOST` | — | SMTP server hostname (e.g. `smtp.gmail.com`). |
| `SMTP_PORT` | `587` | SMTP port. |
| `SMTP_USER` | — | SMTP login (email address). |
| `SMTP_PASS` | — | SMTP password or app-specific password. |
| `FROM_EMAIL` | `SMTP_USER` | Sender address. |
| `FRONTEND_URL` | `http://localhost:3000` | Base URL embedded in email action links. |

### GitHub OAuth

| Variable | Default | Description |
|----------|---------|-------------|
| `GITHUB_CLIENT_ID` | — | Client ID from your GitHub OAuth App. Required for GitHub login. |
| `GITHUB_CLIENT_SECRET` | — | Client secret from your GitHub OAuth App. Required for GitHub login. |
| `SESSION_SECRET` | random | HMAC-SHA256 key for signing session tokens. Set to a strong random value in production (`openssl rand -hex 32`). |

### MCP

| Variable | Description |
|----------|-------------|
| `MCP_SERVER_URL` | URL of an MCP server. When set, Researcher and Engineer agents gain MCP tools with the `mcp_` prefix. E.g. `http://localhost:3100/mcp`. |

---

## Storage Backend Selection

### Memory (default)

No configuration needed. All data is lost on process restart. Use only for demos and development.

### JSON File

```env
STORAGE_BACKEND=json_file
STORAGE_PATH=./data/store.json
```

Suitable for single-instance deployments. Data survives restarts. Writes are atomic (`.tmp` rename). Mount the data directory as a Docker volume:

```yaml
# docker-compose.yml addition
services:
  backend:
    volumes:
      - ./data:/app/data
```

### Puter KV

```env
STORAGE_BACKEND=puter_kv
# Uses PUTER_AUTH_TOKEN already set above
# Optional: PUTER_KV_BASE=https://api.puter.com/kv
```

Persists across machines and deployments. Good for multi-instance or serverless deployments where a local filesystem is not reliable. Uses the same Puter credentials as the LLM.

---

## Stripe Production Setup

1. Create a Stripe account and switch to **live mode**.
2. Set `STRIPE_SECRET_KEY=sk_live_...` and `STRIPE_PUBLISHABLE_KEY=pk_live_...` in `.env`.
3. In the Stripe dashboard, create a webhook endpoint:
   - **URL:** `https://yourdomain.com/api/payments/webhook`
   - **Events:** `payment_intent.succeeded`
4. Copy the signing secret and set `STRIPE_WEBHOOK_SECRET=whsec_...` in `.env`.
5. Rebuild and restart the backend.

**Local testing:**

```bash
stripe listen --forward-to localhost:9999/api/payments/webhook
# Copy the printed whsec_... and set STRIPE_WEBHOOK_SECRET in .env
# Restart backend
```

---

## CORS Configuration

The backend CORS middleware (in `main.py`) allows:
- `http://localhost:3000` — Next.js dev server
- `http://localhost:9999` — same-origin requests

For production, update the `allow_origins` list in `main.py` to include your production domain:

```python
Middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:9999",
        "https://yourdomain.com",      # add your production frontend URL
    ],
    allow_credentials=True,            # required for httpOnly session cookie
    allow_methods=["*"],
    allow_headers=["*"],
)
```

> **Note:** `allow_credentials=True` is required for the `ap_session` httpOnly cookie to be sent with cross-origin requests. When set, `allow_origins` must list explicit origins — wildcards (`"*"`) are not permitted by browsers when credentials are included.

---

## Reverse Proxy (nginx / Caddy)

The backend uses `--proxy-headers` so `X-Forwarded-For` and `X-Forwarded-Proto` are respected.

**Caddy example:**

```
yourdomain.com {
    reverse_proxy /api/* backend:9999
    reverse_proxy /* frontend:3000
}
```

**nginx example:**

```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;

    location /api/ {
        proxy_pass http://backend:9999;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        proxy_pass http://frontend:3000;
    }
}
```

---

## Health Check

```bash
curl http://localhost:9999/health
```

Response includes:

```json
{
  "status": "ok",
  "swarm": {
    "agents": [
      { "role": "ceo",     "docs": "/docs",                 "a2a": "/" },
      { "role": "sales",   "docs": "/sales/docs",           "a2a": "/sales/" },
      { "role": "pm",      "docs": "/pm/docs",              "a2a": "/pm/" },
      { "role": "researcher", "docs": "/researcher/docs",   "a2a": "/researcher/" },
      { "role": "engineer",   "docs": "/engineer/docs",     "a2a": "/engineer/" },
      { "role": "qa",         "docs": "/qa/docs",           "a2a": "/qa/" },
      { "role": "product_manager", "docs": "/product-manager/docs", "a2a": "/product-manager/" }
    ]
  },
  "storage_backend": "json_file",
  "mcp_enabled": false
}
```

The Docker health-check hits `/.well-known/agent-card.json` (the CEO agent card) with a 10-second timeout, retrying 5 times with 30-second intervals.

---

## Production Checklist

- [ ] `PUTER_AUTH_TOKEN`, `PUTER_MODEL`, `PUTER_API_BASE` set and verified
- [ ] `ADMIN_API_KEY` set to a strong random secret (not the default)
- [ ] `STORAGE_BACKEND=json_file` or `puter_kv` (not `memory`)
- [ ] `NEXT_PUBLIC_API_URL` set before building the frontend image
- [ ] CORS `allow_origins` updated to include production domain
- [ ] Stripe live keys set (if using Stripe payment collection)
- [ ] Stripe webhook pointing at `https://yourdomain.com/api/payments/webhook`
- [ ] Reverse proxy configured with TLS
- [ ] Docker containers running as non-root (both images already do this)
- [ ] `FRONTEND_URL` set to production URL (for email action links)
- [ ] GitHub OAuth App callback URL updated to `https://yourdomain.com/api/auth/callback`
- [ ] `SESSION_SECRET` set to a strong random value (`openssl rand -hex 32`)
- [ ] CORS `allow_credentials=True` and `allow_origins` includes production domain (required for session cookie)
