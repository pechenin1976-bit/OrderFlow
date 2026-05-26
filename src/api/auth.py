"""Bearer token auth + простой rate-limit."""
from __future__ import annotations

import time
from collections import defaultdict
from typing import Optional

from aiohttp import web

import config

_rate: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT_PER_MIN = 30


def _check_rate(token: str) -> bool:
    now = time.time()
    window = [t for t in _rate[token] if now - t < 60]
    if len(window) >= RATE_LIMIT_PER_MIN:
        return False
    window.append(now)
    _rate[token] = window
    return True


def extract_token(request: web.Request) -> Optional[str]:
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return request.query.get("token") or None


@web.middleware
async def auth_middleware(request: web.Request, handler):
    if request.path in ("/api/v1/health", "/health"):
        return await handler(request)
    token = extract_token(request)
    if not token or token not in config.API_KEYS:
        return web.json_response({"error": "unauthorized"}, status=401)
    if not _check_rate(token):
        return web.json_response({"error": "rate_limit"}, status=429)
    request["api_token"] = token
    return await handler(request)
