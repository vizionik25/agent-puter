# Primary export: the full multi-agent swarm ASGI application.
# Mount this with uvicorn to serve all 6 specialized agents.
from .swarm import app

# The single-agent example remains importable for reference.
# from . import agent_logic_example as example_agent

__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9999)