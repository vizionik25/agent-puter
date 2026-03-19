"""
api/projects.py — Project status, proposal, and demo URL routes.

GET  /api/projects/{id}           — project status + task progress
GET  /api/projects/{id}/proposal  — full proposal object
POST /api/projects/{id}/demo-url  — admin: set the live demo URL
GET  /api/projects/{id}/demo      — client: get demo URL (requires deposit)
"""
from __future__ import annotations

from datetime import datetime

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from . import _store


async def get_project(request: Request) -> JSONResponse:
    project_id = request.path_params["project_id"]
    project = _store.projects.get(project_id)
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
        "created_at": project.created_at.isoformat(),
        "updated_at": project.updated_at.isoformat(),
    })


async def get_proposal(request: Request) -> JSONResponse:
    project_id = request.path_params["project_id"]
    project = _store.projects.get(project_id)
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
    """Admin endpoint — set the live demo URL for a project."""
    project_id = request.path_params["project_id"]
    project = _store.projects.get(project_id)
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
    _store.projects[project_id] = project

    return JSONResponse({"project_id": project_id, "demo_url": demo_url})


async def get_demo(request: Request) -> JSONResponse:
    """Return the demo URL — only available after deposit is paid."""
    project_id = request.path_params["project_id"]
    project = _store.projects.get(project_id)
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


routes = [
    Route("/api/projects/{project_id}", get_project, methods=["GET"]),
    Route("/api/projects/{project_id}/proposal", get_proposal, methods=["GET"]),
    Route("/api/projects/{project_id}/demo-url", set_demo_url, methods=["POST"]),
    Route("/api/projects/{project_id}/demo", get_demo, methods=["GET"]),
]
