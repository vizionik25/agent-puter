"""
swarm/__init__.py

Re-exports the combined ASGI app from main.py so callers can do:
    from agent_puter.swarm import app
"""
from .main import app

__all__ = ["app"]
