"""
api/auth.py — GitHub OAuth 2.0 authentication.

Routes:
  GET  /api/auth/github    → redirect to GitHub OAuth consent screen
  GET  /api/auth/callback  → exchange code, set session cookie, redirect to /dashboard
  GET  /api/auth/me        → return current user from session cookie (401 if unauthenticated)
  POST /api/auth/logout    → clear session cookie

Session tokens are HMAC-SHA256 signed JSON payloads (no extra dependencies).
Set SESSION_SECRET to a strong random value in production.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from datetime import datetime
from typing import Optional
from urllib.parse import urlencode

import httpx
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse
from starlette.routing import Route

from . import _store
from ..models import User


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def _client_id() -> str:
    return os.getenv("GITHUB_CLIENT_ID", "")

def _client_secret() -> str:
    return os.getenv("GITHUB_CLIENT_SECRET", "")

def _frontend_url() -> str:
    return os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")

def _session_secret() -> str:
    return os.getenv("SESSION_SECRET", "dev-secret-change-in-production")


_COOKIE_SESSION = "ap_session"
_COOKIE_STATE = "ap_oauth_state"
_SESSION_TTL = 30 * 86400  # 30 days
_STATE_TTL = 300            # 5 minutes


# ---------------------------------------------------------------------------
# HMAC-signed session token (no extra deps)
# ---------------------------------------------------------------------------

def _sign(data: str) -> str:
    """Return the HMAC-SHA256 hex digest of *data* using the session secret."""
    return hmac.new(_session_secret().encode(), data.encode(), hashlib.sha256).hexdigest()


def make_session_token(github_id: str, ttl: int = _SESSION_TTL) -> str:
    """Create a signed session token for a GitHub user.

    Args:
        github_id (str): The GitHub user ID to embed as the subject claim.
        ttl (int): Lifetime of the token in seconds. Defaults to 30 days.

    Returns:
        str: A URL-safe base64-encoded payload with an HMAC-SHA256 signature
            appended after a ``'.'`` separator.
    """
    payload = json.dumps({"sub": github_id, "exp": int(time.time()) + ttl})
    data = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")
    return f"{data}.{_sign(data)}"


def verify_session_token(token: str) -> Optional[str]:
    """Verify a signed session token and return the embedded GitHub user ID.

    Args:
        token (str): A token previously produced by :func:`make_session_token`.

    Returns:
        Optional[str]: The GitHub user ID (``sub`` claim) when the signature is
            valid and the token has not expired; ``None`` otherwise.
    """
    try:
        data, sig = token.rsplit(".", 1)
        if not hmac.compare_digest(_sign(data), sig):
            return None
        padding = "=" * (-len(data) % 4)
        payload = json.loads(base64.urlsafe_b64decode(data + padding))
        if payload.get("exp", 0) < time.time():
            return None
        return str(payload["sub"])
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Current-user helper (imported by other route modules)
# ---------------------------------------------------------------------------

async def get_current_user(request: Request) -> Optional[User]:
    """Retrieve the authenticated user from the session cookie.

    Args:
        request (Request): The incoming Starlette request containing cookies.

    Returns:
        Optional[User]: The ``User`` object for the authenticated session, or
            ``None`` if the cookie is absent, invalid, or expired.
    """
    token = request.cookies.get(_COOKIE_SESSION)
    if not token:
        return None
    github_id = verify_session_token(token)
    if not github_id:
        return None
    return await _store.store.get_user(github_id)


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------

async def github_login(request: Request) -> RedirectResponse:
    """Redirect the browser to GitHub's OAuth consent screen.

    Args:
        request (Request): The incoming Starlette request (unused beyond
            triggering the handler; included for ASGI compatibility).

    Returns:
        RedirectResponse: A 302 redirect to GitHub's OAuth authorization URL
            with a CSRF state token set as an HTTP-only cookie, or a 503
            ``JSONResponse`` when ``GITHUB_CLIENT_ID`` is not configured.
    """
    if not _client_id():
        return JSONResponse(
            {"error": "GITHUB_CLIENT_ID is not configured on the server"},
            status_code=503,
        )
    state = secrets.token_urlsafe(16)
    params = urlencode({
        "client_id": _client_id(),
        "redirect_uri": f"{_frontend_url()}/api/auth/callback",
        "scope": "repo user:email",
        "state": state,
    })
    response = RedirectResponse(
        f"https://github.com/login/oauth/authorize?{params}",
        status_code=302,
    )
    response.set_cookie(
        _COOKIE_STATE, state,
        httponly=True, samesite="lax", max_age=_STATE_TTL, path="/",
    )
    return response


async def github_callback(request: Request) -> RedirectResponse:
    """Handle the GitHub OAuth callback: exchange code, upsert user, set session cookie.

    Args:
        request (Request): The incoming Starlette request carrying the ``code``
            and ``state`` query parameters set by GitHub.

    Returns:
        RedirectResponse: A 302 redirect to ``/dashboard`` on success, with the
            session cookie set. On any failure (missing code, state mismatch,
            token exchange error, or GitHub API error) redirects to
            ``{FRONTEND_URL}/?auth_error=<reason>`` instead.
    """
    code = request.query_params.get("code", "")
    state = request.query_params.get("state", "")
    stored_state = request.cookies.get(_COOKIE_STATE, "")

    if not code:
        return RedirectResponse(f"{_frontend_url()}/?auth_error=missing_code", status_code=302)
    if not state or state != stored_state:
        return RedirectResponse(f"{_frontend_url()}/?auth_error=state_mismatch", status_code=302)

    # Exchange code for access token
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": _client_id(),
                "client_secret": _client_secret(),
                "code": code,
                "redirect_uri": f"{_frontend_url()}/api/auth/callback",
            },
            headers={"Accept": "application/json"},
            timeout=15,
        )
    if token_resp.status_code != 200:
        return RedirectResponse(f"{_frontend_url()}/?auth_error=token_exchange_failed", status_code=302)

    token_data = token_resp.json()
    access_token = token_data.get("access_token", "")
    if not access_token:
        return RedirectResponse(f"{_frontend_url()}/?auth_error=no_access_token", status_code=302)

    gh_headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    # Fetch GitHub user profile
    async with httpx.AsyncClient() as client:
        user_resp = await client.get(
            "https://api.github.com/user",
            headers=gh_headers,
            timeout=10,
        )
    if user_resp.status_code != 200:
        return RedirectResponse(f"{_frontend_url()}/?auth_error=github_api_failed", status_code=302)

    gh = user_resp.json()
    github_id = str(gh["id"])
    email: str = gh.get("email") or ""

    # Fetch primary verified email if not public
    if not email:
        async with httpx.AsyncClient() as client:
            emails_resp = await client.get(
                "https://api.github.com/user/emails",
                headers=gh_headers,
                timeout=10,
            )
        if emails_resp.status_code == 200:
            for entry in emails_resp.json():
                if entry.get("primary") and entry.get("verified"):
                    email = entry["email"]
                    break

    # Upsert user record (preserve tier/credits on re-login)
    existing = await _store.store.get_user(github_id)
    user = User(
        github_id=github_id,
        login=gh.get("login", ""),
        name=gh.get("name") or gh.get("login", ""),
        email=email,
        avatar_url=gh.get("avatar_url", ""),
        access_token=access_token,
        tier=existing.tier if existing else "free",
        credits=existing.credits if existing else 0.0,
        created_at=existing.created_at if existing else datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    await _store.store.set_user(user)

    # Set session cookie and redirect to dashboard
    session_token = make_session_token(github_id)
    response = RedirectResponse("/dashboard", status_code=302)
    response.delete_cookie(_COOKIE_STATE, path="/")
    response.set_cookie(
        _COOKIE_SESSION, session_token,
        httponly=True, samesite="lax",
        max_age=_SESSION_TTL, path="/",
    )
    return response


async def me(request: Request) -> JSONResponse:
    """Return the currently authenticated user, or 401.

    Args:
        request (Request): The incoming Starlette request; the session cookie
            is read to identify the user.

    Returns:
        JSONResponse: A 200 response containing the user's ``github_id``,
            ``login``, ``name``, ``email``, ``avatar_url``, ``tier``, and
            ``credits`` fields, or a 401 response when no valid session exists.
    """
    user = await get_current_user(request)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    return JSONResponse({
        "github_id": user.github_id,
        "login": user.login,
        "name": user.name,
        "email": user.email,
        "avatar_url": user.avatar_url,
        "tier": user.tier,
        "credits": user.credits,
    })


async def logout(request: Request) -> JSONResponse:
    """Clear the session cookie and log the current user out.

    Args:
        request (Request): The incoming Starlette request (cookie deletion is
            applied to the response, not the request).

    Returns:
        JSONResponse: A 200 response with ``{"status": "logged_out"}`` and the
            session cookie cleared.
    """
    response = JSONResponse({"status": "logged_out"})
    response.delete_cookie(_COOKIE_SESSION, path="/")
    return response


routes = [
    Route("/api/auth/github", github_login, methods=["GET"]),
    Route("/api/auth/callback", github_callback, methods=["GET"]),
    Route("/api/auth/me", me, methods=["GET"]),
    Route("/api/auth/logout", logout, methods=["POST"]),
]
