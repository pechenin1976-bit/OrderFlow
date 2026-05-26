"""REST: последние N свечей для старта дашборда."""
from __future__ import annotations

import logging
import time
from typing import List, Optional

import aiohttp

from src.symbols.instruments import native_coin, okx_inst_id, okx_spot_inst_id, usdt_instrument

logger = logging.getLogger(__name__)

_HL_TF = {
    "5m": "5m",
    "15m": "15m",
    "1h": "1h",
    "4h": "4h",
    "1d": "1d",
    "1w": "1w",
}


def _bar(t_sec: int, o: float, h: float, l: float, c: float, v: float) -> List[float]:
    return [float(t_sec), o, h, l, c, v]


async def fetch_binance(session: aiohttp.ClientSession, symbol: str, tf: str, limit: int) -> List[List[float]]:
    sym = usdt_instrument("binance", symbol)
    url = "https://fapi.binance.com/fapi/v1/klines"
    params = {"symbol": sym, "interval": tf, "limit": limit}
    async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as r:
        if r.status != 200:
            logger.warning("[history] binance %s HTTP %s", sym, r.status)
            return []
        rows = await r.json()
    out: List[List[float]] = []
    for row in rows:
        out.append(_bar(int(row[0]) // 1000, float(row[1]), float(row[2]), float(row[3]), float(row[4]), float(row[5])))
    return out


_BYBIT_TF = {"5m": "5", "15m": "15", "1h": "60", "4h": "240", "1d": "D", "1w": "W"}


async def fetch_bybit(session: aiohttp.ClientSession, symbol: str, tf: str, limit: int) -> List[List[float]]:
    interval = _BYBIT_TF.get(tf)
    if not interval:
        return []
    sym = usdt_instrument("bybit", symbol)
    url = "https://api.bybit.com/v5/market/kline"
    params = {"category": "linear", "symbol": sym, "interval": interval, "limit": limit}
    async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as r:
        data = await r.json()
    rows = (data.get("result") or {}).get("list") or []
    out: List[List[float]] = []
    for row in reversed(rows):
        out.append(_bar(int(row[0]) // 1000, float(row[1]), float(row[2]), float(row[3]), float(row[4]), float(row[5])))
    return out


_OKX_TF = {"5m": "5m", "15m": "15m", "1h": "1H", "4h": "4H", "1d": "1D", "1w": "1W"}


async def fetch_okx(session: aiohttp.ClientSession, symbol: str, tf: str, limit: int) -> List[List[float]]:
    bar = _OKX_TF.get(tf)
    if not bar:
        return []
    inst = okx_inst_id(symbol)
    url = "https://www.okx.com/api/v5/market/candles"
    params = {"instId": inst, "bar": bar, "limit": str(limit)}
    async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as r:
        data = await r.json()
    rows = data.get("data") or []
    out: List[List[float]] = []
    for row in reversed(rows):
        out.append(_bar(int(row[0]) // 1000, float(row[1]), float(row[2]), float(row[3]), float(row[4]), float(row[5])))
    return out


async def fetch_hyperliquid(
    session: aiohttp.ClientSession, symbol: str, tf: str, limit: int
) -> List[List[float]]:
    interval = _HL_TF.get(tf)
    if not interval:
        return []
    coin = native_coin("hyperliquid", symbol)
    tf_sec = {"5m": 300, "15m": 900, "1h": 3600, "4h": 14400, "1d": 86400, "1w": 604800}.get(tf, 900)
    end_ms = int(time.time() * 1000)
    start_ms = end_ms - limit * tf_sec * 1000
    payload = {
        "type": "candleSnapshot",
        "req": {"coin": coin, "interval": interval, "startTime": start_ms, "endTime": end_ms},
    }
    async with session.post(
        "https://api.hyperliquid.xyz/info",
        json=payload,
        timeout=aiohttp.ClientTimeout(total=15),
    ) as r:
        if r.status != 200:
            logger.warning("[history] hyperliquid %s HTTP %s", coin, r.status)
            return []
        rows = await r.json()
    if not isinstance(rows, list):
        return []
    out: List[List[float]] = []
    for c in rows:
        out.append(_bar(int(c["t"]) // 1000, float(c["o"]), float(c["h"]), float(c["l"]), float(c["c"]), float(c["v"])))
    return out[-limit:]


async def fetch_binance_spot(session: aiohttp.ClientSession, symbol: str, tf: str, limit: int) -> List[List[float]]:
    sym = usdt_instrument("binance_spot", symbol)
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": sym, "interval": tf, "limit": limit}
    async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as r:
        if r.status != 200:
            logger.warning("[history] binance_spot %s HTTP %s", sym, r.status)
            return []
        rows = await r.json()
    out: List[List[float]] = []
    for row in rows:
        out.append(_bar(int(row[0]) // 1000, float(row[1]), float(row[2]), float(row[3]), float(row[4]), float(row[5])))
    return out


async def fetch_bybit_spot(session: aiohttp.ClientSession, symbol: str, tf: str, limit: int) -> List[List[float]]:
    interval = _BYBIT_TF.get(tf)
    if not interval:
        return []
    sym = usdt_instrument("bybit_spot", symbol)
    url = "https://api.bybit.com/v5/market/kline"
    params = {"category": "spot", "symbol": sym, "interval": interval, "limit": limit}
    async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as r:
        data = await r.json()
    rows = (data.get("result") or {}).get("list") or []
    out: List[List[float]] = []
    for row in reversed(rows):
        out.append(_bar(int(row[0]) // 1000, float(row[1]), float(row[2]), float(row[3]), float(row[4]), float(row[5])))
    return out


async def fetch_okx_spot(session: aiohttp.ClientSession, symbol: str, tf: str, limit: int) -> List[List[float]]:
    bar = _OKX_TF.get(tf)
    if not bar:
        return []
    inst = okx_spot_inst_id(symbol)
    url = "https://www.okx.com/api/v5/market/candles"
    params = {"instId": inst, "bar": bar, "limit": str(limit)}
    async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as r:
        data = await r.json()
    rows = data.get("data") or []
    out: List[List[float]] = []
    for row in reversed(rows):
        out.append(_bar(int(row[0]) // 1000, float(row[1]), float(row[2]), float(row[3]), float(row[4]), float(row[5])))
    return out


_FETCHERS = {
    "binance": fetch_binance,
    "binance_spot": fetch_binance_spot,
    "bybit": fetch_bybit,
    "bybit_spot": fetch_bybit_spot,
    "okx": fetch_okx,
    "okx_spot": fetch_okx_spot,
    "hyperliquid": fetch_hyperliquid,
}


async def fetch_history(exchange: str, symbol: str, tf: str, limit: int) -> List[List[float]]:
    fn = _FETCHERS.get(exchange)
    if not fn:
        return []
    try:
        async with aiohttp.ClientSession() as session:
            return await fn(session, symbol, tf, limit)
    except Exception as e:
        logger.warning("[history] %s %s %s: %s", exchange, symbol, tf, e)
        return []
