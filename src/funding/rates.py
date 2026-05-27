"""REST: текущие ставки фандинга для futures-бирж (раз в 60 сек)."""
from __future__ import annotations

import asyncio
import logging
from typing import Dict

import aiohttp

from src.symbols.instruments import native_coin, okx_inst_id, usdt_instrument

logger = logging.getLogger(__name__)

_TIMEOUT = aiohttp.ClientTimeout(total=15)


async def _binance(session: aiohttp.ClientSession, symbols: list[str]) -> Dict[str, float]:
    rev = {usdt_instrument("binance", s): s for s in symbols}
    async with session.get(
        "https://fapi.binance.com/fapi/v1/premiumIndex", timeout=_TIMEOUT
    ) as r:
        if r.status != 200:
            logger.warning("[funding] binance HTTP %s", r.status)
            return {}
        rows = await r.json()
    return {
        rev[row["symbol"]]: float(row["lastFundingRate"])
        for row in rows
        if row.get("symbol") in rev and row.get("lastFundingRate") not in (None, "")
    }


async def _bybit(session: aiohttp.ClientSession, symbols: list[str]) -> Dict[str, float]:
    rev = {usdt_instrument("bybit", s): s for s in symbols}
    async with session.get(
        "https://api.bybit.com/v5/market/tickers",
        params={"category": "linear"},
        timeout=_TIMEOUT,
    ) as r:
        data = await r.json()
    rows = (data.get("result") or {}).get("list") or []
    return {
        rev[row["symbol"]]: float(row["fundingRate"])
        for row in rows
        if row.get("symbol") in rev and row.get("fundingRate") not in (None, "")
    }


async def _okx(session: aiohttp.ClientSession, symbols: list[str]) -> Dict[str, float]:
    # /api/v5/market/tickers does not include fundingRate — use dedicated endpoint per symbol
    sem = asyncio.Semaphore(8)

    async def _one(sym: str) -> tuple[str, float | None]:
        async with sem:
            try:
                async with session.get(
                    "https://www.okx.com/api/v5/public/funding-rate",
                    params={"instId": okx_inst_id(sym)},
                    timeout=_TIMEOUT,
                ) as r:
                    data = await r.json()
                items = data.get("data") or []
                if items and items[0].get("fundingRate") not in (None, ""):
                    return sym, float(items[0]["fundingRate"])
            except Exception as e:
                logger.debug("[funding] okx %s: %s", sym, e)
        return sym, None

    pairs = await asyncio.gather(*[_one(s) for s in symbols])
    return {sym: rate for sym, rate in pairs if rate is not None}


async def _hyperliquid(session: aiohttp.ClientSession, symbols: list[str]) -> Dict[str, float]:
    want = {native_coin("hyperliquid", s): s for s in symbols}
    async with session.post(
        "https://api.hyperliquid.xyz/info",
        json={"type": "metaAndAssetCtxs"},
        timeout=_TIMEOUT,
    ) as r:
        if r.status != 200:
            logger.warning("[funding] hyperliquid HTTP %s", r.status)
            return {}
        data = await r.json()
    if not isinstance(data, list) or len(data) < 2:
        return {}
    universe = data[0].get("universe") or []
    ctxs = data[1]
    out: Dict[str, float] = {}
    for asset, ctx in zip(universe, ctxs):
        sym = want.get(asset.get("name"))
        if sym and ctx.get("funding") is not None:
            # HL funding — hourly rate; convert to 8h to match Binance/Bybit/OKX convention
            out[sym] = float(ctx["funding"]) * 8
    return out


_FETCHERS = {
    "binance": _binance,
    "bybit": _bybit,
    "okx": _okx,
    "hyperliquid": _hyperliquid,
}


async def fetch_all_funding(symbols: list[str]) -> Dict[str, Dict[str, float]]:
    """Parallel fetch; returns {exchange_id: {symbol: rate_8h_decimal}}."""
    async with aiohttp.ClientSession() as session:
        tasks = {ex: fn(session, symbols) for ex, fn in _FETCHERS.items()}
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    out: Dict[str, Dict[str, float]] = {}
    for ex, res in zip(tasks.keys(), results):
        if isinstance(res, Exception):
            logger.warning("[funding] %s: %s", ex, res)
            out[ex] = {}
        else:
            out[ex] = res
    return out
