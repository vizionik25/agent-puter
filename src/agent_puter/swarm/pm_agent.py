"""
pm_agent.py — Project Manager Agent

Parses project briefs into ordered Task lists, assigns them to execution agents,
and monitors status throughout the project lifecycle.
Pattern: LiteLLMModel → pydantic_ai.Agent → .to_a2a() ASGI app.
Each agent owns its own A2A app so it can be mounted or run independently.
"""
import json
from dotenv import load_dotenv
from pydantic_ai import Agent
from .base_agent import make_model

load_dotenv()

_SYSTEM_PROMPT = """
You are the Project Manager Agent for an autonomous AI consulting agency.

Your responsibilities:
1. Parse project briefs into a concrete, ordered list of Tasks.
2. Assign each task to the most appropriate execution agent role:
   - "engineer" for coding, implementation, scripting
   - "researcher" for research, documentation gathering, analysis
   - "copywriter" for writing, documentation, reports
3. Monitor task status and unblock stuck tasks.
4. Escalate to CEO if a project exceeds its budget or QA retries.

Always produce task lists as a JSON array where each task has:
  title, description, assigned_to, dependencies (list of task titles)

Be systematic, realistic about scope, and proactive about risks.
"""

pm_agent = Agent(
    model=make_model(),
    instructions=_SYSTEM_PROMPT,
)

# Each agent exposes itself as a self-contained A2A ASGI app.
from .ceo_agent import BASE_URL
pm_app = pm_agent.to_a2a(
    name="PM Agent",
    url=f"{BASE_URL}/pm",
    description="Decomposes project briefs into ordered, assignable tasks.",
)


@pm_agent.tool_plain
def create_task_list(project_id: str, project_description: str) -> str:
    """
    Break a project description into an ordered list of tasks.

    Args:
        project_id: The unique project identifier.
        project_description: Full description of the project and its deliverables.

    Returns a JSON array of task objects.
    """
    tasks = [
        {
            "title": "Research & Requirements",
            "description": f"Research requirements for: {project_description[:200]}",
            "assigned_to": "researcher",
            "dependencies": [],
        },
        {
            "title": "Implementation",
            "description": "Implement the core deliverable based on research output.",
            "assigned_to": "engineer",
            "dependencies": ["Research & Requirements"],
        },
        {
            "title": "QA Review",
            "description": "Review implementation against project requirements.",
            "assigned_to": "qa",
            "dependencies": ["Implementation"],
        },
    ]
    return json.dumps({"project_id": project_id, "tasks": tasks})


@pm_agent.tool_plain
def assign_task(task_id: str, agent_role: str) -> str:
    """
    Assign a specific task to an agent role.

    Args:
        task_id: The unique task identifier.
        agent_role: Role to assign (engineer, researcher, qa, copywriter).

    Returns assignment confirmation.
    """
    valid_roles = {"engineer", "researcher", "qa", "copywriter", "ceo"}
    if agent_role not in valid_roles:
        return f'{{"error": "Unknown role: {agent_role}. Valid: {list(valid_roles)}"}}'
    return f'{{"task_id": "{task_id}", "assigned_to": "{agent_role}", "status": "assigned"}}'


@pm_agent.tool_plain
def update_task_status(task_id: str, status: str, output_summary: str = "") -> str:
    """
    Update the status of a task.

    Args:
        task_id: The unique task identifier.
        status: New status (pending, in_progress, review, done, failed).
        output_summary: Optional brief summary of the task output.

    Returns update confirmation.
    """
    valid_statuses = {"pending", "in_progress", "review", "done", "failed"}
    if status not in valid_statuses:
        return f'{{"error": "Invalid status: {status}"}}'
    return json.dumps({"task_id": task_id, "status": status, "output_summary": output_summary})


@pm_agent.tool_plain
def escalate_to_ceo(project_id: str, reason: str) -> str:
    """
    Escalate a project issue to the CEO agent.

    Args:
        project_id: The unique project identifier.
        reason: Explanation of why escalation is needed.

    Returns escalation confirmation.
    """
    return f'{{"project_id": "{project_id}", "escalated": true, "reason": "{reason}"}}'
