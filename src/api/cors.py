"""CORS для локального www → OrderFlow API."""
from __future__ import annotations

from aiohttp import web

import config

_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Headers": "Authorization, Content-Type",
    "Access-Control-Max-Age": "86400",
}


@web.middleware
async def cors_middleware(request: web.Request, handler):
    if not config.CORS_ENABLED:
        return await handler(request)
    if request.method == "OPTIONS":
        return web.Response(status=204, headers=_HEADERS)
    resp = await handler(request)
    for k, v in _HEADERS.items():
        resp.headers[k] = v
    return resp
