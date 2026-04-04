"""
middleware.py — Multi-tenancy support via API key resolution.

Agency operators can assign API keys to tenant namespaces using:
    AGENCY_API_KEYS=key1:tenant1,key2:tenant2

Requests that send X-Agency-Key: key1 are routed to the "tenant1" namespace.
Requests without a key (or with an unrecognised key) land in "default".

Usage in route handlers:
    from ..middleware import resolve_tenant
    owner_id = resolve_tenant(request)
"""
from __future__ import annotations

import os
from functools import lru_cache

from starlette.requests import Request


@lru_cache(maxsize=1)
def _load_key_map() -> dict[str, str]:
    """
    Parse AGENCY_API_KEYS env var into {api_key: tenant_id} dict.

    Format: AGENCY_API_KEYS=key1:tenant1,key2:tenant2
    """
    raw = os.getenv("AGENCY_API_KEYS", "")
    mapping: dict[str, str] = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if ":" in pair:
            key, tenant = pair.split(":", 1)
            key = key.strip()
            tenant = tenant.strip()
            if key and tenant:
                mapping[key] = tenant
    return mapping


def resolve_tenant(request: Request) -> str:
    """
    Extract tenant owner_id from the request.

    Checks (in order):
      1. X-Agency-Key header
      2. Authorization: Bearer <key> header

    Returns the mapped tenant_id, or "default" if no valid key is found.
    """
    key_map = _load_key_map()
    if not key_map:
        return "default"

    # Check X-Agency-Key first
    key = request.headers.get("X-Agency-Key", "").strip()
    if not key:
        # Fallback: Authorization: Bearer <key>
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            key = auth[7:].strip()

    return key_map.get(key, "default")
