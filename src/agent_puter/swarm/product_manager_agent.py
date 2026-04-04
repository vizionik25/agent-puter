"""
product_manager_agent.py — Product Manager Agent

Translates business goals into actionable requirements, writes user stories,
prioritizes features, and bridges the gap between Sales and PM/Engineer agents.
Pattern: LiteLLMModel → pydantic_ai.Agent → .to_a2a() ASGI app.
Each agent owns its own A2A app so it can be mounted or run independently.
"""
import json
from dotenv import load_dotenv
from pydantic_ai import Agent
from .base_agent import make_model

load_dotenv()

_SYSTEM_PROMPT = """
You are the Product Manager Agent for an autonomous AI consulting agency.

Your responsibilities:
1. Translate high-level business goals and client requests into clear, actionable
   product requirements and user stories.
2. Prioritize features using impact vs effort analysis — focus on highest-value
   deliverables first.
3. Define acceptance criteria for each feature so QA and engineers know exactly
   what "done" looks like.
4. Bridge communication between Sales (client intent) and PM/Engineer (execution)
   by clarifying ambiguous requirements before work begins.
5. Identify scope risks early and recommend phasing or de-scoping when needed.

Always write user stories in the format:
  "As a [user type], I want [action] so that [benefit]."

Always include measurable acceptance criteria for each story.

Be concise, business-focused, and ruthlessly prioritized.
"""

product_manager_agent = Agent(
    model=make_model(),
    instructions=_SYSTEM_PROMPT,
)

# Each agent exposes itself as a self-contained A2A ASGI app.
from .ceo_agent import BASE_URL
product_manager_app = product_manager_agent.to_a2a(
    name="Product Manager Agent",
    url=f"{BASE_URL}/product-manager",
    description="Translates business goals into prioritized user stories with acceptance criteria.",
)


@product_manager_agent.tool_plain
def write_user_stories(project_id: str, business_goal: str, target_users: str) -> str:
    """
    Generate a prioritized list of user stories from a business goal.

    Args:
        project_id: The unique project identifier.
        business_goal: The high-level goal the client wants to achieve.
        target_users: Comma-separated description of who will use the product.

    Returns a JSON array of user stories with acceptance criteria and priority.
    """
    stories = [
        {
            "id": f"{project_id}-US-001",
            "story": f"As a {target_users.split(',')[0].strip()}, I want to {business_goal[:80]} so that I can achieve my core objective.",
            "priority": "high",
            "acceptance_criteria": [
                "Feature is accessible without errors",
                "Core workflow completes in under 3 steps",
                "Output matches the stated business goal",
            ],
            "estimated_effort": "medium",
        },
        {
            "id": f"{project_id}-US-002",
            "story": f"As a {target_users.split(',')[0].strip()}, I want clear feedback when something goes wrong so that I can correct my input.",
            "priority": "medium",
            "acceptance_criteria": [
                "Error messages are human-readable",
                "User is guided toward a resolution",
            ],
            "estimated_effort": "low",
        },
    ]
    return json.dumps({"project_id": project_id, "user_stories": stories})


@product_manager_agent.tool_plain
def prioritize_features(project_id: str, features: str, constraint: str = "time") -> str:
    """
    Rank a list of features by priority given a constraint.

    Args:
        project_id: The unique project identifier.
        features: Newline-separated list of feature descriptions.
        constraint: Primary constraint to optimize for — "time", "budget", or "scope".

    Returns a JSON array of features ranked high/medium/low with rationale.
    """
    valid_constraints = {"time", "budget", "scope"}
    if constraint not in valid_constraints:
        return f'{{"error": "Invalid constraint: {constraint}. Valid: {list(valid_constraints)}"}}'

    feature_list = [f.strip() for f in features.strip().splitlines() if f.strip()]
    ranked = []
    for i, feature in enumerate(feature_list):
        if i == 0:
            priority, rationale = "high", f"Core value driver — highest impact relative to {constraint}."
        elif i < len(feature_list) // 2 + 1:
            priority, rationale = "medium", f"Important but not blocking — schedule after high-priority items."
        else:
            priority, rationale = "low", f"Nice-to-have — defer if {constraint} is tight."
        ranked.append({"feature": feature, "priority": priority, "rationale": rationale})

    return json.dumps({"project_id": project_id, "constraint": constraint, "ranked_features": ranked})
