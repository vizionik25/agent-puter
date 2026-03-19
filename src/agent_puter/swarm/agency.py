"""
agency.py — Agency Orchestrator

The Agency class owns the autonomous business loop:
  Client Request → Sales → Project Brief → PM → Tasks → Execution → QA → Delivery

Agents are called directly as pydantic-ai Agent instances (not via HTTP).
In production, swap in the A2A HTTP client to call remote agent services.
"""
from __future__ import annotations

import json
import asyncio
from datetime import datetime
from typing import Optional

from .models import (
    AgencyDeps,
    Project,
    ProjectStatus,
    Task,
    TaskStatus,
)

# Import agent instances directly (no network calls at import time)
from .ceo_agent import ceo_agent
from .sales_agent import sales_agent
from .pm_agent import pm_agent
from .researcher_agent import researcher_agent
from .engineer_agent import engineer_agent
from .qa_agent import qa_agent


class Agency:
    """
    Autonomous AI consulting agency orchestrator.

    Wires together all specialized agents into a coherent business loop.
    Each agent is called via .run() (pydantic-ai in-process).
    In production, replace with A2A HTTP client calls to remote agent services.
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

        1. Sales agent parses the request and produces a brief.
        2. CEO agent allocates a token budget.
        3. PM agent breaks the brief into tasks.
        4. Project is stored in deps.projects and returned.

        Args:
            request_text: The raw client request string.
            client_id: Unique identifier for the client.

        Returns a dict with project_id and initial status.
        """
        print(f"[Agency] Received request from {client_id}: {request_text[:80]}...")

        # --- Step 1: Sales agent creates a project brief ---
        brief_result = await sales_agent.run(
            f"Create a project brief for this client request:\n\n{request_text}",
        )
        print(f"[Agency][Sales] Brief: {str(brief_result.output)[:200]}")

        # --- Step 2: CEO allocates budget ---
        budget_result = await ceo_agent.run(
            "Allocate a token budget for a new mid-complexity project. "
            "Call allocate_budget with project_id='new' and requested_tokens=75000."
        )
        print(f"[Agency][CEO] Budget: {str(budget_result.output)[:200]}")

        # --- Step 3: Create the Project object ---
        project = Project(
            name=f"Project for {client_id}",
            description=request_text,
            client_id=client_id,
            status=ProjectStatus.PLANNING,
            budget_tokens=75_000,
        )

        # --- Step 4: PM agent creates task list ---
        task_result = await pm_agent.run(
            f"Create a task list for this project:\n\n{request_text}\n\n"
            f"Project ID: {project.id}"
        )
        print(f"[Agency][PM] Tasks: {str(task_result.output)[:200]}")

        # Parse tasks from PM output if JSON is present
        task_json = _extract_json(str(task_result.output))
        if task_json and "tasks" in task_json:
            for t in task_json["tasks"]:
                project.tasks.append(Task(
                    title=t.get("title", "Unnamed Task"),
                    description=t.get("description", ""),
                    assigned_to=t.get("assigned_to", "engineer"),
                ))

        if not project.tasks:
            # Fallback — ensure there's at least one task
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
          1. Dispatch to the appropriate execution agent.
          2. QA agent reviews the output.
          3. If QA fails, retry up to max_qa_retries times.
          4. If all retries exhausted, escalate to CEO.
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
            await ceo_agent.run(
                f"Approve delivery for project {project.id}. "
                f"Tasks completed: {len(project.tasks)}. "
                "Call approve_delivery with a brief summary."
            )
            print(f"[Agency][CEO] Project {project.id} approved for delivery.")

    async def _execute_task(self, task: Task, project: Project) -> None:
        """Execute a single task with QA feedback loop."""
        task.status = TaskStatus.IN_PROGRESS
        task.updated_at = datetime.utcnow()

        agent = self._get_agent_for_role(task.assigned_to or "engineer")

        while task.retry_count <= self.deps.max_qa_retries:
            print(f"  [Agency] Executing task '{task.title}' "
                  f"(attempt {task.retry_count + 1})")

            prompt = task.description
            if task.qa_feedback:
                prompt += f"\n\nQA FEEDBACK (please address):\n{task.qa_feedback}"

            exec_result = await agent.run(prompt)
            task.output = str(exec_result.output)
            task.status = TaskStatus.REVIEW

            # QA review
            qa_prompt = (
                f"Review the following output for task: '{task.title}'\n\n"
                f"Task requirements: {task.description}\n\n"
                f"Output to review:\n{task.output[:3000]}\n\n"
                "Use the review_output and check_standards tools, then give a "
                "clear PASS or FAIL verdict in your response."
            )
            qa_result = await qa_agent.run(qa_prompt)
            qa_text = str(qa_result.output).lower()
            passed = "pass" in qa_text and "fail" not in qa_text

            if passed:
                task.status = TaskStatus.DONE
                task.updated_at = datetime.utcnow()
                print(f"  [Agency][QA] Task '{task.title}' PASSED ✓")
                return

            task.retry_count += 1
            task.qa_feedback = str(qa_result.output)
            print(f"  [Agency][QA] Task '{task.title}' FAILED — "
                  f"retry {task.retry_count}/{self.deps.max_qa_retries}")

        # Exhausted retries — escalate to CEO
        task.status = TaskStatus.FAILED
        await ceo_agent.run(
            f"Task '{task.title}' in project {project.id} failed after "
            f"{self.deps.max_qa_retries} QA retries. "
            "Decide next action."
        )
        print(f"  [Agency] Task '{task.title}' FAILED after max retries — escalated to CEO.")

    def _get_agent_for_role(self, role: str):
        """Map a role name to the corresponding pydantic-ai Agent instance."""
        return {
            "engineer":   engineer_agent,
            "researcher": researcher_agent,
            "qa":         qa_agent,
            "ceo":        ceo_agent,
        }.get(role, engineer_agent)


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
