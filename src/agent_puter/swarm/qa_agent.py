"""
qa_agent.py — Quality Assurance / Review Agent

Reviews outputs from execution agents and returns a pass/fail verdict.
Pattern: LiteLLMModel → pydantic_ai.Agent → .to_a2a() ASGI app.
Each agent owns its own A2A app so it can be mounted or run independently.
"""
import json
from dotenv import load_dotenv
from pydantic_ai import Agent
from .base_agent import make_model

load_dotenv()

_SYSTEM_PROMPT = """
You are the QA / Review Agent for an autonomous AI consulting agency.

Your responsibilities:
1. Review outputs from execution agents (code, reports, documents).
2. Check against the original task requirements and agency quality standards.
3. Return a clear PASS or FAIL verdict with actionable feedback.
4. Be constructive — specify exactly what needs to change for a PASS.

Quality standards to check:
  CODE:
    - Correct logic and handles edge cases
    - Type hints on all functions
    - Docstrings present
    - No obvious security issues (no eval on untrusted input, no hardcoded secrets)
    - Tests present and passing
  DOCUMENTS:
    - Addresses all requirements from the brief
    - Clear, professional language
    - No factual errors
  GENERAL:
    - Output matches the task description
    - Complete — nothing left as a placeholder

Be rigorous. A false PASS wastes client trust.
"""

qa_agent = Agent(
    model=make_model(),
    instructions=_SYSTEM_PROMPT,
)

# Each agent exposes itself as a self-contained A2A ASGI app.
from .ceo_agent import BASE_URL
qa_app = qa_agent.to_a2a(
    name="QA Agent",
    url=f"{BASE_URL}/qa",
    description="Reviews task output against requirements and coding standards.",
)


@qa_agent.tool_plain
def review_output(task_id: str, task_description: str, output: str) -> str:
    """
    Record a QA review verdict for an agent's output.

    Args:
        task_id: The unique task identifier.
        task_description: The original task requirements.
        output: The output produced by the execution agent.

    Returns a JSON ReviewResult with the reviewer name.
    The LLM states its PASS/FAIL verdict in the surrounding response text.
    """
    return json.dumps({
        "task_id": task_id,
        "reviewer": "qa_agent",
        "status": "review_recorded",
        "note": "See LLM response for PASS/FAIL verdict and feedback.",
    })


@qa_agent.tool_plain
def check_standards(code: str, language: str = "python") -> str:
    """
    Run automated standards checks on a code output.

    Args:
        code: The source code to check.
        language: Programming language (default "python").

    Returns a JSON report of standards violations found.
    """
    violations: list[str] = []

    if language == "python":
        lines = code.split("\n")
        has_docstring = '"""' in code or "'''" in code
        has_type_hints = "->" in code or ": " in code
        has_eval = "eval(" in code

        if not has_docstring:
            violations.append("Missing docstrings")
        if not has_type_hints:
            violations.append("Missing type hints")
        if has_eval:
            violations.append("SECURITY: eval() detected — use safer alternatives")

        function_count = sum(1 for line in lines if line.strip().startswith("def "))
    else:
        function_count = 0

    return json.dumps({
        "language": language,
        "function_count": function_count,
        "violations": violations,
        "clean": len(violations) == 0,
    })
