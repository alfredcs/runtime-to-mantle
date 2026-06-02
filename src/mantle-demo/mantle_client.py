"""
The bedrock-mantle client.

Two responsibilities:
  1. build_request()  -- construct the EXACT HTTP wire object (method, URL,
     headers, JSON body, equivalent curl) for any of the three surfaces. This
     is shown verbatim in the UI's Wire Inspector, so it must be faithful to
     the real API, including the per-surface auth-header difference.
  2. call_live()      -- actually send that request to the real endpoint when
     LIVE mode is enabled and a Bearer token is obtainable.

LIVE mode is optional; the default DEMO mode never calls this network path.
"""
from __future__ import annotations

import json
import os

import httpx

from config import SURFACES, host_for


def _token() -> str | None:
    """Obtain a Bedrock Bearer token for LIVE mode, best effort."""
    for var in ("AWS_BEARER_TOKEN_BEDROCK", "MANTLE_API_KEY", "OPENAI_API_KEY"):
        if os.environ.get(var):
            return os.environ[var]
    try:  # short-term token inheriting the caller's IAM session
        from aws_bedrock_token_generator import provide_token  # type: ignore
        return provide_token()
    except Exception:
        return None


def _mask(token: str | None) -> str:
    if not token:
        return "DEMO-no-credentials"
    return token[:6] + "…" + token[-4:] if len(token) > 12 else "••••"


def _base_url(surface_key: str, region: str) -> str:
    """Origin (scheme + host) for a surface. The Responses surface can be pinned
    to an explicit endpoint via BEDROCK_MANTLE_URL; a trailing /v1 (the common
    OpenAI base_url form) is trimmed so the surface path appends cleanly."""
    if surface_key == "responses":
        override = os.environ.get("BEDROCK_MANTLE_URL")
        if override:
            base = override.rstrip("/")
            if base.endswith("/v1"):
                base = base[:-3]
            return base
    return f"https://{host_for(region)}"


def build_request(surface_key: str, region: str, model: str, body: dict,
                  *, token: str | None = None, live: bool = False) -> dict:
    """Return the wire representation of a Mantle call (token always masked)."""
    surface = SURFACES[surface_key]
    url = f"{_base_url(surface_key, region)}{surface['path']}"
    headers = {"Content-Type": "application/json"}

    if surface_key == "messages":
        headers["x-api-key"] = _mask(token)
        headers["anthropic-version"] = "2023-06-01"
    else:  # OpenAI-style surfaces use a Bearer token
        headers["Authorization"] = f"Bearer {_mask(token)}"

    curl = _as_curl(url, headers, body)
    return {"method": "POST", "url": url, "path": surface["path"],
            "headers": headers, "body": body, "curl": curl,
            "auth_style": surface["auth_header"], "live": live}


def _as_curl(url: str, headers: dict, body: dict) -> str:
    parts = [f"curl -X POST {url}"]
    for k, v in headers.items():
        parts.append(f'  -H "{k}: {v}"')
    parts.append("  -d '" + json.dumps(body, indent=2) + "'")
    return " \\\n".join(parts)


async def call_live(surface_key: str, region: str, body: dict) -> dict:
    """Send a real request to bedrock-mantle. Raises on missing token/HTTP error."""
    token = _token()
    if not token:
        raise RuntimeError("No Bedrock Bearer token available for LIVE mode "
                           "(set AWS_BEARER_TOKEN_BEDROCK or install aws-bedrock-token-generator).")
    surface = SURFACES[surface_key]
    url = f"{_base_url(surface_key, region)}{surface['path']}"
    headers = {"Content-Type": "application/json"}
    if surface_key == "messages":
        headers["x-api-key"] = token
        headers["anthropic-version"] = "2023-06-01"
    else:
        headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(url, headers=headers, json=body)
        resp.raise_for_status()
        return resp.json()


def live_token_available() -> bool:
    return _token() is not None
