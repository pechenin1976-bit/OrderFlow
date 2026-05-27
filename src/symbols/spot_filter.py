"""Какие монеты из списка реально торгуются на spot Bybit / OKX."""
from __future__ import annotations

import logging
from typing import FrozenSet, List, Set

import aiohttp

from src.symbols.instruments import okx_spot_inst_id, usdt_instrument

logger = logging.getLogger(__name__)

_BYBIT_SPOT_INFO = "https://api.bybit.com/v5/market/instruments-info"
_OKX_SPOT_INFO = "https://www.okx.com/api/v5/public/instruments"

_cache: dict[str, FrozenSet[str]] = {}


async def _fetch_set(url: str, params: dict, pick) -> Set[str]:
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=20)) as r:
            data = await r.json()
    return pick(data)


async def bybit_spot_listed(symbols: List[str]) -> FrozenSet[str]:
    key = "bybit_spot"
    if key in _cache:
        listed = _cache[key]
    else:
        raw = await _fetch_set(
            _BYBIT_SPOT_INFO,
            {"category": "spot", "limit": "1000"},
            lambda d: {
                row["symbol"].upper()
                for row in (d.get("result") or {}).get("list") or []
                if row.get("status") == "Trading"
            }
            if d.get("retCode") == 0
            else set(),
        )
        listed = frozenset(raw)
        _cache[key] = listed
        logger.info("[bybit_spot] %s spot USDT instruments cached", len(listed))

    out = {
        s.upper()
        for s in symbols
        if usdt_instrument("bybit_spot", s).upper() in listed
    }
    skip = {s.upper() for s in symbols} - out
    if skip:
        logger.warning("[bybit_spot] skip (no spot): %s", sorted(skip))
    return frozenset(out)


async def okx_spot_listed(symbols: List[str]) -> FrozenSet[str]:
    key = "okx_spot"
    if key in _cache:
        listed = _cache[key]
    else:
        raw = await _fetch_set(
            _OKX_SPOT_INFO,
            {"instType": "SPOT"},
            lambda d: {
                row["instId"].upper()
                for row in d.get("data") or []
                if row.get("state") == "live"
            }
            if d.get("code") == "0"
            else set(),
        )
        listed = frozenset(raw)
        _cache[key] = listed
        logger.info("[okx_spot] %s spot instruments cached", len(listed))

    out = {
        s.upper()
        for s in symbols
        if okx_spot_inst_id(s).upper() in listed
    }
    skip = {s.upper() for s in symbols} - out
    if skip:
        logger.warning("[okx_spot] skip (no spot): %s", sorted(skip))
    return frozenset(out)
