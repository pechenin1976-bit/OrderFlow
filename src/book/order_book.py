"""Локальный L2 стакан из WS depth."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass
class LocalOrderBook:
    bids: Dict[float, float] = field(default_factory=dict)
    asks: Dict[float, float] = field(default_factory=dict)
    last_update_ms: int = 0

    def replace(self, bids: List[Tuple[float, float]], asks: List[Tuple[float, float]], ts_ms: int = 0) -> None:
        self.bids = {p: q for p, q in bids if q > 0}
        self.asks = {p: q for p, q in asks if q > 0}
        self.last_update_ms = ts_ms

    def apply_delta(
        self,
        bids: List[Tuple[float, float]],
        asks: List[Tuple[float, float]],
        ts_ms: int = 0,
        max_levels: int | None = None,
    ) -> None:
        for p, q in bids:
            if q <= 0:
                self.bids.pop(p, None)
            else:
                self.bids[p] = q
        for p, q in asks:
            if q <= 0:
                self.asks.pop(p, None)
            else:
                self.asks[p] = q
        self.last_update_ms = ts_ms
        if max_levels is not None and max_levels > 0:
            self.prune(max_levels)

    def prune(self, max_levels: int) -> None:
        """Оставить только top-N уровней с каждой стороны (по цене)."""
        if len(self.bids) > max_levels:
            keep = sorted(self.bids.keys(), reverse=True)[:max_levels]
            self.bids = {p: self.bids[p] for p in keep}
        if len(self.asks) > max_levels:
            keep = sorted(self.asks.keys())[:max_levels]
            self.asks = {p: self.asks[p] for p in keep}

    def mid_price(self) -> float:
        if not self.bids or not self.asks:
            return 0.0
        best_bid = max(self.bids)
        best_ask = min(self.asks)
        return (best_bid + best_ask) / 2.0

    def top_levels(self, n: int = 50) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]]]:
        bid_levels = sorted(self.bids.items(), key=lambda x: x[0], reverse=True)[:n]
        ask_levels = sorted(self.asks.items(), key=lambda x: x[0])[:n]
        return bid_levels, ask_levels
