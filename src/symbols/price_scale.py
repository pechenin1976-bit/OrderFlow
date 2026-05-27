"""Нормализация цен к «1 монете» для UI (1000PEPE / kPEPE → PEPE)."""
from __future__ import annotations

from typing import Any, Dict, List

import config

_FUTURES_EXCHANGES = frozenset({"binance", "bybit", "hyperliquid"})


def display_divisor(exchange: str, symbol: str) -> float:
    """
    Делитель биржевой цены → цена за 1 coin в UI.
    Binance/Bybit futures: 1000PEPEUSDT; spot: PEPEUSDT.
    Hyperliquid: kPEPE ≈ 1000× PEPE.
    """
    if exchange not in _FUTURES_EXCHANGES:
        return 1.0
    sym = symbol.upper()
    if sym in config.BINANCE_SYMBOL_MAP or sym in config.HYPERLIQUID_SYMBOL_MAP:
        return 1000.0
    return 1.0


def _scale_price(p: float | None, div: float) -> float | None:
    if p is None or not p:
        return p
    return p / div


def _scale_bars(bars: List[List[float]], div: float) -> List[List[float]]:
    if div == 1.0 or not bars:
        return bars
    out: List[List[float]] = []
    for b in bars:
        out.append([b[0], b[1] / div, b[2] / div, b[3] / div, b[4] / div, *b[5:]])
    return out


def _scale_profile(profile: Dict[str, Any], div: float) -> Dict[str, Any]:
    if div == 1.0 or not profile:
        return profile
    p = dict(profile)
    for key in ("mid", "best_bid", "best_ask", "price_lo", "price_hi"):
        if key in p and p[key] is not None:
            p[key] = _scale_price(float(p[key]), div)
    levels = []
    for row in p.get("levels") or []:
        r = dict(row)
        if "price" in r:
            r["price"] = _scale_price(float(r["price"]), div)
        levels.append(r)
    p["levels"] = levels
    return p


def scale_exchange_snapshot(
    exchange: str, symbol: str, snap: Dict[str, Any]
) -> Dict[str, Any]:
    div = display_divisor(exchange, symbol)
    if div == 1.0:
        return snap
    out = dict(snap)
    out["last"] = _scale_price(float(out.get("last") or 0), div) or out.get("last")
    out["mid"] = _scale_price(float(out.get("mid") or 0), div) or out.get("mid")
    if out.get("best_bid"):
        out["best_bid"] = _scale_price(float(out["best_bid"]), div)
    if out.get("best_ask"):
        out["best_ask"] = _scale_price(float(out["best_ask"]), div)
    out["bars"] = _scale_bars(out.get("bars") or [], div)
    if out.get("profile"):
        out["profile"] = _scale_profile(out["profile"], div)
    out["price_divisor"] = div
    return out
