"""Профиль ликвидности стакана — фиксированная сетка от BBO mid."""
from __future__ import annotations

import math
from typing import Any, Dict, List, Tuple


def price_precision(ref: float) -> int:
    """Знаков после запятой для подписи уровней профиля."""
    if ref >= 1000:
        return 2
    if ref >= 1:
        return 4
    if ref >= 0.01:
        return 6
    if ref >= 0.0001:
        return 8
    return 10


def _sqrt_norm(value: float, max_val: float, min_pct: float = 4.0) -> float:
    if value <= 0 or max_val <= 0:
        return 0.0
    pct = math.sqrt(value / max_val) * 100.0
    return min(100.0, max(min_pct, pct))


def build_volume_profile(
    bid_levels: List[Tuple[float, float]],
    ask_levels: List[Tuple[float, float]],
    mid: float,
    range_pct: float = 1.0,
    steps_each_side: int = 10,
    best_bid: float = 0.0,
    best_ask: float = 0.0,
) -> Dict[str, Any]:
    """
    Лимитные заявки (L2), не trades.

    Сетка: ровно steps ступеней вверх и вниз от BBO mid (±range_pct),
    шаг = range_pct / steps на сторону. Цены ступеней не «плывут» при тиках.

    Ширина столбика: sqrt(объём / max) — мелкие уровни видны.
    """
    empty: Dict[str, Any] = {
        "mid": mid,
        "range_pct": range_pct,
        "steps": steps_each_side,
        "source": "orderbook",
        "levels": [],
    }
    if mid <= 0 or steps_each_side < 1 or range_pct <= 0:
        return empty

    bb = best_bid if best_bid > 0 else 0.0
    ba = best_ask if best_ask > 0 else 0.0
    if bb > 0 and ba > 0:
        ref = (bb + ba) / 2.0
    else:
        ref = mid

    half = range_pct / 100.0
    lo = ref * (1.0 - half)
    hi = ref * (1.0 + half)
    n_bins = steps_each_side * 2
    step = (hi - lo) / n_bins
    if step <= 0:
        return empty

    step_pct = range_pct / steps_each_side

    buckets: List[Dict[str, Any]] = [
        {
            "price_lo": lo + i * step,
            "price_hi": lo + (i + 1) * step,
            "price": lo + (i + 0.5) * step,
            "bid": 0.0,
            "ask": 0.0,
        }
        for i in range(n_bins)
    ]

    def _bin(price: float) -> int:
        if price < lo or price > hi:
            return -1
        idx = int((price - lo) / step)
        return min(n_bins - 1, max(0, idx))

    for price, qty in bid_levels:
        if qty <= 0:
            continue
        i = _bin(price)
        if i >= 0:
            buckets[i]["bid"] += qty

    for price, qty in ask_levels:
        if qty <= 0:
            continue
        i = _bin(price)
        if i >= 0:
            buckets[i]["ask"] += qty

    max_total_usdt = 0.0
    for b in buckets:
        b["bid"] = round(b["bid"], 6)
        b["ask"] = round(b["ask"], 6)
        b["total"] = b["bid"] + b["ask"]
        px = b["price"]
        b["bid_usdt"] = b["bid"] * px
        b["ask_usdt"] = b["ask"] * px
        b["total_usdt"] = b["bid_usdt"] + b["ask_usdt"]
        max_total_usdt = max(max_total_usdt, b["total_usdt"])

    if max_total_usdt <= 0:
        return empty

    prec = price_precision(ref)
    levels: List[Dict[str, Any]] = []
    for b in buckets:
        bid_share = (b["bid"] / b["total"] * 100.0) if b["total"] > 0 else 50.0
        at_mid = b["price_lo"] <= ref <= b["price_hi"]
        levels.append({
            "price": round(b["price"], prec),
            "bid": b["bid"],
            "ask": b["ask"],
            "total": b["total"],
            "bid_usdt": round(b["bid_usdt"], 2),
            "ask_usdt": round(b["ask_usdt"], 2),
            "total_usdt": round(b["total_usdt"], 2),
            "total_norm": round(_sqrt_norm(b["total_usdt"], max_total_usdt), 1),
            "bid_share": round(bid_share, 1),
            "dist_pct": round((b["price"] - ref) / ref * 100.0, 3),
            "at_mid": at_mid,
        })

    levels.sort(key=lambda x: x["price"], reverse=True)

    return {
        "mid": ref,
        "best_bid": round(bb, prec) if bb else None,
        "best_ask": round(ba, prec) if ba else None,
        "range_pct": range_pct,
        "step_pct": round(step_pct, 4),
        "steps": steps_each_side,
        "price_lo": round(lo, prec),
        "price_hi": round(hi, prec),
        "n_levels": len(bid_levels) + len(ask_levels),
        "source": "orderbook",
        "norm": "sqrt",
        "max_total_usdt": round(max_total_usdt, 2),
        "volume_unit": "usdt",  # notional; snapshot sets USDC on Hyperliquid
        "levels": levels,
    }
