"""
agency.py — Agency Orchestrator

The Agency class owns the autonomous business loop:
  Client Request → Sales → Project Brief → PM → Tasks → Execution → QA → Delivery

ALL agent calls go through the A2A protocol via fasta2a.A2AClient.
No direct pydantic-ai .run() calls — every agent is addressed by its HTTP URL.
"""
from __future__ import annotations

import json
import uuid
import asyncio
from datetime import datetime
from typing import Optional

from fasta2a.client import A2AClient

from .models import (
    AgencyDeps,
    Project,
    ProjectStatus,
    Task,
    TaskStatus,
)
from .ceo_agent import BASE_URL


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _text_message(text: str) -> dict:
    """Build a minimal A2A Message with a single TextPart.

    Args:
        text (str): The plain-text content for the message part.

    Returns:
        dict: A well-formed A2A message dict with role, kind, messageId,
            and a single text part.
    """
    return {
        "role": "user",
        "kind": "message",
        "messageId": str(uuid.uuid4()),
        "parts": [{"kind": "text", "text": text}],
    }


async def _call_agent(base_url: str, prompt: str) -> str:
    """
    Send a prompt to an agent via the A2A protocol and return the response text.

    Args:
        base_url: The base URL of the target agent (e.g. "http://localhost:9999/pm").
        prompt:   The plain-text prompt to send.

    Returns:
        str: The agent's concatenated text response, or an empty string on
            network or protocol failure.
    """
    client = A2AClient(base_url=base_url)
    try:
        response = await client.send_message(message=_text_message(prompt))
        result = response.get("result")  # type: ignore[union-attr]
        if result is None:
            return ""
        if "status" in result:
            msg = result["status"].get("message", {})
            parts = msg.get("parts", []) if msg else []
        else:
            parts = result.get("parts", [])
        texts = [p["text"] for p in parts if p.get("kind") == "text"]
        return "\n".join(texts)
    except Exception as exc:
        print(f"[Agency][A2A] Error calling {base_url}: {exc}")
        return ""


# ---------------------------------------------------------------------------
# Agent URL map
# ---------------------------------------------------------------------------

_AGENT_URLS: dict[str, str] = {
    "ceo":             f"{BASE_URL}",
    "sales":           f"{BASE_URL}/sales",
    "pm":              f"{BASE_URL}/pm",
    "researcher":      f"{BASE_URL}/researcher",
    "engineer":        f"{BASE_URL}/engineer",
    "qa":              f"{BASE_URL}/qa",
    "product_manager": f"{BASE_URL}/product-manager",
}

# Approximate cost per million tokens (USD) — update to match your model
_INPUT_COST_PER_MTOK = 3.0
_OUTPUT_COST_PER_MTOK = 15.0
# Rough token estimate per A2A call (prompt + response avg for planning calls)
_AVG_TOKENS_PER_CALL = 2_000


def _estimate_call_cost(tokens: int) -> float:
    """Estimate USD cost for a given token count (assumes 50/50 input/output split).

    Args:
        tokens (int): Total token count to cost (input + output combined).

    Returns:
        float: Estimated cost in USD based on the module-level per-million-token
            rates for input and output.
    """
    half = tokens / 2
    return (half * _INPUT_COST_PER_MTOK + half * _OUTPUT_COST_PER_MTOK) / 1_000_000


# ---------------------------------------------------------------------------
# Agency
# ---------------------------------------------------------------------------

class Agency:
    """
    Autonomous AI consulting agency orchestrator.

    All agent communication goes through the A2A protocol via A2AClient.
    Each agent is addressed by its mounted URL on the shared Starlette server.
    """

    def __init__(self, deps: AgencyDeps) -> None:
        """Initialize the Agency with its runtime dependency container.

        Args:
            deps (AgencyDeps): Container holding in-memory state (projects,
                sessions), LLM config, and QA retry limits.
        """
        self.deps = deps

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def handle_client_request(
        self,
        request_text: str,
        client_id: str,
    ) -> dict:
        """Intake a new client request and create a Project.

        Orchestrates four A2A calls in sequence:
        1. Sales agent parses the request and produces a project brief.
        2. CEO agent allocates a token budget.
        3. PM agent decomposes the brief into a task list.
        4. Project is stored in ``deps.projects`` and a summary is returned.

        Args:
            request_text (str): The raw client request describing the project.
            client_id (str): Unique identifier for the client (e.g. session ID
                or email).

        Returns:
            dict: A summary containing ``project_id`` (str), ``status``
                (ProjectStatus), and ``task_count`` (int).
        """
        print(f"[Agency] Received request from {client_id}: {request_text[:80]}...")

        # --- Step 1: Sales agent creates a project brief (A2A) ---
        brief_text = await _call_agent(
            _AGENT_URLS["sales"],
            f"Create a project brief for this client request:\n\n{request_text}",
        )
        print(f"[Agency][Sales→A2A] Brief: {brief_text[:200]}")

        # --- Step 2: CEO allocates budget (A2A) ---
        budget_text = await _call_agent(
            _AGENT_URLS["ceo"],
            "Allocate a token budget for a new mid-complexity project. "
            "Call allocate_budget with project_id='new' and requested_tokens=75000.",
        )
        print(f"[Agency][CEO→A2A] Budget: {budget_text[:200]}")

        # --- Step 3: Create the Project object ---
        project = Project(
            name=f"Project for {client_id}",
            description=request_text,
            client_id=client_id,
            status=ProjectStatus.PLANNING,
            budget_tokens=75_000,
            llm_requests=2,
            tokens_used=_AVG_TOKENS_PER_CALL * 2,
            llm_cost_usd=_estimate_call_cost(_AVG_TOKENS_PER_CALL * 2),
        )

        # --- Step 4: PM agent creates task list (A2A) ---
        task_text = await _call_agent(
            _AGENT_URLS["pm"],
            f"Create a task list for this project:\n\n{request_text}\n\n"
            f"Project ID: {project.id}",
        )
        print(f"[Agency][PM→A2A] Tasks: {task_text[:200]}")
        project.llm_requests += 1
        project.tokens_used += _AVG_TOKENS_PER_CALL
        project.llm_cost_usd += _estimate_call_cost(_AVG_TOKENS_PER_CALL)

        # Parse tasks from PM output if JSON is present
        task_json = _extract_json(task_text)
        if task_json and "tasks" in task_json:
            for t in task_json["tasks"]:
                project.tasks.append(Task(
                    title=t.get("title", "Unnamed Task"),
                    description=t.get("description", ""),
                    assigned_to=t.get("assigned_to", "engineer"),
                ))

        if not project.tasks:
            project.tasks.append(Task(
                title="Implement Request",
                description=request_text,
                assigned_to="engineer",
            ))

        project.status = ProjectStatus.EXECUTION
        self.deps.projects[project.id] = project

        return {
            "project_id": project.id,
            "status": project.status,
            "task_count": len(project.tasks),
        }

    async def _process_project(self, project: Project) -> None:
        """
        Run the execution → QA loop for all pending tasks in a project.

        For each task:
          1. Dispatch to the appropriate execution agent (via A2A).
          2. QA agent reviews the output (via A2A).
          3. If QA fails, retry up to max_qa_retries times.
          4. If all retries exhausted, escalate to CEO (via A2A).
        """
        print(f"\n[Agency] Processing project: {project.name}")

        for task in project.tasks:
            if task.status in (TaskStatus.DONE, TaskStatus.FAILED):
                continue
            await self._execute_task(task, project)

        all_done = all(t.status == TaskStatus.DONE for t in project.tasks)
        project.status = ProjectStatus.DELIVERED if all_done else ProjectStatus.QA
        project.updated_at = datetime.utcnow()

        if all_done:
            await _call_agent(
                _AGENT_URLS["ceo"],
                f"Approve delivery for project {project.id}. "
                f"Tasks completed: {len(project.tasks)}. "
                "Call approve_delivery with a brief summary.",
            )
            project.llm_requests += 1
            project.tokens_used += _AVG_TOKENS_PER_CALL
            project.llm_cost_usd += _estimate_call_cost(_AVG_TOKENS_PER_CALL)
            print(f"[Agency][CEO→A2A] Project {project.id} approved for delivery.")

            # Automated delivery — collect outputs and deploy sandbox
            await self._auto_deploy(project)

    async def _execute_task(self, task: Task, project: Project) -> None:
        """Execute a single task with QA feedback loop, all via A2A."""
        task.status = TaskStatus.IN_PROGRESS
        task.updated_at = datetime.utcnow()

        agent_url = _AGENT_URLS.get(task.assigned_to or "engineer", _AGENT_URLS["engineer"])

        while task.retry_count <= self.deps.max_qa_retries:
            print(f"  [Agency] Executing task '{task.title}' "
                  f"(attempt {task.retry_count + 1}) via A2A → {agent_url}")

            prompt = task.description
            if task.qa_feedback:
                prompt += f"\n\nQA FEEDBACK (please address):\n{task.qa_feedback}"

            # Dispatch to execution agent via A2A
            task.output = await _call_agent(agent_url, prompt)
            task.status = TaskStatus.REVIEW

            # Track cost for this task
            task.tokens_used += _AVG_TOKENS_PER_CALL
            task.cost_usd += _estimate_call_cost(_AVG_TOKENS_PER_CALL)
            project.tokens_used += _AVG_TOKENS_PER_CALL
            project.llm_requests += 1
            project.llm_cost_usd += _estimate_call_cost(_AVG_TOKENS_PER_CALL)

            # QA review via A2A
            qa_prompt = (
                f"Review the following output for task: '{task.title}'\n\n"
                f"Task requirements: {task.description}\n\n"
                f"Output to review:\n{task.output[:3000]}\n\n"
                "Use the review_output and check_standards tools, then give a "
                "clear PASS or FAIL verdict in your response."
            )
            qa_text = await _call_agent(_AGENT_URLS["qa"], qa_prompt)
            passed = "pass" in qa_text.lower() and "fail" not in qa_text.lower()

            project.tokens_used += _AVG_TOKENS_PER_CALL
            project.llm_requests += 1
            project.llm_cost_usd += _estimate_call_cost(_AVG_TOKENS_PER_CALL)

            if passed:
                task.status = TaskStatus.DONE
                task.updated_at = datetime.utcnow()
                print(f"  [Agency][QA→A2A] Task '{task.title}' PASSED ✓")
                return

            task.retry_count += 1
            task.qa_feedback = qa_text
            print(f"  [Agency][QA→A2A] Task '{task.title}' FAILED — "
                  f"retry {task.retry_count}/{self.deps.max_qa_retries}")

        # Exhausted retries — escalate to CEO via A2A
        task.status = TaskStatus.FAILED
        await _call_agent(
            _AGENT_URLS["ceo"],
            f"Task '{task.title}' in project {project.id} failed after "
            f"{self.deps.max_qa_retries} QA retries. Decide next action.",
        )
        project.llm_requests += 1
        project.llm_cost_usd += _estimate_call_cost(_AVG_TOKENS_PER_CALL)
        print(f"  [Agency] Task '{task.title}' FAILED after max retries — escalated to CEO via A2A.")

    async def _auto_deploy(self, project: Project) -> None:
        """
        Automated delivery: collect task outputs and deploy to the sandbox.

        Writes a simple HTML summary of all task outputs to
        deliveries/{project_id}/index.html and sets project.demo_url.
        """
        if project.demo_url:
            return  # Already deployed manually

        outputs = []
        for task in project.tasks:
            if task.output:
                outputs.append(f"<section><h3>{task.title}</h3><pre>{task.output[:2000]}</pre></section>")

        if not outputs:
            return

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{project.name} — Deliverables</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1rem; }}
  h1 {{ color: #7c3aed; }}
  section {{ margin: 2rem 0; border-left: 3px solid #7c3aed; padding-left: 1rem; }}
  pre {{ background: #1e1e2e; color: #cdd6f4; padding: 1rem; overflow-x: auto; border-radius: 6px; }}
</style>
</head>
<body>
<h1>{project.name}</h1>
<p><em>Delivered by Agent-Puter — {datetime.utcnow().strftime('%Y-%m-%d')}</em></p>
{"".join(outputs)}
</body>
</html>"""

        deploy_prompt = (
            f"Deploy the following deliverable for project {project.id}.\n"
            f"Call deploy_to_sandbox with project_id='{project.id}', "
            f"filename='index.html', and the following content:\n\n{html[:4000]}"
        )
        deploy_result = await _call_agent(_AGENT_URLS["engineer"], deploy_prompt)
        project.llm_requests += 1
        project.llm_cost_usd += _estimate_call_cost(_AVG_TOKENS_PER_CALL)

        # Parse URL from engineer's response
        result_json = _extract_json(deploy_result)
        if result_json and result_json.get("status") == "deployed":
            sandbox_url = result_json.get("url", "")
            if sandbox_url:
                project.demo_url = sandbox_url
                project.deployment_status = "deployed"
                print(f"[Agency] Auto-deployed to sandbox: {sandbox_url}")
                return

        # Fallback: generate URL directly
        from pathlib import Path
        deploy_dir = Path("deliveries") / project.id
        try:
            deploy_dir.mkdir(parents=True, exist_ok=True)
            (deploy_dir / "index.html").write_text(html, encoding="utf-8")
            project.demo_url = f"{BASE_URL}/deliveries/{project.id}/index.html"
            project.deployment_status = "deployed"
            print(f"[Agency] Fallback auto-deployed: {project.demo_url}")
        except Exception as exc:
            project.deployment_status = "failed"
            print(f"[Agency] Auto-deploy failed: {exc}")

        # Auto-push to GitHub if the user authenticated via OAuth
        if project.github_user_id:
            await self._push_to_github(project)

    async def _push_to_github(self, project: Project) -> None:
        """Push delivery files to the owner's GitHub account (best-effort)."""
        try:
            from .api.store import store as _data_store
            from .api.github_delivery import push_project_to_github
            user = await _data_store.get_user(project.github_user_id)
            if not user or not user.access_token:
                return
            repo_url = await push_project_to_github(user.access_token, user.login, project)
            project.github_repo_url = repo_url
            await _data_store.set_project(project)
            print(f"[Agency] Pushed to GitHub: {repo_url}")
        except Exception as exc:
            print(f"[Agency] GitHub push failed (non-fatal): {exc}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_json(text: str) -> Optional[dict]:
    """Extract the first JSON object found in a string."""
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == 0:
        return None
    try:
        return json.loads(text[start:end])
    except json.JSONDecodeError:
        return None
