"""
researcher_agent.py — Researcher Agent

Conducts web research and returns structured summaries for execution agents.
Pattern: LiteLLMModel → pydantic_ai.Agent (same as agent.py)
.to_a2a() is called in main.py at server startup, not here at import time.
"""
import json
from dotenv import load_dotenv
from pydantic_ai import Agent
from .base_agent import make_model

load_dotenv()

_SYSTEM_PROMPT = """
You are the Researcher Agent for an autonomous AI consulting agency.

Your responsibilities:
1. Receive research requests from the Project Manager or execution agents.
2. Produce comprehensive, structured research summaries.
3. Identify best practices, relevant documentation, libraries, and APIs.
4. Flag any ambiguities or risks discovered during research.

Always structure your output with clear sections:
  - Summary
  - Key Findings (bullet list)
  - Recommended Approach
  - Risks & Caveats
  - References (URLs or docs)

Be thorough, accurate, and cite sources where possible.
"""

researcher_agent = Agent(
    model=make_model(),
    instructions=_SYSTEM_PROMPT,
)


@researcher_agent.tool_plain
def web_search(query: str, max_results: int = 5) -> str:
    """
    Search the web for information relevant to a research query.

    Args:
        query: The search query string.
        max_results: Maximum number of results to return (default 5).

    Returns a JSON array of search result objects with title and snippet.

    Note: In production wire this up to a real search API (e.g. SerpAPI,
    Brave Search, or Puter's browsing capabilities).
    """
    results = [
        {
            "title": f"Result for: {query}",
            "url": "https://example.com",
            "snippet": (
                f"Placeholder search result for '{query}'. "
                "Wire up a real search API for production use."
            ),
        }
    ]
    return json.dumps({"query": query, "results": results[:max_results]})


@researcher_agent.tool_plain
def summarize_docs(urls: str, focus: str) -> str:
    """
    Fetch and summarize content from one or more documentation URLs.

    Args:
        urls: Comma-separated list of URLs to read and summarize.
        focus: The specific aspect or question to focus the summary on.

    Returns a structured summary string.

    Note: In production use Puter's browser/fetch capabilities.
    """
    url_list = [u.strip() for u in urls.split(",")]
    return json.dumps({
        "urls": url_list,
        "focus": focus,
        "summary": (
            f"Placeholder summary focused on '{focus}' across {len(url_list)} source(s). "
            "Integrate with Puter browser SDK for live document fetching."
        ),
    })
