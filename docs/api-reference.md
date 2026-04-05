# API Reference

---

## REST API

Base URL: `http://localhost:9999` (configurable via `NEXT_PUBLIC_API_URL`)

All endpoints return JSON. Errors always include an `"error"` string field.

---

### Authentication

GitHub OAuth 2.0. The session is maintained via an httpOnly cookie (`ap_session`).

#### `GET /api/auth/github`

Redirect the browser to GitHub's OAuth consent screen. Sets a CSRF state cookie (`ap_oauth_state`, 5-minute TTL).

**Response:** `302` redirect to `https://github.com/login/oauth/authorize`

---

#### `GET /api/auth/callback`

OAuth callback. Exchanges the authorization code for an access token, fetches the GitHub user profile, upserts the `User` record in the store, and sets the session cookie.

**Query params:** `code` (string), `state` (string — must match `ap_oauth_state` cookie)

**Response:** `302` redirect to `/dashboard`

**Errors:** `400` missing code/state or state mismatch

---

#### `GET /api/auth/me`

Return the currently authenticated user's profile.

**Response `200`**

| Field | Type | Description |
|-------|------|-------------|
| `github_id` | string | GitHub user ID |
| `login` | string | GitHub username |
| `name` | string \| null | Display name |
| `email` | string \| null | Primary email |
| `avatar_url` | string | GitHub avatar URL |
| `tier` | string | Subscription tier (`"free"`, `"starter"`, `"pro"`, `"business"`) |
| `credits` | number | Current credit balance |

**Errors:** `401` no valid session cookie

---

#### `POST /api/auth/logout`

Clear the session cookie.

**Response `200`:** `{ "ok": true }`

---

### Consultation

#### `POST /api/consult/start`

Create a consultation session and receive the Sales Agent's opening message.

**Request body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `client_name` | string | yes | Client display name |
| `client_email` | string | yes | Client email — used as `client_id` |
| `initial_message` | string | no | Client's opening project description |

**Response `200`**

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | string | UUID for subsequent calls |
| `reply` | string | Sales Agent's opening text |
| `status` | `"active"` | Always `"active"` on start |

**Errors:** `400` invalid body · `422` missing required field

---

#### `POST /api/consult/{session_id}/message`

Send a follow-up message and receive the agent's reply.

**Request body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message` | string | yes | User message text |

**Response `200`**

| Field | Type | Description |
|-------|------|-------------|
| `reply` | string | Agent reply text |
| `status` | `"active"` \| `"complete"` | Session state |
| `project_id` | string \| null | Set when session transitions to complete |

**Errors:** `400` already complete or invalid body · `404` session not found · `422` missing `message`

---

#### `POST /api/consult/{session_id}/stream`

Send a message and receive the reply as a Server-Sent Events stream.

**Request body:** same as `/message` — `{ "message": string }`

**Response:** `text/event-stream`

```
data: {"type": "chunk", "text": "Hello"}
data: {"type": "chunk", "text": " there"}
data: {"type": "done",  "status": "active"}
```

Event types: `chunk` (text delta), `done` (stream finished, includes `status`), `error` (message in `message` field).

**Errors:** `400` invalid body · `404` session not found

---

#### `GET /api/consult/{session_id}`

Fetch full consultation transcript.

**Response `200`**

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | string | |
| `client_name` | string | |
| `client_email` | string | |
| `messages` | `ConsultMessage[]` | Ordered conversation history |
| `project_id` | string \| null | |
| `status` | `"active"` \| `"complete"` | |

`ConsultMessage`: `{ role: "user"|"agent", content: string, timestamp: string }`

**Errors:** `404` session not found

---

#### `POST /api/consult/{session_id}/complete`

Mark session complete and trigger the agency loop (Sales → CEO → PM → tasks).

**Side effects:** Creates `Project` and `Proposal` in the store. Sends proposal-ready email if SMTP is configured.

**Response `200`**

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | string | |
| `project_id` | string | Newly created project UUID |
| `status` | `"complete"` | |

**Errors:** `404` session not found

---

### Projects

#### `GET /api/projects`

List all projects belonging to the currently authenticated user. Requires a valid session cookie.

**Response `200`:** Array of `ProjectSummary`

| Field | Type | Description |
|-------|------|-------------|
| `project_id` | string | |
| `name` | string | |
| `status` | string | Current lifecycle phase |
| `deposit_paid` | bool | |
| `final_paid` | bool | |
| `total_price_usd` | number | |
| `demo_available` | bool | True when demo URL is set and deposit is paid |
| `github_repo_url` | string \| null | Set after a successful push-github |
| `progress` | `{ done: number, total: number }` | Task completion counts |
| `created_at` | string | ISO 8601 |
| `updated_at` | string | ISO 8601 |

**Errors:** `401` not authenticated

---

#### `GET /api/projects/{project_id}`

Poll for project status, task progress, and payment flags. Used by the status dashboard (polls every 8 seconds).

**Response `200`**

| Field | Type | Description |
|-------|------|-------------|
| `project_id` | string | |
| `name` | string | |
| `status` | `ProjectStatus` | Current lifecycle phase |
| `deposit_paid` | bool | |
| `final_paid` | bool | |
| `total_price_usd` | number | |
| `tasks` | `TaskSummary[]` | See below |
| `progress` | `{ done: number, total: number }` | |
| `demo_available` | bool | True when `demo_url` is set and deposit is paid |
| `deployment_status` | string \| null | `"pending"` \| `"deployed"` \| `"failed"` |
| `llm_cost_usd` | number | Estimated LLM spend so far |
| `created_at` | string | ISO 8601 |
| `updated_at` | string | ISO 8601 |

`TaskSummary`: `{ id, title, status: TaskStatus, assigned_to: string|null }`

`ProjectStatus` values: `intake · planning · execution · qa · delivered · cancelled`

`TaskStatus` values: `pending · in_progress · review · done · failed`

**Errors:** `404` project not found

---

#### `GET /api/projects/{project_id}/proposal`

Fetch the full proposal. Available after `/consult/{id}/complete` returns.

**Response `200`**

| Field | Type | Description |
|-------|------|-------------|
| `project_id` | string | |
| `project_name` | string | |
| `problem_statement` | string | |
| `solution_overview` | string | |
| `implementation_plan` | string | |
| `deliverables` | `string[]` | |
| `estimated_hours` | number | |
| `delivery_eta_days` | number | |
| `total_price_usd` | number | |
| `deposit_amount_usd` | number | 20% of total |
| `final_amount_usd` | number | 80% of total |
| `payment_structure` | string | Human-readable payment terms |
| `deposit_paid` | bool | |
| `final_paid` | bool | |

**Errors:** `404` project not found or proposal not yet ready

---

#### `POST /api/projects/{project_id}/demo-url`

Set the live deliverable URL for a project.

**Request body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `demo_url` | string | yes | Non-empty URL or text content |

**Side effects:** Sends demo-ready email to client if SMTP is configured.

**Response `200`**

| Field | Type | Description |
|-------|------|-------------|
| `project_id` | string | |
| `demo_url` | string | |

**Errors:** `400` invalid body · `422` empty `demo_url` · `404` project not found

---

#### `GET /api/projects/{project_id}/demo`

Fetch the demo URL. Requires deposit to be paid.

**Response `200`**

| Field | Type | Description |
|-------|------|-------------|
| `project_id` | string | |
| `demo_url` | string | |
| `final_paid` | bool | Whether balance has been paid |

**Errors:** `403` deposit not paid · `404` project not found or demo URL not set

---

#### `GET /api/projects/{project_id}/usage`

Fetch LLM token usage and estimated cost for a project.

**Response `200`**

| Field | Type | Description |
|-------|------|-------------|
| `project_id` | string | |
| `tokens_used` | number | Total tokens across all A2A calls |
| `llm_requests` | number | Total A2A calls made |
| `llm_cost_usd` | number | Estimated total USD cost |
| `budget_tokens` | number | Token budget allocated by CEO |
| `budget_remaining` | number | `max(0, budget_tokens - tokens_used)` |
| `task_breakdown` | `TaskUsage[]` | Per-task detail |

`TaskUsage`: `{ task_id, title, tokens_used, cost_usd }`

**Errors:** `404` project not found

---

#### `POST /api/projects/{project_id}/push-github`

Push all files from `deliveries/{project_id}/` to a new public GitHub repository in the authenticated user's account. Requires a valid session cookie.

The repo is named `ap-{slugified-name}-{project_id[:8]}`. If the repo already exists, files are created or updated in place.

**Response `200`**

| Field | Type | Description |
|-------|------|-------------|
| `project_id` | string | |
| `repo_url` | string | HTML URL of the created GitHub repository |

**Errors:** `401` not authenticated · `404` project not found · `400` no GitHub access token on file · `502` GitHub API error

---

### Payments

#### `POST /api/payments/deposit`

Create a Stripe PaymentIntent for the 20% deposit.

**Request body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `project_id` | string | yes | |

**Response `200`**

| Field | Type | Description |
|-------|------|-------------|
| `client_secret` | string | Pass to `stripe.confirmPayment()` |
| `amount_usd` | number | Deposit amount |
| `project_id` | string | |

**Side effects:** Sets `project.stripe_deposit_intent_id`.

**Errors:** `400` already paid, no proposal, or amount < $0.50 · `404` project not found · `503` Stripe not configured

---

#### `POST /api/payments/final`

Create a Stripe PaymentIntent for the 80% final balance. Requires deposit to be paid first.

**Request body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `project_id` | string | yes | |

**Response `200`**

| Field | Type | Description |
|-------|------|-------------|
| `client_secret` | string | Pass to `stripe.confirmPayment()` |
| `amount_usd` | number | Final balance amount |
| `project_id` | string | |

**Side effects:** Sets `project.stripe_final_intent_id`.

**Errors:** `400` deposit not paid, already paid, or no proposal · `404` project not found · `503` Stripe not configured

---

#### `POST /api/payments/webhook`

Stripe webhook receiver for `payment_intent.succeeded` events.

Verified via `STRIPE_WEBHOOK_SECRET` when set; trusts payload in dev mode.

On success for `payment_type=deposit`: sets `project.deposit_paid = True`.  
On success for `payment_type=final`: sets `project.final_paid = True`, sends delivery-complete email.

**Response `200`:** `{ "received": true }`

**Errors:** `400` invalid signature or malformed payload

---

#### `GET /api/payments/{project_id}/status`

**Response `200`**

| Field | Type | Description |
|-------|------|-------------|
| `project_id` | string | |
| `deposit_paid` | bool | |
| `final_paid` | bool | |
| `total_price_usd` | number | |
| `deposit_amount_usd` | number | |
| `final_amount_usd` | number | |

**Errors:** `404` project not found

---

### Admin

All `/api/admin/*` routes require the `X-Admin-Key: <ADMIN_API_KEY>` header.  
Returns `503` if `ADMIN_API_KEY` is not set; `401` if the key is wrong.

---

#### `GET /api/admin/projects`

List all projects with aggregate stats. Supports `?owner_id=` query param filter.

**Response `200`**

| Field | Type | Description |
|-------|------|-------------|
| `projects` | `AdminProjectSummary[]` | See below |
| `total` | number | |

`AdminProjectSummary` fields: `project_id, name, client_id, owner_id, status, deposit_paid, final_paid, total_price_usd, llm_cost_usd, llm_requests, tokens_used, task_count, tasks_done, demo_url, deployment_status, created_at, updated_at`

---

#### `GET /api/admin/sessions`

List all consultation sessions. Supports `?owner_id=` query param filter.

**Response `200`:** `{ sessions: AdminSessionSummary[], total: number }`

`AdminSessionSummary` fields: `session_id, client_name, client_email, owner_id, status, project_id, message_count, created_at, updated_at`

---

#### `GET /api/admin/projects/{project_id}`

Full project detail including task outputs, QA feedback, and cost breakdown.

**Response `200`:** All `Project` fields plus full `tasks[]` array with `output` and `qa_feedback`.

**Errors:** `404` project not found

---

#### `POST /api/admin/projects/{project_id}/demo-url`

Set the demo URL (admin-gated version, no email notification).

**Request body:** `{ "demo_url": string }`

**Response `200`:** `{ "project_id": string, "demo_url": string }`

---

#### `POST /api/admin/projects/{project_id}/status`

Manually override a project's lifecycle status.

**Request body:** `{ "status": string }`

Valid values: `intake · planning · execution · qa · delivered · cancelled`

**Response `200`:** `{ "project_id": string, "status": string }`

**Errors:** `422` invalid status value

---

#### `GET /api/admin/logs`

Return recent server log entries from the in-process ring buffer (max 500).

**Query params:** `?limit=100` (default 100, max 500)

**Response `200`**

```json
{
  "logs": [
    {
      "timestamp": "2025-01-01T00:00:00",
      "level": "info",
      "source": "agency",
      "message": "Task completed",
      "project_id": "abc-123"
    }
  ],
  "total": 42
}
```

---

### Health

#### `GET /` · `GET /health`

Returns swarm status, feature flags, and all available endpoints.

**Response `200`** includes: `status`, `agents[]`, `storage_backend`, `mcp_enabled`, feature endpoint paths.

---

## Static File Delivery

#### `GET /deliveries/{project_id}/{filename}`

Serves files written by the Engineer agent's `deploy_to_sandbox` tool. Mounted as a `StaticFiles` handler at `/deliveries/`.

---

## Agent A2A Endpoints

Each agent exposes the fasta2a A2A protocol at its mount path.

| Mount | Agent |
|-------|-------|
| `/` | CEO Agent |
| `/sales/` | Sales Agent |
| `/pm/` | PM Agent |
| `/product-manager/` | Product Manager Agent |
| `/researcher/` | Researcher Agent |
| `/engineer/` | Engineer Agent |
| `/qa/` | QA Agent |

Standard A2A paths at each mount:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/{mount}/.well-known/agent-card.json` | Agent metadata |
| `GET` | `/{mount}/docs` | Interactive docs UI |
| `POST` | `/{mount}/run` | Send A2A message |

---

## Python Modules

### `base_agent` — `src/agent_puter/swarm/base_agent.py`

#### `make_model() → LiteLLMModel`

Builds a `LiteLLMModel` from `PUTER_MODEL`, `PUTER_AUTH_TOKEN`, `PUTER_API_BASE`. Raises `EnvironmentError` if any are missing. Sets `custom_llm_provider="openai"` for Puter's OpenAI-compatible endpoint.

---

### `models` — `src/agent_puter/swarm/models.py`

#### `TaskStatus` (str, Enum)

`PENDING · IN_PROGRESS · REVIEW · DONE · FAILED`

#### `ProjectStatus` (str, Enum)

`INTAKE · PLANNING · EXECUTION · QA · DELIVERED · CANCELLED`

#### `User` (BaseModel)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `github_id` | `str` | required | GitHub user ID — used as the store key |
| `login` | `str` | required | GitHub username |
| `name` | `Optional[str]` | `None` | Display name |
| `email` | `Optional[str]` | `None` | Primary GitHub email |
| `avatar_url` | `str` | `""` | GitHub avatar URL |
| `access_token` | `str` | `""` | OAuth access token (repo scope) |
| `tier` | `str` | `"free"` | Subscription tier |
| `credits` | `float` | `0.0` | Current credit balance |
| `created_at` | `datetime` | `utcnow()` | |
| `updated_at` | `datetime` | `utcnow()` | |

#### `Task` (BaseModel)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `id` | `str` | `uuid4()` | |
| `title` | `str` | required | |
| `description` | `str` | required | |
| `assigned_to` | `Optional[str]` | `None` | Agent role name |
| `status` | `TaskStatus` | `PENDING` | |
| `output` | `Optional[str]` | `None` | Text produced by execution agent |
| `qa_feedback` | `Optional[str]` | `None` | QA reviewer's comments |
| `retry_count` | `int` | `0` | Incremented each QA failure |
| `tokens_used` | `int` | `0` | LLM tokens for this task |
| `cost_usd` | `float` | `0.0` | Estimated USD cost for this task |
| `created_at` | `datetime` | `utcnow()` | |
| `updated_at` | `datetime` | `utcnow()` | |

#### `Proposal` (BaseModel)

| Field | Type | Default |
|-------|------|---------|
| `problem_statement` | `str` | `""` |
| `solution_overview` | `str` | `""` |
| `implementation_plan` | `str` | `""` |
| `deliverables` | `list[str]` | `[]` |
| `estimated_hours` | `int` | `0` |
| `delivery_eta_days` | `int` | `0` |
| `total_price_usd` | `float` | `0.0` |
| `deposit_amount_usd` | `float` | `0.0` |
| `final_amount_usd` | `float` | `0.0` |
| `payment_structure` | `str` | 20/80 terms |
| `created_at` | `datetime` | `utcnow()` |

#### `Project` (BaseModel)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `id` | `str` | `uuid4()` | |
| `name` | `str` | required | |
| `description` | `str` | required | |
| `client_id` | `str` | required | Client email address |
| `owner_id` | `str` | `"default"` | Tenant namespace |
| `github_user_id` | `Optional[str]` | `None` | GitHub user ID of the authenticated owner |
| `github_repo_url` | `Optional[str]` | `None` | HTML URL of the pushed GitHub repository |
| `status` | `ProjectStatus` | `INTAKE` | |
| `tasks` | `list[Task]` | `[]` | |
| `budget_tokens` | `int` | `100_000` | CEO-allocated token budget |
| `tokens_used` | `int` | `0` | Cumulative tokens across all calls |
| `llm_requests` | `int` | `0` | Total A2A calls made |
| `llm_cost_usd` | `float` | `0.0` | Estimated total LLM cost |
| `proposal` | `Optional[Proposal]` | `None` | |
| `total_price_usd` | `float` | `0.0` | Client-facing price |
| `deposit_paid` | `bool` | `False` | |
| `final_paid` | `bool` | `False` | |
| `demo_url` | `Optional[str]` | `None` | |
| `deployment_status` | `Optional[str]` | `None` | `"pending"` \| `"deployed"` \| `"failed"` |
| `stripe_deposit_intent_id` | `Optional[str]` | `None` | |
| `stripe_final_intent_id` | `Optional[str]` | `None` | |
| `created_at` | `datetime` | `utcnow()` | |
| `updated_at` | `datetime` | `utcnow()` | |

#### `ConsultMessage` (BaseModel)

| Field | Type |
|-------|------|
| `role` | `str` — `"user"` or `"agent"` |
| `content` | `str` |
| `timestamp` | `datetime` |

#### `ConsultSession` (BaseModel)

| Field | Type | Default |
|-------|------|---------|
| `id` | `str` | `uuid4()` |
| `client_name` | `str` | required |
| `client_email` | `str` | required |
| `owner_id` | `str` | `"default"` |
| `github_user_id` | `Optional[str]` | `None` |
| `messages` | `list[ConsultMessage]` | `[]` |
| `project_id` | `Optional[str]` | `None` |
| `status` | `str` | `"active"` |
| `created_at` | `datetime` | `utcnow()` |
| `updated_at` | `datetime` | `utcnow()` |

#### `AgencyDeps` (BaseModel)

| Field | Type | Default |
|-------|------|---------|
| `puter_token` | `Optional[str]` | `None` |
| `model_name` | `Optional[str]` | `None` |
| `base_url` | `Optional[str]` | `None` |
| `projects` | `dict[str, Project]` | `{}` |
| `sessions` | `dict[str, ConsultSession]` | `{}` |
| `max_qa_retries` | `int` | `5` |

#### `ReviewResult` (BaseModel)

| Field | Type | Default |
|-------|------|---------|
| `task_id` | `str` | required |
| `passed` | `bool` | required |
| `feedback` | `str` | required |
| `reviewer` | `str` | `"qa_agent"` |

---

### `api/store` — `src/agent_puter/swarm/api/store.py`

Pluggable async persistence layer. Backend selected at import time via `STORAGE_BACKEND`.

#### `AbstractStore` (ABC)

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_session` | `(session_id: str) → Optional[ConsultSession]` | |
| `set_session` | `(session: ConsultSession) → None` | |
| `list_sessions` | `(owner_id: Optional[str] = None) → list[ConsultSession]` | Sorted newest-first |
| `get_project` | `(project_id: str) → Optional[Project]` | |
| `set_project` | `(project: Project) → None` | |
| `list_projects` | `(owner_id: Optional[str] = None) → list[Project]` | Sorted newest-first |

All methods are `async`.

#### `MemoryStore(AbstractStore)`

In-process dict store with `asyncio.Lock`. Data lost on restart. Default backend.

#### `JsonFileStore(AbstractStore)`

Persists to `STORAGE_PATH` (default `./data/store.json`) as a single JSON file. Writes atomically via a `.tmp` rename. Loads lazily on first access.

Constructor: `JsonFileStore(path: str = "./data/store.json")`

#### `PuterKVStore(AbstractStore)`

Persists to Puter's cloud KV API. Uses `PUTER_AUTH_TOKEN` for auth and `PUTER_KV_BASE` for the endpoint base (default `https://api.puter.com/kv`). Keys are namespaced as `session:{id}` and `project:{id}`.

Private helpers: `_kv_get(key)`, `_kv_set(key, value)`, `_kv_list(pattern)` — each opens an `httpx.AsyncClient` with a 10-second timeout.

#### `make_store() → AbstractStore`

Factory that reads `STORAGE_BACKEND` and returns the appropriate instance. Called once at module import to produce the `store` singleton.

#### `store: AbstractStore`

Module-level singleton used by all route handlers via `from . import _store` then `await _store.store.get_*()`.

---

### `middleware` — `src/agent_puter/swarm/middleware.py`

#### `resolve_tenant(request: Request) → str`

Extracts `owner_id` from the request. Checks `X-Agency-Key` header, then `Authorization: Bearer <key>`. Returns the mapped tenant ID from `AGENCY_API_KEYS`, or `"default"` if no valid key is found or `AGENCY_API_KEYS` is unset.

#### `_load_key_map() → dict[str, str]`

`@lru_cache(maxsize=1)` function that parses `AGENCY_API_KEYS=key1:tenant1,key2:tenant2` into a dict. Called by `resolve_tenant`.

---

### `notifications` — `src/agent_puter/swarm/notifications.py`

All functions are synchronous and fire-and-forget — exceptions are logged, never re-raised. All silently no-op when `SMTP_HOST`, `SMTP_USER`, or `SMTP_PASS` are not set.

#### `notify_proposal_ready(project: Project, session: ConsultSession) → None`

Sends HTML email to `session.client_email` with proposal price, deposit amount, delivery estimate, and a link to `/proposal/{project.id}`.

#### `notify_demo_ready(project: Project, client_email: str, client_name: str) → None`

Sends HTML email notifying the client their demo is live, with a link to `/demo/{project.id}`.

#### `notify_delivery_complete(project: Project, client_email: str, client_name: str) → None`

Sends HTML email confirming full delivery after final payment, with a link to `/status/{project.id}`.

#### `_send(to, subject, body_html, body_text) → None`

Internal SMTP sender. Uses STARTTLS on `SMTP_HOST:SMTP_PORT` (default 587). Logs success and failures to stdout.

---

### `admin` — `src/agent_puter/swarm/api/admin.py`

#### `log_event(level: str, source: str, message: str, project_id: str = "") → None`

Appends an entry to `_LOG_BUFFER` (in-process `deque(maxlen=500)`). Called throughout the codebase. Fields: `timestamp`, `level`, `source`, `message`, `project_id`.

#### `_check_auth(request: Request) → bool`

Returns `True` if `X-Admin-Key` header matches `ADMIN_API_KEY` env var.

Route handlers: `list_projects`, `list_sessions`, `get_project_detail`, `admin_set_demo_url`, `admin_set_status`, `get_logs` — see [Admin REST routes](#admin) above.

---

### `agency` — `src/agent_puter/swarm/agency.py`

#### `Agency`

```python
Agency(deps: AgencyDeps)
```

##### `async handle_client_request(request_text: str, client_id: str) → dict`

Runs the full intake loop (Sales → CEO budget → PM tasks). Persists the project. Returns `{ project_id, status, task_count }`.

##### `async _process_project(project: Project) → None`

Runs execution → QA loop for all pending tasks. Updates project status to `DELIVERED` and calls `_auto_deploy()` when all tasks pass.

##### `async _execute_task(task: Task, project: Project) → None`

Executes a single task with QA retry loop (up to `max_qa_retries`). Escalates to CEO on exhaustion. Increments `task.tokens_used`, `task.cost_usd`, `project.llm_requests`, `project.tokens_used`, `project.llm_cost_usd` after each A2A call.

##### `async _auto_deploy(project: Project) → None`

Generates an HTML summary of all task outputs. Calls Engineer agent via A2A to invoke `deploy_to_sandbox`. Falls back to writing `deliveries/{project_id}/index.html` directly. Sets `project.demo_url` and `project.deployment_status = "deployed"`.

#### `async _call_agent(base_url: str, prompt: str) → str`

Module-level helper. Sends prompt via `A2AClient` and returns response text. Handles both `Task` (reads `status.message.parts`) and `Message` (reads `parts` directly) response shapes. Returns empty string on failure.

#### `_text_message(text: str) → dict`

Builds a minimal A2A message envelope with a single `TextPart`.

#### `_extract_json(text: str) → Optional[dict]`

Extracts the first JSON object from a string. Returns `None` if not found or invalid.

#### `_estimate_call_cost(tokens: int) → float`

Returns `(tokens / 2 * INPUT_RATE + tokens / 2 * OUTPUT_RATE) / 1_000_000` using `_INPUT_COST_PER_MTOK = 3.0` and `_OUTPUT_COST_PER_MTOK = 15.0`.

#### `_AGENT_URLS: dict[str, str]`

```python
{
    "ceo":             "http://localhost:9999",
    "sales":           "http://localhost:9999/sales",
    "pm":              "http://localhost:9999/pm",
    "researcher":      "http://localhost:9999/researcher",
    "engineer":        "http://localhost:9999/engineer",
    "qa":              "http://localhost:9999/qa",
    "product_manager": "http://localhost:9999/product-manager",
}
```

#### `_AVG_TOKENS_PER_CALL: int = 2_000`

Fixed token estimate applied to each A2A call for cost tracking.

---

### Agent Tools

#### CEO Agent — `ceo_agent.py`

##### `allocate_budget(project_id: str, requested_tokens: int) → str`
Returns JSON with `approved_tokens` (capped at 100,000).

##### `approve_delivery(project_id: str, summary: str) → str`
Returns JSON with `status: "approved"`.

##### `publish_goal(goal: str) → str`
Returns JSON with `status: "published"`.

---

#### Sales Agent — `sales_agent.py`

##### `create_project_brief(client_id: str, request_text: str, deliverables: str, constraints: str) → str`
Returns JSON brief with parsed deliverables list, constraints list, and `estimated_tokens`.

##### `send_proposal(client_id: str, brief_summary: str, price_estimate: str) → str`
Returns JSON with `status: "proposal_sent"`.

---

#### PM Agent — `pm_agent.py`

##### `create_task_list(project_id: str, project_description: str) → str`
Returns JSON `{ project_id, tasks: [{ title, description, assigned_to, dependencies }] }`.

##### `assign_task(task_id: str, agent_role: str) → str`
Valid roles: `engineer · researcher · qa · copywriter · ceo`.

##### `update_task_status(task_id: str, status: str, output_summary: str = "") → str`
Valid statuses: `pending · in_progress · review · done · failed`.

##### `escalate_to_ceo(project_id: str, reason: str) → str`
Returns JSON with `escalated: true`.

---

#### Product Manager Agent — `product_manager_agent.py`

##### `write_user_stories(project_id: str, business_goal: str, target_users: str) → str`
Returns JSON `{ project_id, user_stories: [{ id, story, priority, acceptance_criteria, estimated_effort }] }`.

##### `prioritize_features(project_id: str, features: str, constraint: str = "time") → str`
`features` is newline-separated. `constraint` must be `"time"`, `"budget"`, or `"scope"`. Returns JSON ranked feature list with rationale.

---

#### Engineer Agent — `engineer_agent.py`

##### `write_code(filename: str, language: str, description: str) → str`
Records code generation intent. Returns JSON with `status: "code_generation_requested"`.

##### `run_tests(test_command: str, working_directory: str = ".") → str`
Executes shell command (60s timeout). Returns JSON with `exit_code`, `stdout` (2000 char cap), `stderr` (1000 char cap), `passed`.

##### `read_file(filepath: str) → str`
Returns JSON with `filepath` and `content` (10,000 char cap). Returns `{ error }` on failure.

##### `write_file(filepath: str, content: str) → str`
Creates parent directories as needed. Returns JSON with `bytes_written` and `status: "ok"`.

##### `deploy_to_sandbox(project_id: str, content: str, filename: str = "index.html") → str`
Writes `content` to `deliveries/{project_id}/{filename}`. Creates the directory if needed. Returns JSON with `status`, `url` (`/deliveries/{project_id}/{filename}`), and `bytes`.

MCP toolsets are attached when `MCP_SERVER_URL` is set — tools are exposed with the `mcp_` prefix.

---

#### Researcher Agent — `researcher_agent.py`

##### `web_search(query: str, max_results: int = 5) → str`
Returns JSON `{ query, results: [{ title, url, snippet }] }`. Placeholder implementation — wire to SerpAPI / Brave Search or set `MCP_SERVER_URL` for live results.

##### `summarize_docs(urls: str, focus: str) → str`
`urls` is comma-separated. Returns JSON with `urls`, `focus`, `summary`. Placeholder — integrate Puter browser SDK or an MCP server for live fetching.

MCP toolsets are attached when `MCP_SERVER_URL` is set — tools are exposed with the `mcp_` prefix.

---

#### QA Agent — `qa_agent.py`

##### `review_output(task_id: str, task_description: str, output: str) → str`
Records review intent. PASS/FAIL verdict is in the agent's response text, not the tool return value.

##### `check_standards(code: str, language: str = "python") → str`
Returns JSON `{ language, function_count, violations: string[], clean: bool }`.  
Checks for: missing docstrings, missing type hints, `eval()` on untrusted input.

---

### `api/_store` — `src/agent_puter/swarm/api/_store.py`

Re-exports the `store` singleton from `api/store.py`:

```python
from .store import store
```

All route handlers import via `from . import _store` and call `await _store.store.get_*()`.

---

## Frontend TypeScript Client

**File:** `frontend/lib/api.ts`  
**Base URL:** `process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:9999"`

#### `req<T>(path: string, options?: RequestInit): Promise<T>`

Generic fetch wrapper. Throws `Error("API {status}: {text}")` on non-2xx responses. Always sets `Content-Type: application/json`.

#### Consultation functions

| Function | Signature | Returns |
|----------|-----------|---------|
| `consultStart` | `(body: { client_name, client_email, initial_message })` | `ConsultStartResponse` |
| `consultMessage` | `(id, body: { message })` | `ConsultMessageResponse` |
| `consultComplete` | `(id)` | `{ session_id, project_id, status }` |
| `consultGet` | `(id)` | `ConsultSession` |
| `consultStream` | `(id, message, onChunk)` | `Promise<void>` |

#### `consultStream(id, message, onChunk)`

Reads SSE `text/event-stream` response chunk by chunk using `ReadableStream`. Calls `onChunk(text)` for each `type=chunk` event. Throws on `type=error` or non-2xx status. Silently skips partial JSON.

#### Project functions

| Function | Signature | Returns |
|----------|-----------|---------|
| `projectGet` | `(id)` | `Project` |
| `proposalGet` | `(id)` | `Proposal` |
| `demoGet` | `(id)` | `{ demo_url: string }` |
| `usageGet` | `(id)` | `UsageReport` |
| `myProjects` | `()` | `ProjectSummary[]` |
| `pushToGitHub` | `(projectId)` | `{ repo_url: string }` |

#### Auth functions — `lib/auth.ts`

| Function | Signature | Returns |
|----------|-----------|---------|
| `getMe` | `()` | `Promise<GitHubUser \| null>` |
| `loginWithGitHub` | `()` | `void` — redirects to `/api/auth/github` |
| `logout` | `()` | `Promise<void>` — POSTs to `/api/auth/logout`, redirects to `/` |

`GitHubUser`: `{ github_id, login, name: string|null, email: string|null, avatar_url, tier, credits }`

#### TypeScript interfaces

`ConsultMessage · ConsultSession · ConsultStartResponse · ConsultMessageResponse · Proposal · TaskItem · Project · ProjectSummary · UsageReport`

`UsageReport`: `{ project_id, tokens_used, llm_requests, llm_cost_usd, budget_tokens, budget_remaining, task_breakdown: Array<{ task_id, title, tokens_used, cost_usd }> }`

Note: The backend Stripe payment endpoints (`/api/payments/*`) are not currently called by the frontend. Credit deduction is handled entirely in `lib/billing.ts` client-side.
