"""CORS для локального www → OrderFlow API."""
from __future__ import annotations

from aiohttp import web

import config

_BASE_HEADERS = {
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Headers": "Authorization, Content-Type",
    "Access-Control-Max-Age": "86400",
}


def _cors_headers(origin: str) -> dict[str, str]:
    headers = dict(_BASE_HEADERS)
    if origin in config.CORS_ORIGINS:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Vary"] = "Origin"
    return headers


@web.middleware
async def cors_middleware(request: web.Request, handler):
    if not config.CORS_ENABLED:
        return await handler(request)

    origin = request.headers.get("Origin", "")
    headers = _cors_headers(origin)

    if request.method == "OPTIONS":
        if not headers.get("Access-Control-Allow-Origin"):
            return web.Response(status=403)
        return web.Response(status=204, headers=headers)

    resp = await handler(request)
    for k, v in headers.items():
        resp.headers[k] = v
    return resp
