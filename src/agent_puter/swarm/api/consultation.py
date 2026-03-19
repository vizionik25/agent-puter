"""
api/consultation.py — Consultation session routes.

POST /api/consult/start          — create session, get sales agent greeting
POST /api/consult/{id}/message   — send user message, get agent reply
GET  /api/consult/{id}           — fetch session transcript + status
POST /api/consult/{id}/complete  — mark session complete, kick off agency loop
"""
from __future__ import annotations

import os
from datetime import datetime

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from ..models import ConsultMessage, ConsultSession
from ..sales_agent import sales_agent

# Shared in-memory store — imported by main.py to inject into AgencyDeps
from . import _store


async def start(request: Request) -> JSONResponse:
    """Create a new consultation session and get the sales agent's opening greeting."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

    client_name = body.get("client_name", "").strip()
    client_email = body.get("client_email", "").strip()
    initial_message = body.get("initial_message", body.get("message", "")).strip()

    if not client_name or not client_email:
        return JSONResponse(
            {"error": "client_name and client_email are required"},
            status_code=422,
        )

    session = ConsultSession(
        client_name=client_name,
        client_email=client_email,
    )

    # Build the prompt for the sales agent
    prompt = (
        f"A new client has arrived for a consultation.\n"
        f"Name: {client_name}\n"
        f"Email: {client_email}\n"
    )
    if initial_message:
        prompt += f"Their initial request: {initial_message}\n"
        session.messages.append(ConsultMessage(role="user", content=initial_message))

    prompt += (
        "\nGreet them warmly and professionally. Ask one focused question to "
        "understand their core problem or goal. Keep your response concise (2-3 sentences)."
    )

    result = await sales_agent.run(prompt)
    agent_reply = str(result.output)

    session.messages.append(ConsultMessage(role="agent", content=agent_reply))
    _store.sessions[session.id] = session

    return JSONResponse({
        "session_id": session.id,
        "reply": agent_reply,
        "status": session.status,
    })


async def send_message(request: Request) -> JSONResponse:
    """Append a user message to the session and return the agent's reply."""
    session_id = request.path_params["session_id"]
    session = _store.sessions.get(session_id)
    if not session:
        return JSONResponse({"error": "Session not found"}, status_code=404)

    if session.status == "complete":
        return JSONResponse({"error": "Session is already complete"}, status_code=400)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

    user_msg = body.get("message", "").strip()
    if not user_msg:
        return JSONResponse({"error": "message is required"}, status_code=422)

    session.messages.append(ConsultMessage(role="user", content=user_msg))
    session.updated_at = datetime.utcnow()

    # Build conversation context for the agent
    history = "\n".join(
        f"{'Client' if m.role == 'user' else 'You'}: {m.content}"
        for m in session.messages
    )
    prompt = (
        f"You are in a consultation with {session.client_name}.\n\n"
        f"Conversation so far:\n{history}\n\n"
        "Continue the consultation. Ask clarifying questions to fully understand "
        "their needs. When you have enough information, summarize the project and "
        "tell them the team will prepare a detailed proposal. Keep replies concise."
    )

    result = await sales_agent.run(prompt)
    agent_reply = str(result.output)

    session.messages.append(ConsultMessage(role="agent", content=agent_reply))
    _store.sessions[session_id] = session

    return JSONResponse({
        "reply": agent_reply,
        "status": session.status,
    })


async def get_session(request: Request) -> JSONResponse:
    """Return the full session transcript and status."""
    session_id = request.path_params["session_id"]
    session = _store.sessions.get(session_id)
    if not session:
        return JSONResponse({"error": "Session not found"}, status_code=404)

    return JSONResponse({
        "session_id": session.id,
        "client_name": session.client_name,
        "client_email": session.client_email,
        "messages": [
            {"role": m.role, "content": m.content, "timestamp": m.timestamp.isoformat()}
            for m in session.messages
        ],
        "project_id": session.project_id,
        "status": session.status,
    })


async def complete_session(request: Request) -> JSONResponse:
    """Mark the consultation complete and kick off the agency intake loop."""
    session_id = request.path_params["session_id"]
    session = _store.sessions.get(session_id)
    if not session:
        return JSONResponse({"error": "Session not found"}, status_code=404)

    if session.status == "complete":
        return JSONResponse({
            "session_id": session.id,
            "project_id": session.project_id,
            "status": "already_complete",
        })

    # Build a consolidated request from the transcript
    user_messages = [m.content for m in session.messages if m.role == "user"]
    consolidated = " | ".join(user_messages) if user_messages else "No details provided."

    # Import Agency lazily to avoid circular deps
    from ..agency import Agency
    from ..models import AgencyDeps, Proposal, Project, ProjectStatus
    import os

    deps = AgencyDeps(
        puter_token=os.getenv("PUTER_AUTH_TOKEN"),
        model_name=os.getenv("PUTER_MODEL"),
        projects=_store.projects,
        sessions=_store.sessions,
    )

    result = await Agency(deps).handle_client_request(
        consolidated, client_id=session.client_email
    )
    project_id = result["project_id"]

    # Generate a basic proposal stub (a full LLM-generated proposal can be added later)
    project = _store.projects.get(project_id)
    if project and project.proposal is None:
        base_price = max(500.0, len(consolidated.split()) * 12.5)
        proposal = Proposal(
            problem_statement=f"Client {session.client_name} needs: {consolidated[:300]}",
            solution_overview=(
                "Our autonomous AI consulting agency will design, build, and deliver "
                "a custom solution tailored to your specific requirements."
            ),
            implementation_plan=(
                "1. Requirements analysis & architecture design\n"
                "2. Iterative development with automated QA\n"
                "3. Demo deployment for client review\n"
                "4. Final delivery after payment clearance"
            ),
            deliverables=["Full source code", "Documentation", "Deployment guide"],
            estimated_hours=max(10, len(consolidated.split()) // 5),
            delivery_eta_days=14,
            total_price_usd=round(base_price, 2),
            deposit_amount_usd=round(base_price * 0.20, 2),
            final_amount_usd=round(base_price * 0.80, 2),
        )
        project.proposal = proposal
        project.total_price_usd = proposal.total_price_usd
        _store.projects[project_id] = project

    session.project_id = project_id
    session.status = "complete"
    session.updated_at = datetime.utcnow()
    _store.sessions[session_id] = session

    return JSONResponse({
        "session_id": session.id,
        "project_id": project_id,
        "status": "complete",
    })


routes = [
    Route("/api/consult/start", start, methods=["POST"]),
    Route("/api/consult/{session_id}/message", send_message, methods=["POST"]),
    Route("/api/consult/{session_id}", get_session, methods=["GET"]),
    Route("/api/consult/{session_id}/complete", complete_session, methods=["POST"]),
]
