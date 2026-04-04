"""
api/admin.py — Admin REST API routes.

All routes require the X-Admin-Key header matching ADMIN_API_KEY env var.
If ADMIN_API_KEY is not set, admin routes return 503.

GET  /api/admin/projects          — list all projects (optionally filter by owner_id)
GET  /api/admin/sessions          — list all sessions
GET  /api/admin/projects/{id}     — full project detail including task outputs
POST /api/admin/projects/{id}/demo-url — set demo URL (same as projects.py but admin-gated)
GET  /api/admin/logs              — recent server log entries
POST /api/admin/projects/{id}/status  — manually set project status
"""
from __future__ import annotations

import os
from collections import deque
from datetime import datetime

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from . import _store

# ---------------------------------------------------------------------------
# In-process log ring buffer — agents write here via log_event()
# ---------------------------------------------------------------------------

_LOG_BUFFER: deque[dict] = deque(maxlen=500)


def log_event(level: str, source: str, message: str, project_id: str = "") -> None:
    """Append an entry to the admin log ring buffer."""
    _LOG_BUFFER.appendleft({
        "timestamp": datetime.utcnow().isoformat(),
        "level": level,
        "source": source,
        "message": message,
        "project_id": project_id,
    })


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------


def _check_auth(request: Request) -> bool:
    """Return True if the request carries a valid admin key."""
    admin_key = os.getenv("ADMIN_API_KEY", "")
    if not admin_key:
        return False
    provided = request.headers.get("X-Admin-Key", "")
    return provided == admin_key


def _auth_error(configured: bool) -> JSONResponse:
    if not configured:
        return JSONResponse({"error": "Admin API not configured — set ADMIN_API_KEY"}, status_code=503)
    return JSONResponse({"error": "Invalid or missing X-Admin-Key header"}, status_code=401)


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------


async def list_projects(request: Request) -> JSONResponse:
    """List all projects, optionally filtered by owner_id query param."""
    if not os.getenv("ADMIN_API_KEY") or not _check_auth(request):
        return _auth_error(bool(os.getenv("ADMIN_API_KEY")))

    owner_id = request.query_params.get("owner_id")
    all_projects = await _store.store.list_projects(owner_id=owner_id)

    return JSONResponse({
        "projects": [
            {
                "project_id": p.id,
                "name": p.name,
                "client_id": p.client_id,
                "owner_id": p.owner_id,
                "status": p.status,
                "deposit_paid": p.deposit_paid,
                "final_paid": p.final_paid,
                "total_price_usd": p.total_price_usd,
                "llm_cost_usd": round(p.llm_cost_usd, 4),
                "llm_requests": p.llm_requests,
                "tokens_used": p.tokens_used,
                "task_count": len(p.tasks),
                "tasks_done": sum(1 for t in p.tasks if t.status == "done"),
                "demo_url": p.demo_url,
                "deployment_status": p.deployment_status,
                "created_at": p.created_at.isoformat(),
                "updated_at": p.updated_at.isoformat(),
            }
            for p in all_projects
        ],
        "total": len(all_projects),
    })


async def list_sessions(request: Request) -> JSONResponse:
    """List all consultation sessions, optionally filtered by owner_id."""
    if not os.getenv("ADMIN_API_KEY") or not _check_auth(request):
        return _auth_error(bool(os.getenv("ADMIN_API_KEY")))

    owner_id = request.query_params.get("owner_id")
    all_sessions = await _store.store.list_sessions(owner_id=owner_id)

    return JSONResponse({
        "sessions": [
            {
                "session_id": s.id,
                "client_name": s.client_name,
                "client_email": s.client_email,
                "owner_id": s.owner_id,
                "status": s.status,
                "project_id": s.project_id,
                "message_count": len(s.messages),
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat(),
            }
            for s in all_sessions
        ],
        "total": len(all_sessions),
    })


async def get_project_detail(request: Request) -> JSONResponse:
    """Full project detail including task outputs and cost breakdown."""
    if not os.getenv("ADMIN_API_KEY") or not _check_auth(request):
        return _auth_error(bool(os.getenv("ADMIN_API_KEY")))

    project_id = request.path_params["project_id"]
    project = await _store.store.get_project(project_id)
    if not project:
        return JSONResponse({"error": "Project not found"}, status_code=404)

    return JSONResponse({
        "project_id": project.id,
        "name": project.name,
        "description": project.description,
        "client_id": project.client_id,
        "owner_id": project.owner_id,
        "status": project.status,
        "deposit_paid": project.deposit_paid,
        "final_paid": project.final_paid,
        "total_price_usd": project.total_price_usd,
        "llm_cost_usd": round(project.llm_cost_usd, 4),
        "llm_requests": project.llm_requests,
        "tokens_used": project.tokens_used,
        "demo_url": project.demo_url,
        "deployment_status": project.deployment_status,
        "proposal": project.proposal.model_dump() if project.proposal else None,
        "tasks": [
            {
                "id": t.id,
                "title": t.title,
                "description": t.description,
                "assigned_to": t.assigned_to,
                "status": t.status,
                "retry_count": t.retry_count,
                "tokens_used": t.tokens_used,
                "cost_usd": round(t.cost_usd, 4),
                "output": t.output,
                "qa_feedback": t.qa_feedback,
                "created_at": t.created_at.isoformat(),
                "updated_at": t.updated_at.isoformat(),
            }
            for t in project.tasks
        ],
        "created_at": project.created_at.isoformat(),
        "updated_at": project.updated_at.isoformat(),
    })


async def admin_set_demo_url(request: Request) -> JSONResponse:
    """Admin: set the live demo URL for a project."""
    if not os.getenv("ADMIN_API_KEY") or not _check_auth(request):
        return _auth_error(bool(os.getenv("ADMIN_API_KEY")))

    project_id = request.path_params["project_id"]
    project = await _store.store.get_project(project_id)
    if not project:
        return JSONResponse({"error": "Project not found"}, status_code=404)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

    demo_url = body.get("demo_url", "").strip()
    if not demo_url:
        return JSONResponse({"error": "demo_url is required"}, status_code=422)

    project.demo_url = demo_url
    project.updated_at = datetime.utcnow()
    await _store.store.set_project(project)

    log_event("info", "admin", f"Demo URL set: {demo_url}", project_id=project_id)
    return JSONResponse({"project_id": project_id, "demo_url": demo_url})


async def admin_set_status(request: Request) -> JSONResponse:
    """Admin: manually override a project's status."""
    if not os.getenv("ADMIN_API_KEY") or not _check_auth(request):
        return _auth_error(bool(os.getenv("ADMIN_API_KEY")))

    project_id = request.path_params["project_id"]
    project = await _store.store.get_project(project_id)
    if not project:
        return JSONResponse({"error": "Project not found"}, status_code=404)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

    new_status = body.get("status", "").strip()
    valid = {"intake", "planning", "execution", "qa", "delivered", "cancelled"}
    if new_status not in valid:
        return JSONResponse({"error": f"Invalid status. Valid: {sorted(valid)}"}, status_code=422)

    project.status = new_status  # type: ignore[assignment]
    project.updated_at = datetime.utcnow()
    await _store.store.set_project(project)

    log_event("info", "admin", f"Status set to {new_status}", project_id=project_id)
    return JSONResponse({"project_id": project_id, "status": new_status})


async def get_logs(request: Request) -> JSONResponse:
    """Return recent server log entries (last 200, newest first)."""
    if not os.getenv("ADMIN_API_KEY") or not _check_auth(request):
        return _auth_error(bool(os.getenv("ADMIN_API_KEY")))

    limit = min(int(request.query_params.get("limit", "100")), 500)
    logs = list(_LOG_BUFFER)[:limit]

    return JSONResponse({"logs": logs, "total": len(_LOG_BUFFER)})


routes = [
    Route("/api/admin/projects", list_projects, methods=["GET"]),
    Route("/api/admin/sessions", list_sessions, methods=["GET"]),
    Route("/api/admin/projects/{project_id}", get_project_detail, methods=["GET"]),
    Route("/api/admin/projects/{project_id}/demo-url", admin_set_demo_url, methods=["POST"]),
    Route("/api/admin/projects/{project_id}/status", admin_set_status, methods=["POST"]),
    Route("/api/admin/logs", get_logs, methods=["GET"]),
]
