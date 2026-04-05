"""
api/consultation.py — Consultation session routes.

POST /api/consult/start               — create session, get sales agent greeting
POST /api/consult/{id}/message        — send user message, get agent reply
POST /api/consult/{id}/stream         — SSE streaming version of /message
GET  /api/consult/{id}                — fetch session transcript + status
POST /api/consult/{id}/complete       — mark session complete, kick off agency loop
"""
from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime

from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Route

from ..models import ConsultMessage, ConsultSession
from ..sales_agent import sales_agent
from . import _store
from ..api.admin import log_event


def _owner_id(request: Request) -> str:
    """Extract tenant owner_id from X-Agency-Key header, defaulting to 'default'."""
    from ..middleware import resolve_tenant
    return resolve_tenant(request)


def _estimate_cost(request_tokens: int, response_tokens: int) -> float:
    """Rough cost estimate in USD based on Claude Sonnet pricing ($3/$15 per MTok).

    Args:
        request_tokens (int): Number of input tokens consumed.
        response_tokens (int): Number of output tokens generated.

    Returns:
        float: Estimated cost in USD.
    """
    return (request_tokens * 3.0 + response_tokens * 15.0) / 1_000_000


async def start(request: Request) -> JSONResponse:
    """Create a new consultation session and get the sales agent's opening greeting.

    Args:
        request (Request): POST body must contain ``client_name`` (str) and
            ``client_email`` (str). Optional fields: ``initial_message`` / ``message``
            (str), ``github_user_id`` (str).

    Returns:
        JSONResponse: 200 ``{"session_id", "reply", "status"}`` on success;
        400 for invalid JSON; 422 if ``client_name`` or ``client_email`` are
        missing.
    """
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
        owner_id=_owner_id(request),
        github_user_id=body.get("github_user_id") or None,
    )

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
    await _store.store.set_session(session)

    log_event("info", "consultation", f"Session started: {session.id}", project_id="")
    return JSONResponse({
        "session_id": session.id,
        "reply": agent_reply,
        "status": session.status,
    })


async def send_message(request: Request) -> JSONResponse:
    """Append a user message to the session and return the agent's reply.

    Also tracks LLM token usage against the linked project when one exists.

    Args:
        request (Request): Path param ``session_id`` (str); POST body must
            contain ``message`` (str).

    Returns:
        JSONResponse: 200 ``{"reply", "status"}`` on success; 400 if the
        session is already complete or the JSON body is invalid; 404 if the
        session does not exist; 422 if ``message`` is missing or empty.
    """
    session_id = request.path_params["session_id"]
    session = await _store.store.get_session(session_id)
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

    # --- LLM cost tracking ---
    usage = result.usage()
    if usage:
        req_tok = usage.request_tokens or 0
        res_tok = usage.response_tokens or 0
        cost = _estimate_cost(req_tok, res_tok)
        # Update project cost if session is linked to a project
        if session.project_id:
            project = await _store.store.get_project(session.project_id)
            if project:
                project.tokens_used += req_tok + res_tok
                project.llm_requests += 1
                project.llm_cost_usd += cost
                project.updated_at = datetime.utcnow()
                await _store.store.set_project(project)

    session.messages.append(ConsultMessage(role="agent", content=agent_reply))
    await _store.store.set_session(session)

    return JSONResponse({
        "reply": agent_reply,
        "status": session.status,
    })


async def stream_message(request: Request) -> StreamingResponse:
    """Stream the agent's reply as server-sent events.

    SSE streaming version of ``/message``. Emits events:

    - ``{"type": "chunk", "text": "..."}`` — incremental text delta
    - ``{"type": "done", "status": "active"}`` — stream complete
    - ``{"type": "error", "message": "..."}`` — on any failure

    Args:
        request (Request): Path param ``session_id`` (str); POST body must
            contain ``message`` (str).

    Returns:
        StreamingResponse: ``text/event-stream`` response (200). Error
        conditions (session not found, already complete, bad JSON, missing
        message) are delivered as SSE error events with the corresponding HTTP
        status code (404, 400, 400, 422 respectively).
    """
    session_id = request.path_params["session_id"]
    session = await _store.store.get_session(session_id)
    if not session:
        async def _not_found():
            yield f'data: {json.dumps({"type": "error", "message": "Session not found"})}\n\n'
        return StreamingResponse(_not_found(), media_type="text/event-stream", status_code=404)

    if session.status == "complete":
        async def _complete():
            yield f'data: {json.dumps({"type": "error", "message": "Session already complete"})}\n\n'
        return StreamingResponse(_complete(), media_type="text/event-stream", status_code=400)

    try:
        body = await request.json()
    except Exception:
        async def _bad_body():
            yield f'data: {json.dumps({"type": "error", "message": "Invalid JSON body"})}\n\n'
        return StreamingResponse(_bad_body(), media_type="text/event-stream", status_code=400)

    user_msg = body.get("message", "").strip()
    if not user_msg:
        async def _no_msg():
            yield f'data: {json.dumps({"type": "error", "message": "message is required"})}\n\n'
        return StreamingResponse(_no_msg(), media_type="text/event-stream", status_code=422)

    session.messages.append(ConsultMessage(role="user", content=user_msg))
    session.updated_at = datetime.utcnow()

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

    # Capture session_id to close over in the generator
    _session_id = session_id

    async def _generate():
        full_reply = []
        try:
            async with sales_agent.run_stream(prompt) as streamed:
                async for chunk in streamed.stream_text(delta=True):
                    full_reply.append(chunk)
                    yield f'data: {json.dumps({"type": "chunk", "text": chunk})}\n\n'

            # Persist completed message
            reply_text = "".join(full_reply)
            sess = await _store.store.get_session(_session_id)
            if sess:
                sess.messages.append(ConsultMessage(role="agent", content=reply_text))
                sess.updated_at = datetime.utcnow()
                await _store.store.set_session(sess)

            yield f'data: {json.dumps({"type": "done", "status": "active"})}\n\n'
        except Exception as exc:
            yield f'data: {json.dumps({"type": "error", "message": str(exc)})}\n\n'

    return StreamingResponse(_generate(), media_type="text/event-stream")


async def get_session(request: Request) -> JSONResponse:
    """Return the full session transcript and status.

    Args:
        request (Request): Path param ``session_id`` (str).

    Returns:
        JSONResponse: 200 ``{"session_id", "client_name", "client_email",
        "owner_id", "messages", "project_id", "status"}`` where ``messages``
        is a list of ``{"role", "content", "timestamp"}`` objects; 404 if the
        session does not exist.
    """
    session_id = request.path_params["session_id"]
    session = await _store.store.get_session(session_id)
    if not session:
        return JSONResponse({"error": "Session not found"}, status_code=404)

    return JSONResponse({
        "session_id": session.id,
        "client_name": session.client_name,
        "client_email": session.client_email,
        "owner_id": session.owner_id,
        "messages": [
            {"role": m.role, "content": m.content, "timestamp": m.timestamp.isoformat()}
            for m in session.messages
        ],
        "project_id": session.project_id,
        "status": session.status,
    })


async def complete_session(request: Request) -> JSONResponse:
    """Mark the consultation complete and kick off the agency intake loop.

    Consolidates the session transcript, runs ``Agency.handle_client_request``
    to produce a project and proposal, persists all mutated state, and fires a
    proposal-ready email notification.

    Args:
        request (Request): Path param ``session_id`` (str).

    Returns:
        JSONResponse: 200 ``{"session_id", "project_id", "status"}``; if the
        session was already complete, ``status`` is ``"already_complete"``; 404
        if the session does not exist.
    """
    session_id = request.path_params["session_id"]
    session = await _store.store.get_session(session_id)
    if not session:
        return JSONResponse({"error": "Session not found"}, status_code=404)

    if session.status == "complete":
        return JSONResponse({
            "session_id": session.id,
            "project_id": session.project_id,
            "status": "already_complete",
        })

    user_messages = [m.content for m in session.messages if m.role == "user"]
    consolidated = " | ".join(user_messages) if user_messages else "No details provided."

    from ..agency import Agency
    from ..models import AgencyDeps, Proposal

    # Build a snapshot of current state for AgencyDeps
    all_projects = {p.id: p for p in await _store.store.list_projects()}
    all_sessions = {s.id: s for s in await _store.store.list_sessions()}

    deps = AgencyDeps(
        puter_token=os.getenv("PUTER_AUTH_TOKEN"),
        model_name=os.getenv("PUTER_MODEL"),
        projects=all_projects,
        sessions=all_sessions,
    )

    result = await Agency(deps).handle_client_request(
        consolidated, client_id=session.client_email
    )
    project_id = result["project_id"]

    # Persist any projects mutated by the agency loop
    for pid, proj in deps.projects.items():
        proj.owner_id = session.owner_id
        proj.github_user_id = session.github_user_id
        await _store.store.set_project(proj)

    project = await _store.store.get_project(project_id)
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
        await _store.store.set_project(project)

    session.project_id = project_id
    session.status = "complete"
    session.updated_at = datetime.utcnow()
    await _store.store.set_session(session)

    # Email notification (non-blocking)
    project = await _store.store.get_project(project_id)
    if project:
        from ..notifications import notify_proposal_ready
        try:
            notify_proposal_ready(project, session)
        except Exception as exc:
            log_event("warn", "notifications", f"Email failed: {exc}", project_id=project_id)

    log_event("info", "consultation", f"Session complete, project {project_id} created", project_id=project_id)
    return JSONResponse({
        "session_id": session.id,
        "project_id": project_id,
        "status": "complete",
    })


routes = [
    Route("/api/consult/start", start, methods=["POST"]),
    Route("/api/consult/{session_id}/stream", stream_message, methods=["POST"]),
    Route("/api/consult/{session_id}/message", send_message, methods=["POST"]),
    Route("/api/consult/{session_id}", get_session, methods=["GET"]),
    Route("/api/consult/{session_id}/complete", complete_session, methods=["POST"]),
]
