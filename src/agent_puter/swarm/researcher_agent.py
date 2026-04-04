"""
researcher_agent.py — Researcher Agent

Conducts web research and returns structured summaries for execution agents.
Pattern: LiteLLMModel → pydantic_ai.Agent → .to_a2a() ASGI app.
Each agent owns its own A2A app so it can be mounted or run independently.

MCP: When MCP_SERVER_URL is set, the agent also exposes the MCP server's tools
with the "mcp_" prefix, enabling real web browsing or custom data-source tools.
"""
import json
import os
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


def _make_mcp_toolsets() -> list:
    """Return a list of MCP toolsets to attach, based on MCP_SERVER_URL env var."""
    mcp_url = os.getenv("MCP_SERVER_URL", "").strip()
    if not mcp_url:
        return []
    try:
        from pydantic_ai.mcp import MCPServerHTTP
        print(f"[ResearcherAgent] Attaching MCP server: {mcp_url}")
        return [MCPServerHTTP(url=mcp_url, tool_prefix="mcp")]
    except Exception as exc:
        print(f"[ResearcherAgent] Could not attach MCP server: {exc}")
        return []


researcher_agent = Agent(
    model=make_model(),
    instructions=_SYSTEM_PROMPT,
    toolsets=_make_mcp_toolsets(),
)

# Each agent exposes itself as a self-contained A2A ASGI app.
from .ceo_agent import BASE_URL
researcher_app = researcher_agent.to_a2a(
    name="Researcher Agent",
    url=f"{BASE_URL}/researcher",
    description="Performs web research and document summarization.",
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
    Brave Search, or via an MCP server with MCP_SERVER_URL).
    """
    results = [
        {
            "title": f"Result for: {query}",
            "url": "https://example.com",
            "snippet": (
                f"Placeholder search result for '{query}'. "
                "Wire up a real search API or set MCP_SERVER_URL for production use."
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

    Note: In production use Puter's browser/fetch capabilities or set
    MCP_SERVER_URL to an MCP server with browser/fetch tools.
    """
    url_list = [u.strip() for u in urls.split(",")]
    return json.dumps({
        "urls": url_list,
        "focus": focus,
        "summary": (
            f"Placeholder summary focused on '{focus}' across {len(url_list)} source(s). "
            "Set MCP_SERVER_URL to an MCP server with fetch tools for live document fetching."
        ),
    })
