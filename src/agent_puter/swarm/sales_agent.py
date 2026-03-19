"""
sales_agent.py — Sales & Intake Agent

Receives inbound client requests, negotiates scope, produces a Project brief.
Pattern: LiteLLMModel → pydantic_ai.Agent → .to_a2a() ASGI app.
Each agent owns its own A2A app so it can be mounted or run independently.
"""
import json
from dotenv import load_dotenv
from pydantic_ai import Agent
from .base_agent import make_model

load_dotenv()

_SYSTEM_PROMPT = """
You are the Sales & Intake Agent for an autonomous AI consulting agency.

Your responsibilities:
1. Receive and parse incoming client requests.
2. Clarify scope, deliverables, and constraints by asking targeted questions.
3. Generate a concise, structured project brief that the Project Manager can act on.
4. Estimate rough effort in token budget terms.

Output project briefs as JSON with these keys:
  name, description, client_id, estimated_tokens, deliverables (list), constraints (list)

Be professional, thorough, and focused on extracting actionable requirements.
"""

sales_agent = Agent(
    model=make_model(),
    instructions=_SYSTEM_PROMPT,
)

# Each agent exposes itself as a self-contained A2A ASGI app.
from .ceo_agent import BASE_URL
sales_app = sales_agent.to_a2a(
    name="Sales Agent",
    url=f"{BASE_URL}/sales",
    description="Handles client intake and produces structured project briefs.",
)


@sales_agent.tool_plain
def create_project_brief(
    client_id: str,
    request_text: str,
    deliverables: str,
    constraints: str,
) -> str:
    """
    Generate a structured project brief from raw client input.

    Args:
        client_id: The client's unique identifier.
        request_text: The client's original request text.
        deliverables: Comma-separated list of expected deliverables.
        constraints: Comma-separated list of constraints or requirements.

    Returns a JSON project brief.
    """
    brief = {
        "client_id": client_id,
        "name": f"Project for {client_id}",
        "description": request_text,
        "deliverables": [d.strip() for d in deliverables.split(",")],
        "constraints": [c.strip() for c in constraints.split(",")],
        "estimated_tokens": 50_000,
        "status": "brief_ready",
    }
    return json.dumps(brief)


@sales_agent.tool_plain
def send_proposal(client_id: str, brief_summary: str, price_estimate: str) -> str:
    """
    Send a proposal to the client for approval.

    Args:
        client_id: The client's unique identifier.
        brief_summary: A human-readable summary of the project scope.
        price_estimate: Estimated cost / effort description.

    Returns confirmation that the proposal was dispatched.
    """
    return (
        f'{{"client_id": "{client_id}", "status": "proposal_sent", '
        f'"summary": "{brief_summary}", "estimate": "{price_estimate}"}}'
    )
