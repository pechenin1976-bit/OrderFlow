"""REST API для quantilan.com (poll snapshot)."""
from __future__ import annotations

import logging

from aiohttp import web

import config
from src.api.auth import auth_middleware
from src.api.cors import cors_middleware
from src.state.market_state import MarketState, resolve_symbol

logger = logging.getLogger(__name__)


def create_app(state: MarketState) -> web.Application:
    app = web.Application(middlewares=[cors_middleware, auth_middleware])

    async def health(_request: web.Request) -> web.Response:
        return web.json_response({"status": "ok", "service": "orderflow"})

    async def symbols(request: web.Request) -> web.Response:
        from src.symbols.volume_rank import get_volumes, sort_symbols

        sort_mode = (request.query.get("sort") or "alpha").lower()
        if sort_mode not in ("alpha", "volume"):
            sort_mode = "alpha"
        vol = await get_volumes(state.symbols)
        ordered = sort_symbols(state.symbols, vol, sort_mode)
        return web.json_response({
            "symbols": ordered,
            "volume_usd": {s: vol.get(s, 0.0) for s in state.symbols},
            "sort": sort_mode,
            "tf": list(config.TF_SECONDS.keys()),
            "profile_range_pct": list(config.PROFILE_RANGE_CHOICES),
        })

    async def snapshot(request: web.Request) -> web.Response:
        raw_sym = (request.query.get("symbol") or config.DEFAULT_SYMBOLS[0]).upper()
        sym = resolve_symbol(raw_sym)
        tf = request.query.get("tf") or config.DEFAULT_TF
        range_pct = request.query.get("range") or request.query.get("profile_range_pct")
        if tf not in config.TF_SECONDS:
            return web.json_response({"error": "invalid tf"}, status=400)
        if sym not in state.symbols:
            return web.json_response({"error": "invalid symbol"}, status=400)

        from src.state.market_state import _normalize_profile_range

        range_norm = _normalize_profile_range(range_pct)
        refresh = request.query.get("refresh", "").lower() in ("1", "true", "yes")
        if refresh:
            token = request.get("api_token", "")
            from src.api.auth import _check_rate
            if not _check_rate(f"refresh:{token or 'anon'}"):
                return web.json_response({"error": "rate_limit"}, status=429)

        state.touch_interest(sym, tf, range_norm)

        if not refresh:
            cached = await state.get_cached_json(sym, tf, range_norm)
            if cached is not None:
                return web.Response(
                    body=cached,
                    content_type="application/json",
                    charset="utf-8",
                )

        snap = await state.build_snapshot(
            sym, tf, config.DEFAULT_BARS_COUNT, range_norm, refresh_history=refresh
        )
        body = await state.get_cached_json(sym, tf, range_norm)
        if body is not None:
            return web.Response(
                body=body,
                content_type="application/json",
                charset="utf-8",
            )
        return web.json_response(snap)

    async def funding(_request: web.Request) -> web.Response:
        return web.json_response({
            "rates": state.funding_rates,
            "symbols": state.symbols,
        })

    app.router.add_get("/health", health)
    app.router.add_get("/api/v1/health", health)
    app.router.add_get("/api/v1/symbols", symbols)
    app.router.add_get("/api/v1/snapshot", snapshot)
    app.router.add_get("/api/v1/funding", funding)
    return app


async def start_api(state: MarketState) -> web.AppRunner:
    app = create_app(state)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, config.API_HOST, config.API_PORT)
    await site.start()
    logger.info("API http://%s:%s", config.API_HOST, config.API_PORT)
    return runner
