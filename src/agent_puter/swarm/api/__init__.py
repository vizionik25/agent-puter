"""
api/ — Client-facing REST API routes.

Exports:
    routes  — flat list of all Starlette Route objects, mounted in main.py
    _store  — shared in-memory session/project store
"""
from . import _store  # noqa: F401 — shared singleton
from .consultation import routes as _consult_routes
from .projects import routes as _project_routes
from .payments import routes as _payment_routes

routes = [*_consult_routes, *_project_routes, *_payment_routes]

__all__ = ["routes", "_store"]
