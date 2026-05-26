"""Глобальное состояние: symbol × exchange."""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import config
from src.bars.ohlcv import MultiTfBars
from src.book.order_book import LocalOrderBook
from src.compose.liquidity import compose_liquidity_zones


EXCHANGES = ("binance", "bybit", "hyperliquid", "okx")


@dataclass
class ExchangeSymbolState:
    exchange: str
    symbol: str
    book: LocalOrderBook = field(default_factory=LocalOrderBook)
    bars: MultiTfBars = field(default_factory=lambda: MultiTfBars(config.TF_SECONDS))
    last_price: float = 0.0
    last_trade_ms: int = 0
    connected: bool = False
    error: str = ""

    def on_trade(self, price: float, qty: float, ts_ms: int) -> None:
        self.last_price = price
        self.last_trade_ms = ts_ms
        self.bars.on_trade(price, qty, ts_ms)

    def snapshot_exchange(self, tf: str, bars_count: int) -> Dict[str, Any]:
        mid = self.book.mid_price() or self.last_price
        bids, asks = self.book.top_levels(config.BOOK_DEPTH_LEVELS)
        densities = compose_liquidity_zones(
            bids,
            asks,
            mid,
            band_bps=config.BAND_BPS,
            min_zone_vol=config.MIN_ZONE_VOL,
            top_n=config.TOP_ZONES_PER_SIDE,
        )
        return {
            "connected": self.connected,
            "last": self.last_price,
            "mid": mid,
            "bars": self.bars.get(tf, bars_count),
            "densities": densities,
            "error": self.error or None,
        }


class MarketState:
    def __init__(self, symbols: list[str]):
        self.symbols = [s.upper() for s in symbols]
        self._states: Dict[str, Dict[str, ExchangeSymbolState]] = {}
        self._latest_snapshot: Dict[str, Any] = {}
        self._lock = asyncio.Lock()
        for sym in self.symbols:
            self._states[sym] = {
                ex: ExchangeSymbolState(exchange=ex, symbol=sym) for ex in EXCHANGES
            }

    def get(self, symbol: str, exchange: str) -> ExchangeSymbolState:
        sym = symbol.upper()
        return self._states[sym][exchange]

    async def build_snapshot(self, symbol: str, tf: str, bars_count: int) -> Dict[str, Any]:
        sym = symbol.upper()
        if sym not in self._states:
            return {}
        exchanges = {
            ex: st.snapshot_exchange(tf, bars_count)
            for ex, st in self._states[sym].items()
        }
        snap = {
            "ts": int(time.time()),
            "symbol": sym,
            "tf": tf,
            "exchanges": exchanges,
            "meta": {"publish_interval_sec": config.PUBLISH_INTERVAL_SEC},
        }
        async with self._lock:
            self._latest_snapshot[sym] = snap
        return snap

    async def get_cached(self, symbol: str) -> Optional[Dict[str, Any]]:
        async with self._lock:
            return self._latest_snapshot.get(symbol.upper())
