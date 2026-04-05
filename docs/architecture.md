# Architecture

Agent-Puter is structured as three loosely-coupled components that communicate over HTTP.

---

## System Diagram

```
Browser
  │
  │  http://localhost:3000
  ▼
┌──────────────────────────────────────────────────────────────────┐
│  Next.js 16 Frontend  (port 3000)                                │
│                                                                  │
│  Pages                        Client-side libraries              │
│  /                 landing    lib/api.ts      REST client        │
│  /consult          chat SSE   lib/billing.ts  localStorage mock  │
│  /proposal/[id]    CTA        components/CreditBadge.tsx         │
│  /billing          plans      components/MockStripeModal.tsx     │
│  /demo/[id]        iframe                                        │
│  /status/[id]      polling                                       │
│                                                                  │
│  next.config.ts  output:standalone                               │
└────────────────────────────────┬─────────────────────────────────┘
                                 │  fetch /api/*  (relative URLs)
                                 │  Docker: proxy via API_URL env var
                                 │  Local dev: NEXT_PUBLIC_API_URL=http://localhost:9999
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│  Starlette Backend  (port 9999)                                  │
│                                                                  │
│  ── REST API routes ───────────────────────────────────────── │
│  /api/consult/*       consultation.py                            │
│  /api/projects/*      projects.py                                │
│  /api/payments/*      payments.py + Stripe SDK                   │
│  /api/admin/*         admin.py  (X-Admin-Key)                    │
│                                                                  │
│  ── Agent A2A apps (fasta2a) ──────────────────────────────── │
│  /              CEO Agent        ceo_agent.py                    │
│  /sales         Sales Agent      sales_agent.py                  │
│  /pm            PM Agent         pm_agent.py                     │
│  /product-manager  Product Mgr   product_manager_agent.py        │
│  /researcher    Researcher       researcher_agent.py             │
│  /engineer      Engineer         engineer_agent.py               │
│  /qa            QA Agent         qa_agent.py                     │
│                                                                  │
│  /deliveries/*    StaticFiles — auto-deployed sandbox HTML       │
│                                                                  │
│  Store: MemoryStore | JsonFileStore | PuterKVStore               │
└──────────────────────────────────────────────────────────────────┘
                                 │
                                 │  HTTPS  (LiteLLM)
                                 ▼
                    Puter.js OpenAI-compatible API
                    (or any OpenAI-compatible endpoint)
```

---

## Component Map

```
┌─────────────────────────────────────────────────────────────┐
│  Browser                                                     │
│  Next.js 16 — port 3000                                     │
│  ├── /consult            Chat (SSE streaming)               │
│  ├── /proposal/[id]      Proposal + credit execution CTA    │
│  ├── /billing            Subscription & credit management   │
│  ├── /demo/[id]          Live demo (iframe)                 │
│  └── /status/[id]        Progress dashboard (polls 8s)      │
└────────────────────┬────────────────────────────────────────┘
                     │  JSON REST / SSE  (NEXT_PUBLIC_API_URL)
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Starlette — port 9999                                       │
│                                                              │
│  Middleware                                                  │
│  └── CORSMiddleware (localhost:3000, localhost:9999)        │
│                                                              │
│  REST API (api/)                                             │
│  ├── /api/consult/*        consultation.py                  │
│  ├── /api/consult/{id}/stream  SSE streaming                │
│  ├── /api/projects/*       projects.py                      │
│  ├── /api/payments/*       payments.py  ──► Stripe          │
│  └── /api/admin/*          admin.py (X-Admin-Key)          │
│                                                              │
│  A2A sub-apps (fasta2a .to_a2a())                           │
│  ├── /           CEO Agent                                   │
│  ├── /sales      Sales Agent                                │
│  ├── /pm         PM Agent                                   │
│  ├── /product-manager  Product Manager Agent                │
│  ├── /researcher Researcher Agent (+ optional MCP)          │
│  ├── /engineer   Engineer Agent (+ optional MCP)            │
│  └── /qa         QA Agent                                   │
│                                                              │
│  Static files                                                │
│  └── /deliveries/{project_id}/  Sandbox delivery hosting   │
│                                                              │
│  Persistence (api/store.py)                                  │
│  └── AbstractStore → MemoryStore | JsonFileStore | PuterKVStore│
└─────────────────────────────────────────────────────────────┘
```

---

## Agent Swarm

Each agent is declared in its own module following an identical three-step pattern:

```python
# 1. Build a LiteLLMModel (reads PUTER_* env vars)
from .base_agent import make_model
from pydantic_ai import Agent

agent = Agent(model=make_model(), instructions=SYSTEM_PROMPT, toolsets=_make_mcp_toolsets())

# 2. Register tools
@agent.tool_plain
def my_tool(arg: str) -> str: ...

# 3. Expose as a self-contained A2A ASGI app
from .ceo_agent import BASE_URL
app = agent.to_a2a(name="...", url=f"{BASE_URL}/mount-path", description="...")
```

`main.py` imports each `(agent, app)` pair, initialises the `app.task_manager` in the lifespan, and mounts the app at its path. `main.py` never calls `.to_a2a()` or `.run()` itself.

### Agent roster

| Module | Mount | Role |
|--------|-------|------|
| `ceo_agent.py` | `/ceo` (also root `/`) | Strategy, budget allocation, final approval |
| `sales_agent.py` | `/sales` | Client intake, project brief |
| `pm_agent.py` | `/pm` | Task decomposition, assignment, escalation |
| `product_manager_agent.py` | `/product-manager` | User stories, feature prioritization |
| `researcher_agent.py` | `/researcher` | Web research, doc summarization (+ MCP) |
| `engineer_agent.py` | `/engineer` | Code generation, file I/O, test execution, sandbox deploy (+ MCP) |
| `qa_agent.py` | `/qa` | Output review, PASS/FAIL verdict |

### Inter-agent communication

All agent-to-agent calls use `fasta2a.client.A2AClient`. `agency.py` owns the business loop and dispatches every call via HTTP:

```python
client = A2AClient(base_url="http://localhost:9999/pm")
response = await client.send_message(message={
    "role": "user", "kind": "message",
    "messageId": "<uuid>",
    "parts": [{"kind": "text", "text": prompt}],
})
```

The response is either a `Task` (with `status.message.parts`) or a `Message` (with `parts` directly). `_call_agent()` in `agency.py` handles both shapes and returns plain text.

---

## Persistence Layer

All session and project data flows through `api/store.py`'s `AbstractStore` interface. The active backend is selected at import time via `STORAGE_BACKEND`:

```
STORAGE_BACKEND=memory    → MemoryStore    (default — resets on restart)
STORAGE_BACKEND=json_file → JsonFileStore  (persists to STORAGE_PATH)
STORAGE_BACKEND=puter_kv  → PuterKVStore   (Puter cloud KV via HTTPS)
```

Route handlers use the async interface directly:

```python
from . import _store

session = await _store.store.get_session(session_id)
await _store.store.set_project(project)
projects = await _store.store.list_projects(owner_id="acme")
```

`JsonFileStore` writes atomically via a `.tmp` rename. `PuterKVStore` namespaces keys as `session:{id}` and `project:{id}` and calls `GET/POST /kv/get|set|list` on `PUTER_KV_BASE`.

---

## Multi-tenancy

`middleware.py:resolve_tenant(request)` extracts a `tenant_id` from the incoming request:

1. Checks `X-Agency-Key` header
2. Falls back to `Authorization: Bearer <key>`
3. Returns `"default"` if no recognised key is found

Keys are mapped to tenants via `AGENCY_API_KEYS=key1:tenant1,key2:tenant2`. The `owner_id` is stored on every `ConsultSession` and `Project`. Store list methods accept an `owner_id` filter so each tenant sees only their own data.

---

## Agency Business Loop

`Agency.handle_client_request()` drives the full lifecycle:

```
Client request text
    │
    ├─[A2A]─► Sales Agent      → project brief
    ├─[A2A]─► CEO Agent        → token budget allocation
    ├─[A2A]─► PM Agent         → ordered task list (JSON)
    │
    └─► For each task:
           ├─[A2A]─► Engineer or Researcher  → task output
           ├─[A2A]─► QA Agent               → PASS / FAIL
           │          ├─ PASS → mark DONE, next task
           │          └─ FAIL → increment retry, re-execute (max 5)
           │                     └─ retries exhausted → [A2A]─► CEO escalation
           │
    ├─[A2A]─► CEO Agent        → approve_delivery
    └──────► _auto_deploy()    → generate HTML, deploy to /deliveries/{id}/
```

Each A2A call is tracked: `project.llm_requests += 1`, `project.tokens_used += ~2000`, `project.llm_cost_usd += estimated_cost`. Per-task cost rolls up into `task.cost_usd`.

---

## LLM Cost Tracking

`agency.py` tracks a fixed estimate of `~2000 tokens` per A2A call using approximate Claude Sonnet pricing:

| Token type | Rate |
|-----------|------|
| Input | $3.00 / MTok |
| Output | $15.00 / MTok |

The `consultation.py` route also captures real `RunResult.usage()` data when `sales_agent.run()` is called directly (non-A2A path). Totals accumulate on `Project.tokens_used`, `Project.llm_requests`, and `Project.llm_cost_usd`. Task-level detail is in `Task.tokens_used` and `Task.cost_usd`.

Exposed via `GET /api/projects/{id}/usage`.

---

## Streaming Chat

The `POST /api/consult/{id}/stream` endpoint uses pydantic-ai's `run_stream()` API and returns a `text/event-stream` response:

```
data: {"type": "chunk", "text": "Hello"}
data: {"type": "chunk", "text": " there"}
data: {"type": "done",  "status": "active"}
```

The frontend `consultStream()` function in `lib/api.ts` reads the `ReadableStream` chunk-by-chunk and calls `onChunk(text)` for each delta. The chat UI writes each chunk into the active agent bubble in real time. It falls back to non-streaming `consultMessage()` if the stream endpoint is unavailable.

---

## Automated Delivery

After all tasks pass QA, `Agency._auto_deploy()`:

1. Collects `task.output` from every `DONE` task
2. Generates a single HTML page summarising all deliverables
3. Tries to dispatch a `deploy_to_sandbox` call via the Engineer agent (A2A)
4. Falls back to writing `deliveries/{project_id}/index.html` directly if the A2A call doesn't parse correctly
5. Sets `project.demo_url` and `project.deployment_status = "deployed"`

The Engineer agent's `deploy_to_sandbox(project_id, content, filename)` tool writes to `deliveries/{project_id}/{filename}`. Starlette serves this directory as `StaticFiles` at `/deliveries/`.

---

## MCP Integration

When `MCP_SERVER_URL` is set, both the Researcher and Engineer agents attach an `MCPServerHTTP` toolset:

```python
from pydantic_ai.mcp import MCPServerHTTP
toolsets = [MCPServerHTTP(url=mcp_url, tool_prefix="mcp")]
agent = Agent(model=make_model(), instructions=..., toolsets=toolsets)
```

Tools from the MCP server are exposed to the LLM with the `mcp_` prefix alongside the agent's built-in tools. The MCP server connection is established per-agent-run by pydantic-ai's toolset lifecycle. If `MCP_SERVER_URL` is not set or the connection fails, the agent starts normally with only its built-in tools.

---

## Email Notifications

`notifications.py` sends transactional emails at three lifecycle points:

| Trigger | Function | Recipient |
|---------|----------|-----------|
| `POST /api/consult/{id}/complete` | `notify_proposal_ready()` | `session.client_email` |
| `POST /api/projects/{id}/demo-url` | `notify_demo_ready()` | `project.client_id` |
| Stripe `payment_intent.succeeded` (final) | `notify_delivery_complete()` | `project.client_id` |

All notifications are fire-and-forget (exceptions are logged, never re-raised). They are silently skipped when `SMTP_HOST` / `SMTP_USER` / `SMTP_PASS` are not set.

---

## Admin System

`api/admin.py` exposes a management API protected by `X-Admin-Key: <ADMIN_API_KEY>`. An in-process `deque(maxlen=500)` ring buffer captures log events written by `log_event(level, source, message, project_id)` throughout the codebase.

The Next.js `/admin` page authenticates with the admin key client-side, lists all projects with aggregate stats (revenue, LLM cost), and links to per-project detail pages. The `/admin/projects/[id]` page shows full task output, QA feedback, cost metrics, demo URL setter, and the log tail filtered to that project.

---

## Data Model Relationships

```
ConsultSession
  ├── id: UUID
  ├── owner_id: str           (tenant namespace)
  ├── messages: ConsultMessage[]
  └── project_id → Project.id

Project
  ├── id: UUID
  ├── owner_id: str           (tenant namespace)
  ├── status: ProjectStatus
  ├── tasks: Task[]
  ├── proposal: Proposal | null
  ├── llm_requests: int       (cost tracking)
  ├── llm_cost_usd: float     (cost tracking)
  ├── tokens_used: int        (cost tracking)
  ├── stripe_deposit_intent_id
  ├── stripe_final_intent_id
  ├── deposit_paid: bool
  ├── final_paid: bool
  ├── demo_url: str | null
  └── deployment_status: str | null

Task
  ├── id: UUID
  ├── status: TaskStatus
  ├── assigned_to: str
  ├── output: str | null
  ├── qa_feedback: str | null
  ├── retry_count: int
  ├── tokens_used: int        (task-level cost tracking)
  └── cost_usd: float         (task-level cost tracking)

Proposal
  ├── total_price_usd
  ├── deposit_amount_usd  (20%)
  └── final_amount_usd    (80%)
```

All data lives in the `AbstractStore` — two namespaced collections of `ConsultSession` and `Project`. The active backend is controlled by `STORAGE_BACKEND`.

---

## Billing Mock System

All billing state is frontend-only. No backend billing endpoints exist. State is persisted in `localStorage` under the key `agentputer_billing`.

**State shape (`BillingState`):**

```typescript
{
  tierId: "free" | "starter" | "pro" | "business",
  credits: number,
  cycleStart: string,        // ISO date of last monthly grant
  ledger: CreditLedgerEntry[],
  executedProjects: string[] // idempotency: project IDs already charged
}
```

**Monthly reset:** `getState()` detects when `cycleStart` is more than 30 days ago and auto-grants the tier's `creditsPerMonth`, adding a `monthly_grant` ledger entry.

**Credit pack purchases:** `purchasePack(packId)` throws if `tierId === "free"`. A paid subscription is required to top up.

**Project execution:** `deductCredit(projectId, cost)` is idempotent. Calling it again for the same `projectId` is a no-op. Throws `"Insufficient credits"` if balance is low.

**Cost formula (from `billing.ts`):**

```
totalTokens   = estimatedHours × 75,000
inputTokens   = totalTokens × 0.70
outputTokens  = totalTokens × 0.30
totalCredits  = (inputTokens / 1,000,000 × 3) + (outputTokens / 1,000,000 × 15)
```

Rates: 3 credits / 1M input tokens, 15 credits / 1M output tokens.

---

## Stripe Legacy Endpoints

The backend still exposes four Stripe endpoints for deposit/final payment flows (`/api/payments/*`). These are not currently wired into the frontend credit flow but remain available for operators who want to integrate real payment collection:

```
POST /api/payments/deposit       → creates 20% PaymentIntent
POST /api/payments/final         → creates 80% PaymentIntent (requires deposit_paid)
POST /api/payments/webhook       → handles payment_intent.succeeded, sets deposit_paid/final_paid
GET  /api/payments/{id}/status   → returns deposit_paid, final_paid flags
```

The `Project` model tracks `deposit_paid`, `final_paid`, `stripe_deposit_intent_id`, and `stripe_final_intent_id` for this flow.

---

## Lifespan & Startup

```python
@asynccontextmanager
async def _lifespan(app):
    async with _ceo_app.task_manager:
      async with _sales_app.task_manager:
        async with _pm_app.task_manager:
          async with _researcher_app.task_manager:
            async with _engineer_app.task_manager:
              async with _qa_app.task_manager:
                async with _product_manager_app.task_manager:
                  yield
```

`Path("deliveries").mkdir(exist_ok=True)` runs at module import to ensure the sandbox directory exists before the static file handler is mounted.

---

## LLM Provider Abstraction

`base_agent.py:make_model()` constructs a `LiteLLMModel` from three env vars:

| Var | Example |
|-----|---------|
| `PUTER_MODEL` | `openai/claude-sonnet-4-5` |
| `PUTER_AUTH_TOKEN` | Puter session token |
| `PUTER_API_BASE` | `https://api.puter.com/puterai/openai/v1` |

`custom_llm_provider="openai"` is hardcoded because Puter exposes an OpenAI-compatible endpoint. `pydantic-ai-litellm` handles tool schema conversion automatically for any provider.

---

## Adding a New Agent

1. Create `src/agent_puter/swarm/my_agent.py` following the three-step pattern above.
2. In `main.py`:
   - Import `my_agent, my_app as _my_app`
   - Add `async with _my_app.task_manager:` to the lifespan nesting
   - Add `Mount("/my-agent", app=_my_app)` to routes
   - Add an entry to the health endpoint's `agents` list
3. In `agency.py`, add `"my_agent": f"{BASE_URL}/my-agent"` to `_AGENT_URLS`.
