"""
main.py — Swarm ASGI Entry Point

One server, all agents + client-facing REST API.

Endpoints:
  GET  /health                      → health / agent listing
  GET  /.well-known/agent-card.json → CEO agent card
  GET  /docs                        → CEO fasta2a docs UI
  POST /run                         → CEO A2A run endpoint
  GET|POST /sales/*  /pm/*  ...     → per-agent sub-apps
  POST /api/consult/*               → consultation session routes
  GET|POST /api/projects/*          → project / proposal / demo routes
  POST /api/payments/*              → Stripe payment routes

Run:
  uv run agent-puter
  uvicorn agent_puter.swarm.main:app --host 0.0.0.0 --port 9999
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Mount, Route
from starlette.responses import JSONResponse
from starlette.requests import Request

from .ceo_agent import ceo_agent, ceo_app as _ceo_app
from .sales_agent import sales_agent, sales_app as _sales_app
from .pm_agent import pm_agent, pm_app as _pm_app
from .researcher_agent import researcher_agent, researcher_app as _researcher_app
from .engineer_agent import engineer_agent, engineer_app as _engineer_app
from .qa_agent import qa_agent, qa_app as _qa_app
from .api import routes as api_routes

# All A2A apps are owned by their respective agent modules.
# main.py mounts them — it does NOT call .to_a2a() itself.


@asynccontextmanager
async def _lifespan(app: Starlette) -> AsyncIterator[None]:
    """Initialize every fasta2a TaskManager before serving requests."""
    async with _ceo_app.task_manager:
        async with _sales_app.task_manager:
            async with _pm_app.task_manager:
                async with _researcher_app.task_manager:
                    async with _engineer_app.task_manager:
                        async with _qa_app.task_manager:
                            yield


# ---------------------------------------------------------------------------
# Root-level handlers delegate to the CEO agent.
# ---------------------------------------------------------------------------

async def _root_agent_card(request: Request):
    return await _ceo_app._agent_card_endpoint(request)

async def _root_docs(request: Request):
    return await _ceo_app._docs_endpoint(request)

async def _root_run(request: Request):
    return await _ceo_app._agent_run_endpoint(request)

async def health(request: Request) -> JSONResponse:
    return JSONResponse({
        "status": "ok",
        "swarm": {
            "root": {
                "agent": "CEO",
                "docs": "http://localhost:9999/docs",
                "agent_card": "http://localhost:9999/.well-known/agent-card.json",
            },
            "agents": [
                {"role": "ceo",        "docs": "/docs",            "a2a": "/"},
                {"role": "sales",      "docs": "/sales/docs",      "a2a": "/sales/"},
                {"role": "pm",         "docs": "/pm/docs",         "a2a": "/pm/"},
                {"role": "researcher", "docs": "/researcher/docs", "a2a": "/researcher/"},
                {"role": "engineer",   "docs": "/engineer/docs",   "a2a": "/engineer/"},
                {"role": "qa",         "docs": "/qa/docs",         "a2a": "/qa/"},
            ],
        },
        "api": {
            "consult": "/api/consult/start",
            "projects": "/api/projects/{id}",
            "payments": "/api/payments/deposit",
        },
    })


app = Starlette(
    lifespan=_lifespan,
    middleware=[
        Middleware(
            CORSMiddleware,
            allow_origins=[
                "http://localhost:3000",   # Next.js dev
                "http://localhost:9999",   # same-origin
            ],
            allow_methods=["*"],
            allow_headers=["*"],
        ),
    ],
    routes=[
        # ── Client REST API ──────────────────────────────────────────────
        *api_routes,

        # ── Root (CEO) endpoints — browser-compatible docs ──────────────
        Route("/",                             health,           methods=["GET"]),
        Route("/health",                       health,           methods=["GET"]),
        Route("/.well-known/agent-card.json", _root_agent_card, methods=["GET", "HEAD", "OPTIONS"]),
        Route("/docs",                         _root_docs,       methods=["GET"]),
        Route("/run",                          _root_run,        methods=["POST"]),

        # ── Per-agent sub-apps (A2A protocol + per-agent docs) ───────────
        Mount("/ceo",        app=_ceo_app),
        Mount("/sales",      app=_sales_app),
        Mount("/pm",         app=_pm_app),
        Mount("/researcher", app=_researcher_app),
        Mount("/engineer",   app=_engineer_app),
        Mount("/qa",         app=_qa_app),
    ],
)
