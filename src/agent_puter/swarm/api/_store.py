"""
api/_store.py — Re-exports the async store singleton.

All route handlers should use:
    from . import _store
    session = await _store.store.get_session(id)
    await _store.store.set_session(session)

The `store` object's backend is controlled by STORAGE_BACKEND env var.
AgencyDeps still receives a snapshot of the projects/sessions dicts for
compatibility with the agency orchestration loop.
"""
from __future__ import annotations

from .store import store

__all__ = ["store"]
