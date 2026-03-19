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
    """Build a minimal A2A Message with a single TextPart."""
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

    Returns the agent's text response, or an empty string on failure.
    """
    client = A2AClient(base_url=base_url)
    try:
        response = await client.send_message(message=_text_message(prompt))
        # SendMessageResponse is JSONRPCResponse[Union[Task, Message], JSONRPCError]
        # Access result — may be a Task (has 'status') or a Message (has 'parts' directly).
        result = response.get("result")  # type: ignore[union-attr]
        if result is None:
            return ""
        # Task path: result["status"]["message"]["parts"]
        if "status" in result:
            msg = result["status"].get("message", {})
            parts = msg.get("parts", []) if msg else []
        else:
            # Message path: result["parts"]
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
    "ceo":        f"{BASE_URL}",
    "sales":      f"{BASE_URL}/sales",
    "pm":         f"{BASE_URL}/pm",
    "researcher": f"{BASE_URL}/researcher",
    "engineer":   f"{BASE_URL}/engineer",
    "qa":         f"{BASE_URL}/qa",
}


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
        self.deps = deps

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def handle_client_request(
        self,
        request_text: str,
        client_id: str,
    ) -> dict:
        """
        Intake a new client request and create a Project.

        1. Sales agent parses the request and produces a brief (via A2A).
        2. CEO agent allocates a token budget (via A2A).
        3. PM agent breaks the brief into tasks (via A2A).
        4. Project is stored in deps.projects and returned.
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
        )

        # --- Step 4: PM agent creates task list (A2A) ---
        task_text = await _call_agent(
            _AGENT_URLS["pm"],
            f"Create a task list for this project:\n\n{request_text}\n\n"
            f"Project ID: {project.id}",
        )
        print(f"[Agency][PM→A2A] Tasks: {task_text[:200]}")

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
            print(f"[Agency][CEO→A2A] Project {project.id} approved for delivery.")

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
        print(f"  [Agency] Task '{task.title}' FAILED after max retries — escalated to CEO via A2A.")


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
