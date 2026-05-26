"""24h quote volume (USDT) с Binance USD-M — сортировка списка монет."""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Dict, List

import aiohttp

from src.symbols.instruments import usdt_instrument

logger = logging.getLogger(__name__)

_CACHE: Dict[str, float] = {}
_CACHE_TS: float = 0.0
_TTL_SEC = 900.0
_LOCK = asyncio.Lock()


async def fetch_volume_usd(symbols: List[str]) -> Dict[str, float]:
    want = [s.upper() for s in symbols]
    # Binance ticker: PEPE → 1000PEPEUSDT
    inst_to_coin = {usdt_instrument("binance", s): s for s in want}
    out: Dict[str, float] = {s: 0.0 for s in want}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://fapi.binance.com/fapi/v1/ticker/24hr",
                timeout=aiohttp.ClientTimeout(total=20),
            ) as r:
                if r.status != 200:
                    return out
                rows = await r.json()
        for row in rows:
            sym = str(row.get("symbol", ""))
            coin = inst_to_coin.get(sym)
            if not coin:
                continue
            try:
                out[coin] = float(row.get("quoteVolume") or 0.0)
            except (TypeError, ValueError):
                out[coin] = 0.0
    except Exception as e:
        logger.warning("[volume_rank] fetch failed: %s", e)
    return out


async def get_volumes(symbols: List[str], *, force: bool = False) -> Dict[str, float]:
    global _CACHE_TS
    now = time.time()
    async with _LOCK:
        if not force and _CACHE and (now - _CACHE_TS) < _TTL_SEC:
            return {s: _CACHE.get(s, 0.0) for s in symbols}
        fresh = await fetch_volume_usd(symbols)
        _CACHE.clear()
        _CACHE.update(fresh)
        _CACHE_TS = now
        return {s: _CACHE.get(s, 0.0) for s in symbols}


def sort_symbols(symbols: List[str], volume_usd: Dict[str, float], mode: str) -> List[str]:
    syms = [s.upper() for s in symbols]
    if mode == "volume":
        return sorted(syms, key=lambda s: (-volume_usd.get(s, 0.0), s))
    return sorted(syms)
