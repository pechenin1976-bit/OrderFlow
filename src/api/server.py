"""REST API для quantilan.com (poll snapshot)."""
from __future__ import annotations

import logging

from aiohttp import web

import config
from src.api.auth import auth_middleware
from src.state.market_state import MarketState

logger = logging.getLogger(__name__)


def create_app(state: MarketState) -> web.Application:
    app = web.Application(middlewares=[auth_middleware])

    async def health(_request: web.Request) -> web.Response:
        return web.json_response({"status": "ok", "service": "orderflow"})

    async def symbols(_request: web.Request) -> web.Response:
        return web.json_response({"symbols": state.symbols, "tf": list(config.TF_SECONDS.keys())})

    async def snapshot(request: web.Request) -> web.Response:
        sym = (request.query.get("symbol") or config.DEFAULT_SYMBOLS[0]).upper()
        tf = request.query.get("tf") or config.DEFAULT_TF
        if tf not in config.TF_SECONDS:
            return web.json_response({"error": "invalid tf"}, status=400)
        if sym not in state.symbols:
            return web.json_response({"error": "invalid symbol"}, status=400)

        cached = await state.get_cached(sym)
        if cached and cached.get("tf") == tf:
            return web.json_response(cached)
        snap = await state.build_snapshot(sym, tf, config.DEFAULT_BARS_COUNT)
        return web.json_response(snap)

    app.router.add_get("/health", health)
    app.router.add_get("/api/v1/health", health)
    app.router.add_get("/api/v1/symbols", symbols)
    app.router.add_get("/api/v1/snapshot", snapshot)
    return app


async def start_api(state: MarketState) -> web.AppRunner:
    app = create_app(state)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, config.API_HOST, config.API_PORT)
    await site.start()
    logger.info("API http://%s:%s", config.API_HOST, config.API_PORT)
    return runner
