"""
ceo_agent.py — CEO / Orchestrator Agent

Sets macro goals, allocates token budgets, gives final delivery sign-off.
Pattern: LiteLLMModel → pydantic_ai.Agent (same as agent.py)
.to_a2a() is called in main.py at server startup, not here at import time.
"""
from dotenv import load_dotenv
from pydantic_ai import Agent
from .base_agent import make_model

load_dotenv()

_SYSTEM_PROMPT = """
You are the CEO of an autonomous AI consulting agency.

Your responsibilities:
1. Define and communicate the agency's strategic goals.
2. Allocate token budgets to projects fairly based on scope and value.
3. Approve or reject final deliverables before client handoff.
4. Intervene when a project is stuck (e.g. QA retries exceeded).

Always respond with structured reasoning before taking any action.
Be decisive, concise, and business-focused.
"""

ceo_agent = Agent(
    model=make_model(),
    instructions=_SYSTEM_PROMPT,
)


@ceo_agent.tool_plain
def allocate_budget(project_id: str, requested_tokens: int) -> str:
    """
    Allocate a token budget to a project.

    Args:
        project_id: The unique project identifier.
        requested_tokens: Number of tokens the PM is requesting.

    Returns a JSON string with the approved budget.
    """
    approved = min(requested_tokens, 100_000)
    return f'{{"project_id": "{project_id}", "approved_tokens": {approved}}}'


@ceo_agent.tool_plain
def approve_delivery(project_id: str, summary: str) -> str:
    """
    Review and approve a completed project for delivery to the client.

    Args:
        project_id: The unique project identifier.
        summary: A brief summary of what was delivered.

    Returns approval status.
    """
    return (
        f'{{"project_id": "{project_id}", "status": "approved", '
        f'"message": "Delivery approved. Summary acknowledged."}}'
    )


@ceo_agent.tool_plain
def publish_goal(goal: str) -> str:
    """
    Publish a new strategic goal for the agency.

    Args:
        goal: The strategic goal statement.

    Returns confirmation.
    """
    return f'{{"goal": "{goal}", "status": "published"}}'
