"""
api/_store.py — Shared in-memory store for sessions and projects.

Imported by all API route modules and by main.py to share state
across the consultation, projects, and payments endpoints.

In production, replace with Puter KV or a real database.
"""
from __future__ import annotations

from ..models import ConsultSession, Project

# Single shared dictionaries — mutated in-place by all route handlers
sessions: dict[str, ConsultSession] = {}
projects: dict[str, Project] = {}
