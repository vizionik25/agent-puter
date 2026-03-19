"""
api/payments.py — Stripe payment routes.

POST /api/payments/deposit          — create 20% deposit PaymentIntent
POST /api/payments/final            — create 80% final PaymentIntent
POST /api/payments/webhook          — Stripe webhook (payment_intent.succeeded)
GET  /api/payments/{project_id}/status — deposit_paid + final_paid flags
"""
from __future__ import annotations

import os
import json
from datetime import datetime

import stripe
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from . import _store

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")


async def create_deposit(request: Request) -> JSONResponse:
    """Create a Stripe PaymentIntent for the 20% deposit."""
    if not stripe.api_key:
        return JSONResponse({"error": "Stripe not configured"}, status_code=503)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

    project_id = body.get("project_id", "").strip()
    project = _store.projects.get(project_id)
    if not project:
        return JSONResponse({"error": "Project not found"}, status_code=404)

    if project.deposit_paid:
        return JSONResponse({"error": "Deposit already paid"}, status_code=400)

    if not project.proposal:
        return JSONResponse({"error": "No proposal available yet"}, status_code=404)

    amount_cents = int(project.proposal.deposit_amount_usd * 100)
    if amount_cents < 50:
        return JSONResponse({"error": "Amount too small"}, status_code=400)

    intent = stripe.PaymentIntent.create(
        amount=amount_cents,
        currency="usd",
        metadata={
            "project_id": project_id,
            "payment_type": "deposit",
            "client_email": project.client_id,
        },
        description=f"20% deposit — {project.name}",
    )

    project.stripe_deposit_intent_id = intent.id
    project.updated_at = datetime.utcnow()
    _store.projects[project_id] = project

    return JSONResponse({
        "client_secret": intent.client_secret,
        "amount_usd": project.proposal.deposit_amount_usd,
        "project_id": project_id,
    })


async def create_final(request: Request) -> JSONResponse:
    """Create a Stripe PaymentIntent for the 80% final balance."""
    if not stripe.api_key:
        return JSONResponse({"error": "Stripe not configured"}, status_code=503)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

    project_id = body.get("project_id", "").strip()
    project = _store.projects.get(project_id)
    if not project:
        return JSONResponse({"error": "Project not found"}, status_code=404)

    if not project.deposit_paid:
        return JSONResponse(
            {"error": "Deposit must be paid before final payment"},
            status_code=400,
        )

    if project.final_paid:
        return JSONResponse({"error": "Final payment already made"}, status_code=400)

    if not project.proposal:
        return JSONResponse({"error": "No proposal available yet"}, status_code=404)

    amount_cents = int(project.proposal.final_amount_usd * 100)

    intent = stripe.PaymentIntent.create(
        amount=amount_cents,
        currency="usd",
        metadata={
            "project_id": project_id,
            "payment_type": "final",
            "client_email": project.client_id,
        },
        description=f"80% final balance — {project.name}",
    )

    project.stripe_final_intent_id = intent.id
    project.updated_at = datetime.utcnow()
    _store.projects[project_id] = project

    return JSONResponse({
        "client_secret": intent.client_secret,
        "amount_usd": project.proposal.final_amount_usd,
        "project_id": project_id,
    })


async def webhook(request: Request) -> JSONResponse:
    """
    Handle Stripe webhook events.
    Listens for payment_intent.succeeded and updates the project's payment flags.
    """
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    if webhook_secret:
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        except stripe.error.SignatureVerificationError:
            return JSONResponse({"error": "Invalid signature"}, status_code=400)
    else:
        # Dev mode: trust the payload without signature verification
        try:
            event = json.loads(payload)
        except Exception:
            return JSONResponse({"error": "Invalid payload"}, status_code=400)

    event_type = event.get("type") if isinstance(event, dict) else event.type
    data_obj = (
        event["data"]["object"]
        if isinstance(event, dict)
        else event.data.object
    )

    if event_type == "payment_intent.succeeded":
        intent_id = data_obj.get("id") if isinstance(data_obj, dict) else data_obj.id
        metadata = (
            data_obj.get("metadata", {})
            if isinstance(data_obj, dict)
            else data_obj.metadata
        )
        project_id = metadata.get("project_id")
        payment_type = metadata.get("payment_type")

        if project_id and project_id in _store.projects:
            project = _store.projects[project_id]
            if payment_type == "deposit":
                project.deposit_paid = True
            elif payment_type == "final":
                project.final_paid = True
            project.updated_at = datetime.utcnow()
            _store.projects[project_id] = project

    return JSONResponse({"received": True})


async def payment_status(request: Request) -> JSONResponse:
    """Return the current payment status for a project."""
    project_id = request.path_params["project_id"]
    project = _store.projects.get(project_id)
    if not project:
        return JSONResponse({"error": "Project not found"}, status_code=404)

    return JSONResponse({
        "project_id": project_id,
        "deposit_paid": project.deposit_paid,
        "final_paid": project.final_paid,
        "total_price_usd": project.total_price_usd,
        "deposit_amount_usd": project.proposal.deposit_amount_usd if project.proposal else 0,
        "final_amount_usd": project.proposal.final_amount_usd if project.proposal else 0,
    })


routes = [
    Route("/api/payments/deposit", create_deposit, methods=["POST"]),
    Route("/api/payments/final", create_final, methods=["POST"]),
    Route("/api/payments/webhook", webhook, methods=["POST"]),
    Route("/api/payments/{project_id}/status", payment_status, methods=["GET"]),
]
