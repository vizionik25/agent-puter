# API Reference

---

## REST API

Base URL: `http://localhost:9999` (configurable via `NEXT_PUBLIC_API_URL`)

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

**Path params:** `session_id` — from `/start`

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

**Side effects:** Creates `Project` and stub `Proposal` in the in-memory store.

**Response `200`**

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | string | |
| `project_id` | string | Newly created project UUID |
| `status` | `"complete"` | |

**Errors:** `404` session not found

---

### Projects

#### `GET /api/projects/{project_id}`

Poll for project status, task progress, and payment flags. Used by the status dashboard.

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

Admin endpoint — set the live deliverable URL for a project.

**Request body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `demo_url` | string | yes | Non-empty URL or text content |

**Response `200`**

| Field | Type | Description |
|-------|------|-------------|
| `project_id` | string | |
| `demo_url` | string | |

**Errors:** `400` invalid body or empty `demo_url` · `404` project not found

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
On success for `payment_type=final`: sets `project.final_paid = True`.

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

### Health

#### `GET /` · `GET /health`

Returns swarm status and all available endpoints.

**Response `200`:** JSON listing all agent A2A paths and API entry points.

---

## Agent A2A Endpoints

Each agent exposes the fasta2a A2A protocol at its mount path. All sub-paths are handled by the fasta2a ASGI app.

| Mount | Agent | Docs UI |
|-------|-------|---------|
| `/` | CEO Agent | `/docs` |
| `/ceo/` | CEO Agent (alias) | `/ceo/docs` |
| `/sales/` | Sales Agent | `/sales/docs` |
| `/pm/` | PM Agent | `/pm/docs` |
| `/product-manager/` | Product Manager Agent | `/product-manager/docs` |
| `/researcher/` | Researcher Agent | `/researcher/docs` |
| `/engineer/` | Engineer Agent | `/engineer/docs` |
| `/qa/` | QA Agent | `/qa/docs` |

Standard A2A paths provided by fasta2a at each mount:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/{mount}/.well-known/agent-card.json` | Agent metadata |
| `GET` | `/{mount}/docs` | Interactive docs UI |
| `POST` | `/{mount}/run` | Send A2A message |

---

## Python Modules

### `base_agent` — `src/agent_puter/swarm/base_agent.py`

#### `make_model() → LiteLLMModel`

Builds a `LiteLLMModel` from `PUTER_MODEL`, `PUTER_AUTH_TOKEN`, `PUTER_API_BASE` environment variables. Raises `EnvironmentError` if any are missing.

---

### `models` — `src/agent_puter/swarm/models.py`

#### `TaskStatus` (str, Enum)

`PENDING · IN_PROGRESS · REVIEW · DONE · FAILED`

#### `ProjectStatus` (str, Enum)

`INTAKE · PLANNING · EXECUTION · QA · DELIVERED · CANCELLED`

#### `Task` (BaseModel)

| Field | Type | Default |
|-------|------|---------|
| `id` | `str` | `uuid4()` |
| `title` | `str` | required |
| `description` | `str` | required |
| `assigned_to` | `Optional[str]` | `None` |
| `status` | `TaskStatus` | `PENDING` |
| `output` | `Optional[str]` | `None` |
| `qa_feedback` | `Optional[str]` | `None` |
| `retry_count` | `int` | `0` |
| `created_at` | `datetime` | `utcnow()` |
| `updated_at` | `datetime` | `utcnow()` |

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
| `payment_structure` | `str` | `""` |
| `created_at` | `datetime` | `utcnow()` |

#### `Project` (BaseModel)

| Field | Type | Default |
|-------|------|---------|
| `id` | `str` | `uuid4()` |
| `name` | `str` | required |
| `description` | `str` | required |
| `client_id` | `str` | required |
| `status` | `ProjectStatus` | `INTAKE` |
| `tasks` | `list[Task]` | `[]` |
| `budget_tokens` | `int` | `100_000` |
| `tokens_used` | `int` | `0` |
| `proposal` | `Optional[Proposal]` | `None` |
| `total_price_usd` | `float` | `0.0` |
| `deposit_paid` | `bool` | `False` |
| `final_paid` | `bool` | `False` |
| `demo_url` | `Optional[str]` | `None` |
| `stripe_deposit_intent_id` | `Optional[str]` | `None` |
| `stripe_final_intent_id` | `Optional[str]` | `None` |
| `created_at` | `datetime` | `utcnow()` |
| `updated_at` | `datetime` | `utcnow()` |

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

### `agency` — `src/agent_puter/swarm/agency.py`

#### `Agency`

```python
Agency(deps: AgencyDeps)
```

##### `async handle_client_request(request_text: str, client_id: str) → dict`

Runs the full intake loop (Sales → CEO budget → PM tasks). Returns `{ project_id, status, task_count }`.

##### `async _process_project(project: Project) → None`

Runs execution → QA loop for all pending tasks. Updates `project.status` to `DELIVERED` or `QA`.

##### `async _execute_task(task: Task, project: Project) → None`

Executes a single task with QA retry loop (up to `max_qa_retries`). Escalates to CEO on exhaustion.

#### `async _call_agent(base_url: str, prompt: str) → str`

Module-level helper. Sends a prompt via A2A and returns the response text (empty string on failure).

#### `_text_message(text: str) → dict`

Builds a minimal A2A message envelope with a single `TextPart`.

#### `_extract_json(text: str) → Optional[dict]`

Extracts the first JSON object from a string. Returns `None` if none found or invalid JSON.

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

---

### Agent Tools

#### CEO Agent tools — `ceo_agent.py`

##### `allocate_budget(project_id: str, requested_tokens: int) → str`
Returns JSON with `approved_tokens` (capped at 100,000).

##### `approve_delivery(project_id: str, summary: str) → str`
Returns JSON with `status: "approved"`.

##### `publish_goal(goal: str) → str`
Returns JSON with `status: "published"`.

---

#### Sales Agent tools — `sales_agent.py`

##### `create_project_brief(client_id: str, request_text: str, deliverables: str, constraints: str) → str`
Returns JSON brief with parsed deliverables list, constraints list, and `estimated_tokens`.

##### `send_proposal(client_id: str, brief_summary: str, price_estimate: str) → str`
Returns JSON with `status: "proposal_sent"`.

---

#### PM Agent tools — `pm_agent.py`

##### `create_task_list(project_id: str, project_description: str) → str`
Returns JSON `{ project_id, tasks: [{ title, description, assigned_to, dependencies }] }`.

##### `assign_task(task_id: str, agent_role: str) → str`
Valid roles: `engineer · researcher · qa · copywriter · ceo`. Returns assignment confirmation JSON.

##### `update_task_status(task_id: str, status: str, output_summary: str = "") → str`
Valid statuses: `pending · in_progress · review · done · failed`.

##### `escalate_to_ceo(project_id: str, reason: str) → str`
Returns JSON with `escalated: true`.

---

#### Product Manager Agent tools — `product_manager_agent.py`

##### `write_user_stories(project_id: str, business_goal: str, target_users: str) → str`
Returns JSON `{ project_id, user_stories: [{ id, story, priority, acceptance_criteria, estimated_effort }] }`.

##### `prioritize_features(project_id: str, features: str, constraint: str = "time") → str`
`features` is newline-separated. `constraint` must be `"time"`, `"budget"`, or `"scope"`. Returns JSON ranked feature list with rationale.

---

#### Engineer Agent tools — `engineer_agent.py`

##### `write_code(filename: str, language: str, description: str) → str`
Records code generation intent. Returns JSON with `status: "code_generation_requested"`.

##### `run_tests(test_command: str, working_directory: str = ".") → str`
Executes shell command (60s timeout). Returns JSON with `exit_code`, `stdout` (2000 char cap), `stderr` (1000 char cap), `passed`.

##### `read_file(filepath: str) → str`
Returns JSON with `filepath` and `content` (10,000 char cap). Returns `{ error }` on failure.

##### `write_file(filepath: str, content: str) → str`
Creates parent directories as needed. Returns JSON with `bytes_written` and `status: "ok"`.

---

#### Researcher Agent tools — `researcher_agent.py`

##### `web_search(query: str, max_results: int = 5) → str`
Returns JSON `{ query, results: [{ title, url, snippet }] }`. Placeholder in current implementation — wire to SerpAPI / Brave Search for production.

##### `summarize_docs(urls: str, focus: str) → str`
`urls` is comma-separated. Returns JSON with `urls`, `focus`, `summary`. Placeholder — integrate Puter browser SDK for production.

---

#### QA Agent tools — `qa_agent.py`

##### `review_output(task_id: str, task_description: str, output: str) → str`
Records review intent. PASS/FAIL verdict is in the agent's response text, not the tool return value.

##### `check_standards(code: str, language: str = "python") → str`
Returns JSON `{ language, function_count, violations: string[], clean: bool }`.  
Checks for: missing docstrings, missing type hints, `eval()` on untrusted input.

---

### `api/_store` — `src/agent_puter/swarm/api/_store.py`

Module-level singletons:

```python
sessions: dict[str, ConsultSession]   # keyed by session UUID
projects: dict[str, Project]          # keyed by project UUID
```

Both are plain `dict` — no thread locks, no persistence. Reset on every process restart.

---

## Frontend TypeScript Client

**File:** `frontend/lib/api.ts`  
**Base URL:** `process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:9999"`

#### `req<T>(path: string, options?: RequestInit): Promise<T>`

Generic fetch wrapper. Throws `Error("API {status}: {text}")` on non-2xx responses.

#### Consultation functions

| Function | Returns |
|----------|---------|
| `consultStart(body)` | `ConsultStartResponse` |
| `consultMessage(id, body)` | `ConsultMessageResponse` |
| `consultComplete(id)` | `{ session_id, project_id, status }` |
| `consultGet(id)` | `ConsultSession` |

#### Project functions

| Function | Returns |
|----------|---------|
| `projectGet(id)` | `Project` |
| `proposalGet(id)` | `Proposal` |
| `demoGet(id)` | `{ demo_url: string }` |

#### Payment functions

| Function | Returns |
|----------|---------|
| `depositIntent(body)` | `{ client_secret, intent_id }` |
| `finalIntent(body)` | `{ client_secret, intent_id }` |
| `paymentStatus(id)` | `PaymentStatus` |
