"""
api/store.py — Pluggable persistence layer for sessions and projects.

Backends (selected via STORAGE_BACKEND env var):
  memory    — in-memory dicts, default, resets on restart
  json_file — persists to a JSON file at STORAGE_PATH (default: ./data/store.json)
  puter_kv  — Puter cloud key-value store (requires PUTER_AUTH_TOKEN + PUTER_KV_BASE)

All backends expose the same async interface so route handlers never need to
know which backend is active.
"""
from __future__ import annotations

import asyncio
import json
import os
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx

from ..models import ConsultSession, Project, User


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------


class AbstractStore(ABC):
    """Async key-value store for ConsultSession and Project objects."""

    @abstractmethod
    async def get_session(self, session_id: str) -> Optional[ConsultSession]:
        """Retrieve a ConsultSession by its ID, or None if not found."""
        ...

    @abstractmethod
    async def set_session(self, session: ConsultSession) -> None:
        """Persist a ConsultSession, overwriting any existing record with the same ID."""
        ...

    @abstractmethod
    async def list_sessions(self, owner_id: Optional[str] = None) -> list[ConsultSession]:
        """Return all sessions, optionally filtered by owner_id, newest first."""
        ...

    @abstractmethod
    async def get_project(self, project_id: str) -> Optional[Project]:
        """Retrieve a Project by its ID, or None if not found."""
        ...

    @abstractmethod
    async def set_project(self, project: Project) -> None:
        """Persist a Project, overwriting any existing record with the same ID."""
        ...

    @abstractmethod
    async def list_projects(self, owner_id: Optional[str] = None) -> list[Project]:
        """Return all projects, optionally filtered by owner_id, newest first."""
        ...

    @abstractmethod
    async def get_user(self, github_id: str) -> Optional[User]:
        """Retrieve a User by their GitHub ID, or None if not found."""
        ...

    @abstractmethod
    async def set_user(self, user: User) -> None:
        """Persist a User, overwriting any existing record with the same GitHub ID."""
        ...

    @abstractmethod
    async def list_users(self) -> list[User]:
        """Return all users, newest first."""
        ...


# ---------------------------------------------------------------------------
# In-memory backend (default)
# ---------------------------------------------------------------------------


class MemoryStore(AbstractStore):
    """Thread-safe in-memory store. Data is lost when the process restarts."""

    def __init__(self) -> None:
        self._sessions: dict[str, ConsultSession] = {}
        self._projects: dict[str, Project] = {}
        self._users: dict[str, User] = {}
        self._lock = asyncio.Lock()

    async def get_session(self, session_id: str) -> Optional[ConsultSession]:
        return self._sessions.get(session_id)

    async def set_session(self, session: ConsultSession) -> None:
        async with self._lock:
            self._sessions[session.id] = session

    async def list_sessions(self, owner_id: Optional[str] = None) -> list[ConsultSession]:
        items = list(self._sessions.values())
        if owner_id is not None:
            items = [s for s in items if s.owner_id == owner_id]
        return sorted(items, key=lambda s: s.created_at, reverse=True)

    async def get_project(self, project_id: str) -> Optional[Project]:
        return self._projects.get(project_id)

    async def set_project(self, project: Project) -> None:
        async with self._lock:
            self._projects[project.id] = project

    async def list_projects(self, owner_id: Optional[str] = None) -> list[Project]:
        items = list(self._projects.values())
        if owner_id is not None:
            items = [p for p in items if p.owner_id == owner_id]
        return sorted(items, key=lambda p: p.created_at, reverse=True)

    async def get_user(self, github_id: str) -> Optional[User]:
        return self._users.get(github_id)

    async def set_user(self, user: User) -> None:
        async with self._lock:
            self._users[user.github_id] = user

    async def list_users(self) -> list[User]:
        return sorted(self._users.values(), key=lambda u: u.created_at, reverse=True)


# ---------------------------------------------------------------------------
# JSON-file backend
# ---------------------------------------------------------------------------


class JsonFileStore(AbstractStore):
    """
    Persists all data as a single JSON file on disk.

    Suitable for single-instance deployments where you want data to survive
    restarts without running a database. Set STORAGE_PATH to override the
    default location (./data/store.json).
    """

    def __init__(self, path: str = "./data/store.json") -> None:
        self._path = Path(path)
        self._lock = asyncio.Lock()
        self._sessions: dict[str, ConsultSession] = {}
        self._projects: dict[str, Project] = {}
        self._users: dict[str, User] = {}
        self._loaded = False

    def _ensure_dir(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> None:
        if self._loaded:
            return
        self._ensure_dir()
        if self._path.exists():
            try:
                raw = json.loads(self._path.read_text(encoding="utf-8"))
                for sid, sdata in raw.get("sessions", {}).items():
                    self._sessions[sid] = ConsultSession.model_validate(sdata)
                for pid, pdata in raw.get("projects", {}).items():
                    self._projects[pid] = Project.model_validate(pdata)
                for uid, udata in raw.get("users", {}).items():
                    self._users[uid] = User.model_validate(udata)
            except Exception as exc:
                print(f"[JsonFileStore] Failed to load {self._path}: {exc}")
        self._loaded = True

    def _save(self) -> None:
        self._ensure_dir()
        data = {
            "sessions": {sid: s.model_dump(mode="json") for sid, s in self._sessions.items()},
            "projects": {pid: p.model_dump(mode="json") for pid, p in self._projects.items()},
            "users": {uid: u.model_dump(mode="json") for uid, u in self._users.items()},
        }
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        tmp.replace(self._path)

    async def get_session(self, session_id: str) -> Optional[ConsultSession]:
        async with self._lock:
            self._load()
            return self._sessions.get(session_id)

    async def set_session(self, session: ConsultSession) -> None:
        async with self._lock:
            self._load()
            self._sessions[session.id] = session
            self._save()

    async def list_sessions(self, owner_id: Optional[str] = None) -> list[ConsultSession]:
        async with self._lock:
            self._load()
            items = list(self._sessions.values())
        if owner_id is not None:
            items = [s for s in items if s.owner_id == owner_id]
        return sorted(items, key=lambda s: s.created_at, reverse=True)

    async def get_project(self, project_id: str) -> Optional[Project]:
        async with self._lock:
            self._load()
            return self._projects.get(project_id)

    async def set_project(self, project: Project) -> None:
        async with self._lock:
            self._load()
            self._projects[project.id] = project
            self._save()

    async def list_projects(self, owner_id: Optional[str] = None) -> list[Project]:
        async with self._lock:
            self._load()
            items = list(self._projects.values())
        if owner_id is not None:
            items = [p for p in items if p.owner_id == owner_id]
        return sorted(items, key=lambda p: p.created_at, reverse=True)

    async def get_user(self, github_id: str) -> Optional[User]:
        async with self._lock:
            self._load()
            return self._users.get(github_id)

    async def set_user(self, user: User) -> None:
        async with self._lock:
            self._load()
            self._users[user.github_id] = user
            self._save()

    async def list_users(self) -> list[User]:
        async with self._lock:
            self._load()
            items = list(self._users.values())
        return sorted(items, key=lambda u: u.created_at, reverse=True)


# ---------------------------------------------------------------------------
# Puter KV backend
# ---------------------------------------------------------------------------

_PUTER_KV_BASE = "https://api.puter.com/kv"


class PuterKVStore(AbstractStore):
    """
    Persists data in Puter's cloud key-value store.

    Requires:
        PUTER_AUTH_TOKEN — Puter session token (same as LLM config)
        PUTER_KV_BASE    — optional override for KV endpoint (default: https://api.puter.com/kv)

    Keys are namespaced as:
        session:{id}  → ConsultSession JSON
        project:{id}  → Project JSON
        _sessions_index → JSON list of all session IDs
        _projects_index → JSON list of all project IDs
    """

    def __init__(self) -> None:
        token = os.getenv("PUTER_AUTH_TOKEN", "")
        base = os.getenv("PUTER_KV_BASE", _PUTER_KV_BASE)
        self._base = base.rstrip("/")
        self._headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    async def _kv_get(self, key: str) -> Optional[str]:
        async with httpx.AsyncClient() as client:
            try:
                r = await client.get(f"{self._base}/get", params={"key": key}, headers=self._headers, timeout=10)
                if r.status_code == 200:
                    return r.text
                return None
            except Exception as exc:
                print(f"[PuterKVStore] GET {key} failed: {exc}")
                return None

    async def _kv_set(self, key: str, value: str) -> None:
        async with httpx.AsyncClient() as client:
            try:
                await client.post(
                    f"{self._base}/set",
                    json={"key": key, "value": value},
                    headers=self._headers,
                    timeout=10,
                )
            except Exception as exc:
                print(f"[PuterKVStore] SET {key} failed: {exc}")

    async def _kv_list(self, pattern: str = "*") -> list[str]:
        async with httpx.AsyncClient() as client:
            try:
                r = await client.get(f"{self._base}/list", params={"pattern": pattern}, headers=self._headers, timeout=10)
                if r.status_code == 200:
                    return r.json()
            except Exception as exc:
                print(f"[PuterKVStore] LIST {pattern} failed: {exc}")
            return []

    async def get_session(self, session_id: str) -> Optional[ConsultSession]:
        raw = await self._kv_get(f"session:{session_id}")
        if not raw:
            return None
        try:
            return ConsultSession.model_validate_json(raw)
        except Exception:
            return None

    async def set_session(self, session: ConsultSession) -> None:
        await self._kv_set(f"session:{session.id}", session.model_dump_json())

    async def list_sessions(self, owner_id: Optional[str] = None) -> list[ConsultSession]:
        keys = await self._kv_list("session:*")
        results = []
        for key in keys:
            sid = key.removeprefix("session:")
            s = await self.get_session(sid)
            if s and (owner_id is None or s.owner_id == owner_id):
                results.append(s)
        return sorted(results, key=lambda s: s.created_at, reverse=True)

    async def get_project(self, project_id: str) -> Optional[Project]:
        raw = await self._kv_get(f"project:{project_id}")
        if not raw:
            return None
        try:
            return Project.model_validate_json(raw)
        except Exception:
            return None

    async def set_project(self, project: Project) -> None:
        await self._kv_set(f"project:{project.id}", project.model_dump_json())

    async def list_projects(self, owner_id: Optional[str] = None) -> list[Project]:
        keys = await self._kv_list("project:*")
        results = []
        for key in keys:
            pid = key.removeprefix("project:")
            p = await self.get_project(pid)
            if p and (owner_id is None or p.owner_id == owner_id):
                results.append(p)
        return sorted(results, key=lambda p: p.created_at, reverse=True)

    async def get_user(self, github_id: str) -> Optional[User]:
        raw = await self._kv_get(f"user:{github_id}")
        if not raw:
            return None
        try:
            return User.model_validate_json(raw)
        except Exception:
            return None

    async def set_user(self, user: User) -> None:
        await self._kv_set(f"user:{user.github_id}", user.model_dump_json())

    async def list_users(self) -> list[User]:
        keys = await self._kv_list("user:*")
        results = []
        for key in keys:
            uid = key.removeprefix("user:")
            u = await self.get_user(uid)
            if u:
                results.append(u)
        return sorted(results, key=lambda u: u.created_at, reverse=True)


# ---------------------------------------------------------------------------
# Factory — select backend from env
# ---------------------------------------------------------------------------


def make_store() -> AbstractStore:
    """Build and return the configured store backend.

    Reads the ``STORAGE_BACKEND`` environment variable to select a backend.
    Additional variables are consumed by specific backends:

    * ``json_file`` — ``STORAGE_PATH`` (default: ``./data/store.json``)
    * ``puter_kv``  — ``PUTER_AUTH_TOKEN``, ``PUTER_KV_BASE``

    Returns:
        AbstractStore: A ready-to-use store instance. One of
            :class:`MemoryStore`, :class:`JsonFileStore`, or
            :class:`PuterKVStore` depending on ``STORAGE_BACKEND``.
    """
    backend = os.getenv("STORAGE_BACKEND", "memory").lower()
    if backend == "json_file":
        path = os.getenv("STORAGE_PATH", "./data/store.json")
        print(f"[Store] Using JSON file backend: {path}")
        return JsonFileStore(path=path)
    if backend == "puter_kv":
        print("[Store] Using Puter KV backend")
        return PuterKVStore()
    print("[Store] Using in-memory backend")
    return MemoryStore()


# Module-level singleton — initialised once at import time
store: AbstractStore = make_store()
