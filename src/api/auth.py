"""Bearer license key / dev API_KEYS + rate-limit."""

from __future__ import annotations



import time

from collections import defaultdict

from typing import Optional



from aiohttp import web



import config

from src.api.license_client import validate_license_key



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





async def _is_authorized(token: str) -> bool:

    if token in config.API_KEYS:

        return True

    return await validate_license_key(token)





@web.middleware

async def auth_middleware(request: web.Request, handler):

    if request.method == "OPTIONS":
        return await handler(request)

    if request.path in ("/api/v1/health", "/health"):

        return await handler(request)

    token = extract_token(request)

    if not token:

        return web.json_response({"error": "unauthorized"}, status=401)

    if not await _is_authorized(token):

        return web.json_response({"error": "unauthorized"}, status=401)

    if not _check_rate(token):

        return web.json_response({"error": "rate_limit"}, status=429)

    request["api_token"] = token

    return await handler(request)

