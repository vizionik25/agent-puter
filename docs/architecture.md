# Architecture

Agent-Puter runs as a single Starlette process on port 9999. It serves both the REST API consumed by the Next.js frontend and all seven A2A agent endpoints. Every inter-agent call travels over HTTP using the A2A protocol — there are no direct Python `.run()` calls between agents.

---

## Component Map

```
┌─────────────────────────────────────────────────────────────┐
│  Browser                                                     │
│  Next.js 16 — port 3000                                     │
│  ├── /consult            Chat with Sales Agent              │
│  ├── /proposal/[id]      View proposal                      │
│  ├── /pay/[id]/deposit   Stripe 20% deposit form            │
│  ├── /pay/[id]/final     Stripe 80% balance form            │
│  ├── /demo/[id]          Live demo (iframe, gated)          │
│  └── /status/[id]        Progress dashboard (polls 8s)      │
└────────────────────┬────────────────────────────────────────┘
                     │  JSON REST  (NEXT_PUBLIC_API_URL)
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Starlette — port 9999                                       │
│                                                              │
│  REST API                                                    │
│  ├── /api/consult/*        consultation.py                  │
│  ├── /api/projects/*       projects.py                      │
│  └── /api/payments/*       payments.py  ──► Stripe          │
│                                                              │
│  A2A sub-apps (fasta2a .to_a2a())                           │
│  ├── /           CEO Agent                                   │
│  ├── /sales      Sales Agent                                │
│  ├── /pm         PM Agent                                   │
│  ├── /product-manager  Product Manager Agent                │
│  ├── /researcher Researcher Agent                           │
│  ├── /engineer   Engineer Agent                             │
│  └── /qa         QA Agent                                   │
│                                                              │
│  In-memory store                                             │
│  api/_store.py  { sessions: {}, projects: {} }              │
└─────────────────────────────────────────────────────────────┘
```

---

## Agent Swarm

Each agent is declared in its own module following an identical three-step pattern:

```python
# 1. Build a LiteLLMModel (reads PUTER_* env vars)
from .base_agent import make_model
from pydantic_ai import Agent

agent = Agent(model=make_model(), instructions=SYSTEM_PROMPT)

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
| `researcher_agent.py` | `/researcher` | Web research, doc summarization |
| `engineer_agent.py` | `/engineer` | Code generation, file I/O, test execution |
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
    └─[A2A]─► CEO Agent        → approve_delivery
```

The `Agency` instance is constructed per-request inside `consultation.py`'s `complete_session` handler. There is no persistent Agency singleton.

---

## Data Model Relationships

```
ConsultSession
  ├── id: UUID
  ├── messages: ConsultMessage[]
  └── project_id → Project.id

Project
  ├── id: UUID
  ├── status: ProjectStatus enum
  ├── tasks: Task[]
  ├── proposal: Proposal | null
  ├── stripe_deposit_intent_id
  ├── stripe_final_intent_id
  ├── deposit_paid: bool
  └── final_paid: bool

Task
  ├── id: UUID
  ├── status: TaskStatus enum
  ├── assigned_to: "engineer" | "researcher" | "qa" | ...
  ├── output: str | null
  ├── qa_feedback: str | null
  └── retry_count: int

Proposal
  ├── total_price_usd
  ├── deposit_amount_usd  (20%)
  └── final_amount_usd    (80%)
```

All data lives in two plain dicts in `api/_store.py`:

```python
sessions: dict[str, ConsultSession]
projects: dict[str, Project]
```

Both reset on server restart. Replace with a durable store (Redis, PostgreSQL, Puter KV) for production.

---

## Payment Flow

```
Frontend                    Backend                 Stripe
   │                           │                      │
   ├─POST /api/payments/deposit─►─stripe.PaymentIntent.create─►│
   │◄─── client_secret ─────────┤◄────────────────────────────┤
   │                           │                      │
   ├─stripe.confirmPayment() ──────────────────────────────────►│
   │                           │◄─── webhook (succeeded) ──────┤
   │                           │  project.deposit_paid = True  │
   │                           │                      │
   │   (client views demo)     │                      │
   │                           │                      │
   ├─POST /api/payments/final ──►─stripe.PaymentIntent.create─►│
   │◄─── client_secret ─────────┤◄────────────────────────────┤
   ├─stripe.confirmPayment() ──────────────────────────────────►│
   │                           │◄─── webhook (succeeded) ──────┤
   │                           │  project.final_paid = True    │
```

Stripe webhook signature verification uses `STRIPE_WEBHOOK_SECRET`. In dev mode (secret not set), the webhook trusts the payload without verification.

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

Each `task_manager` is a fasta2a async context that must be entered before the app handles any A2A requests. The nesting order is arbitrary but must be symmetric on exit.

---

## LLM Provider Abstraction

`base_agent.py:make_model()` constructs a `LiteLLMModel` from three env vars:

| Var | Example |
|-----|---------|
| `PUTER_MODEL` | `openai/claude-sonnet-4-5` |
| `PUTER_AUTH_TOKEN` | Puter session token |
| `PUTER_API_BASE` | `https://api.puter.com/puterai/openai/v1` |

`custom_llm_provider="openai"` is hardcoded because Puter exposes an OpenAI-compatible endpoint. Switching providers means updating only `make_model()`.

`pydantic-ai-litellm` bridges pydantic-ai's tool spec to LiteLLM's format automatically — you do not need to manually convert tool schemas.

---

## Adding a New Agent

1. Create `src/agent_puter/swarm/my_agent.py` following the three-step pattern above.
2. In `main.py`:
   - Import `my_agent, my_app as _my_app`
   - Add `async with _my_app.task_manager:` to the lifespan nesting
   - Add `Mount("/my-agent", app=_my_app)` to routes
   - Add an entry to the health endpoint's `agents` list
3. In `agency.py`, add `"my_agent": f"{BASE_URL}/my-agent"` to `_AGENT_URLS`.
