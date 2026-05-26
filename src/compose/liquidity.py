"""Композиция уровней стакана в зоны ликвидности."""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

import numpy as np


def _cluster_side(
    levels: List[Tuple[float, float]],
    mid: float,
    band_bps: float,
    min_zone_vol: float,
    side: str,
) -> List[Dict[str, Any]]:
    if not levels or mid <= 0:
        return []

    sorted_levels = sorted(levels, key=lambda x: x[0], reverse=(side == "bid"))
    zones: List[Dict[str, Any]] = []
    cur_prices: List[float] = []
    cur_vol = 0.0

    def flush() -> None:
        nonlocal cur_prices, cur_vol
        if not cur_prices or cur_vol < min_zone_vol:
            cur_prices, cur_vol = [], 0.0
            return
        p_center = sum(cur_prices) / len(cur_prices)
        dist_bps = abs(p_center - mid) / mid * 10000.0
        zones.append({
            "price": round(p_center, 8),
            "volume": round(cur_vol, 6),
            "dist_bps": round(dist_bps, 2),
            "side": side,
            "n_levels": len(cur_prices),
        })
        cur_prices, cur_vol = [], 0.0

    band_frac = band_bps / 10000.0
    anchor = sorted_levels[0][0]

    for price, vol in sorted_levels:
        if vol <= 0:
            continue
        if not cur_prices:
            cur_prices = [price]
            cur_vol = vol
            anchor = price
            continue
        if abs(price - anchor) / mid <= band_frac:
            cur_prices.append(price)
            cur_vol += vol
        else:
            flush()
            cur_prices = [price]
            cur_vol = vol
            anchor = price
    flush()
    return zones


def compose_liquidity_zones(
    bid_levels: List[Tuple[float, float]],
    ask_levels: List[Tuple[float, float]],
    mid: float,
    band_bps: float = 5.0,
    min_zone_vol: float = 0.0,
    top_n: int = 15,
) -> List[Dict[str, Any]]:
    bids = _cluster_side(bid_levels, mid, band_bps, min_zone_vol, "bid")
    asks = _cluster_side(ask_levels, mid, band_bps, min_zone_vol, "ask")
    all_z = bids + asks
    if not all_z:
        return []

    vols = np.array([z["volume"] for z in all_z], dtype=float)
    med = float(np.median(vols)) if len(vols) else 1.0
    med = med if med > 0 else 1.0

    for z in all_z:
        z["score"] = round(z["volume"] / med, 3)

    all_z.sort(key=lambda z: z["score"], reverse=True)
    return all_z[: top_n * 2]
