"""
api/projects.py — Project status, proposal, demo URL, and usage routes.

GET  /api/projects                  — list projects for the authenticated user
GET  /api/projects/{id}             — project status + task progress
GET  /api/projects/{id}/proposal    — full proposal object
POST /api/projects/{id}/demo-url    — admin: set the live demo URL
GET  /api/projects/{id}/demo        — client: get demo URL (requires deposit)
GET  /api/projects/{id}/usage       — LLM token + cost breakdown
POST /api/projects/{id}/push-github — push delivery files to user's GitHub repo
"""
from __future__ import annotations

from datetime import datetime

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from . import _store
from ..api.admin import log_event
from .auth import get_current_user


async def list_projects(request: Request) -> JSONResponse:
    """Return all projects owned by the currently authenticated user.

    Args:
        request (Request): Must carry a valid authentication credential
            (resolved by ``get_current_user``).

    Returns:
        JSONResponse: 200 list of project summary objects, each containing
        ``project_id``, ``name``, ``status``, payment flags, ``progress``,
        ``demo_available``, ``github_repo_url``, and timestamps; 401 if the
        request is not authenticated.
    """
    user = await get_current_user(request)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    all_projects = await _store.store.list_projects()
    user_projects = [p for p in all_projects if p.github_user_id == user.github_id]

    return JSONResponse([
        {
            "project_id": p.id,
            "name": p.name,
            "status": p.status,
            "deposit_paid": p.deposit_paid,
            "final_paid": p.final_paid,
            "total_price_usd": p.total_price_usd,
            "demo_available": bool(p.demo_url and p.deposit_paid),
            "github_repo_url": p.github_repo_url,
            "progress": {
                "done": sum(1 for t in p.tasks if t.status == "done"),
                "total": len(p.tasks),
            },
            "created_at": p.created_at.isoformat(),
            "updated_at": p.updated_at.isoformat(),
        }
        for p in user_projects
    ])


async def get_project(request: Request) -> JSONResponse:
    """Return project status and per-task progress for a single project.

    Args:
        request (Request): Path param ``project_id`` (str).

    Returns:
        JSONResponse: 200 ``{"project_id", "name", "status", "deposit_paid",
        "final_paid", "total_price_usd", "tasks", "progress", "demo_available",
        "deployment_status", "github_repo_url", "llm_cost_usd", "created_at",
        "updated_at"}``; 404 if the project does not exist.
    """
    project_id = request.path_params["project_id"]
    project = await _store.store.get_project(project_id)
    if not project:
        return JSONResponse({"error": "Project not found"}, status_code=404)

    tasks_summary = [
        {
            "id": t.id,
            "title": t.title,
            "status": t.status,
            "assigned_to": t.assigned_to,
        }
        for t in project.tasks
    ]
    done = sum(1 for t in project.tasks if t.status == "done")
    total = len(project.tasks)

    return JSONResponse({
        "project_id": project.id,
        "name": project.name,
        "status": project.status,
        "deposit_paid": project.deposit_paid,
        "final_paid": project.final_paid,
        "total_price_usd": project.total_price_usd,
        "tasks": tasks_summary,
        "progress": {"done": done, "total": total},
        "demo_available": bool(project.demo_url and project.deposit_paid),
        "deployment_status": project.deployment_status,
        "github_repo_url": project.github_repo_url,
        "llm_cost_usd": round(project.llm_cost_usd, 4),
        "created_at": project.created_at.isoformat(),
        "updated_at": project.updated_at.isoformat(),
    })


async def get_proposal(request: Request) -> JSONResponse:
    """Return the full proposal object for a project.

    Args:
        request (Request): Path param ``project_id`` (str).

    Returns:
        JSONResponse: 200 ``{"project_id", "project_name", "problem_statement",
        "solution_overview", "implementation_plan", "deliverables",
        "estimated_hours", "delivery_eta_days", "total_price_usd",
        "deposit_amount_usd", "final_amount_usd", "payment_structure",
        "deposit_paid", "final_paid"}``; 404 if the project does not exist or
        the proposal is not yet ready.
    """
    project_id = request.path_params["project_id"]
    project = await _store.store.get_project(project_id)
    if not project:
        return JSONResponse({"error": "Project not found"}, status_code=404)

    if not project.proposal:
        return JSONResponse({"error": "Proposal not yet ready"}, status_code=404)

    p = project.proposal
    return JSONResponse({
        "project_id": project.id,
        "project_name": project.name,
        "problem_statement": p.problem_statement,
        "solution_overview": p.solution_overview,
        "implementation_plan": p.implementation_plan,
        "deliverables": p.deliverables,
        "estimated_hours": p.estimated_hours,
        "delivery_eta_days": p.delivery_eta_days,
        "total_price_usd": p.total_price_usd,
        "deposit_amount_usd": p.deposit_amount_usd,
        "final_amount_usd": p.final_amount_usd,
        "payment_structure": p.payment_structure,
        "deposit_paid": project.deposit_paid,
        "final_paid": project.final_paid,
    })


async def set_demo_url(request: Request) -> JSONResponse:
    """Admin endpoint — set the live demo URL for a project.

    Also fires a demo-ready email notification to the client.

    Args:
        request (Request): Path param ``project_id`` (str); POST body must
            contain ``demo_url`` (str).

    Returns:
        JSONResponse: 200 ``{"project_id", "demo_url"}`` on success; 400 for
        invalid JSON; 404 if the project does not exist; 422 if ``demo_url`` is
        missing or empty.
    """
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

    # Email the client that the demo is ready
    from ..notifications import notify_demo_ready
    try:
        notify_demo_ready(project, client_email=project.client_id, client_name=project.client_id)
    except Exception as exc:
        log_event("warn", "notifications", f"Demo email failed: {exc}", project_id=project_id)

    log_event("info", "projects", f"Demo URL set: {demo_url}", project_id=project_id)
    return JSONResponse({"project_id": project_id, "demo_url": demo_url})


async def get_demo(request: Request) -> JSONResponse:
    """Return the demo URL — only available after deposit is paid.

    Args:
        request (Request): Path param ``project_id`` (str).

    Returns:
        JSONResponse: 200 ``{"project_id", "demo_url", "final_paid"}`` on
        success; 403 if the deposit has not been paid; 404 if the project does
        not exist or the demo URL has not been set yet.
    """
    project_id = request.path_params["project_id"]
    project = await _store.store.get_project(project_id)
    if not project:
        return JSONResponse({"error": "Project not found"}, status_code=404)

    if not project.deposit_paid:
        return JSONResponse(
            {"error": "Deposit payment required before viewing the demo"},
            status_code=403,
        )

    if not project.demo_url:
        return JSONResponse(
            {"error": "Demo not yet available — the team is still building"},
            status_code=404,
        )

    return JSONResponse({
        "project_id": project_id,
        "demo_url": project.demo_url,
        "final_paid": project.final_paid,
    })


async def get_usage(request: Request) -> JSONResponse:
    """Return LLM token usage and estimated cost for a project.

    Args:
        request (Request): Path param ``project_id`` (str).

    Returns:
        JSONResponse: 200 ``{"project_id", "tokens_used", "llm_requests",
        "llm_cost_usd", "budget_tokens", "budget_remaining",
        "task_breakdown"}``; 404 if the project does not exist.
    """
    project_id = request.path_params["project_id"]
    project = await _store.store.get_project(project_id)
    if not project:
        return JSONResponse({"error": "Project not found"}, status_code=404)

    task_breakdown = [
        {
            "task_id": t.id,
            "title": t.title,
            "tokens_used": t.tokens_used,
            "cost_usd": round(t.cost_usd, 4),
        }
        for t in project.tasks
    ]

    return JSONResponse({
        "project_id": project_id,
        "tokens_used": project.tokens_used,
        "llm_requests": project.llm_requests,
        "llm_cost_usd": round(project.llm_cost_usd, 4),
        "budget_tokens": project.budget_tokens,
        "budget_remaining": max(0, project.budget_tokens - project.tokens_used),
        "task_breakdown": task_breakdown,
    })


async def push_to_github(request: Request) -> JSONResponse:
    """Push project delivery files to the authenticated user's GitHub account.

    Args:
        request (Request): Path param ``project_id`` (str); must carry a valid
            authentication credential with a GitHub access token.

    Returns:
        JSONResponse: 200 ``{"repo_url"}`` on success; 401 if not
        authenticated; 403 if the project belongs to a different GitHub user;
        404 if the project does not exist; 422 if the GitHub access token is
        unavailable; 500 if the push operation fails.
    """
    user = await get_current_user(request)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    project_id = request.path_params["project_id"]
    project = await _store.store.get_project(project_id)
    if not project:
        return JSONResponse({"error": "Project not found"}, status_code=404)

    if project.github_user_id and project.github_user_id != user.github_id:
        return JSONResponse({"error": "Forbidden"}, status_code=403)

    if not user.access_token:
        return JSONResponse({"error": "GitHub access token not available"}, status_code=422)

    from .github_delivery import push_project_to_github
    try:
        repo_url = await push_project_to_github(user.access_token, user.login, project)
        project.github_repo_url = repo_url
        project.github_user_id = user.github_id
        project.updated_at = datetime.utcnow()
        await _store.store.set_project(project)
        log_event("info", "projects", f"Pushed to GitHub: {repo_url}", project_id=project_id)
        return JSONResponse({"repo_url": repo_url})
    except Exception as exc:
        log_event("error", "projects", f"GitHub push failed: {exc}", project_id=project_id)
        return JSONResponse({"error": f"GitHub push failed: {exc}"}, status_code=500)


routes = [
    Route("/api/projects", list_projects, methods=["GET"]),
    Route("/api/projects/{project_id}", get_project, methods=["GET"]),
    Route("/api/projects/{project_id}/proposal", get_proposal, methods=["GET"]),
    Route("/api/projects/{project_id}/demo-url", set_demo_url, methods=["POST"]),
    Route("/api/projects/{project_id}/demo", get_demo, methods=["GET"]),
    Route("/api/projects/{project_id}/usage", get_usage, methods=["GET"]),
    Route("/api/projects/{project_id}/push-github", push_to_github, methods=["POST"]),
]
