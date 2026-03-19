"""
server.py — CLI entry point for the agent swarm.

Called by `uv run agent-puter` (defined in pyproject.toml).
Launches the full swarm ASGI app via uvicorn.
"""
import uvicorn


def run() -> None:
    """Start the swarm server.  All 6 agent A2A apps are served together."""
    uvicorn.run(
        "agent_puter.swarm.main:app",
        host="0.0.0.0",
        port=9999,
        reload=False,
    )


if __name__ == "__main__":
    run()
