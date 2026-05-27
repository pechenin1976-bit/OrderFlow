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
from src.compose.volume_profile import build_volume_profile
from src.symbols.price_scale import scale_exchange_snapshot


EXCHANGES = ("binance", "bybit", "hyperliquid", "okx", "binance_spot", "bybit_spot", "okx_spot")


@dataclass
class ExchangeSymbolState:
    exchange: str
    symbol: str
    book: LocalOrderBook = field(default_factory=LocalOrderBook)
    bars: MultiTfBars = field(init=False)
    last_price: float = 0.0
    last_trade_ms: int = 0
    connected: bool = False
    error: str = ""
    _seeded_tf: set = field(default_factory=set)

    def __post_init__(self) -> None:
        self.bars = MultiTfBars(config.TF_SECONDS, self.exchange)

    def on_trade(self, price: float, qty: float, ts_ms: int) -> None:
        self.last_price = price
        self.last_trade_ms = ts_ms
        self.bars.on_trade(price, qty, ts_ms)

    def snapshot_exchange(self, tf: str, bars_count: int, range_pct: float) -> Dict[str, Any]:
        bars = self.bars.get(tf, bars_count)
        # Одна цена для шапки, графика и центра профиля — close последней свечи
        last = float(bars[-1][4]) if bars else self.last_price
        if last > 0:
            self.last_price = last
        bids, asks = self.book.top_levels(config.BOOK_DEPTH_LEVELS)
        best_bid = bids[0][0] if bids else 0.0
        best_ask = asks[0][0] if asks else 0.0
        bbo_mid = self.book.mid_price() or ((best_bid + best_ask) / 2 if best_bid and best_ask else last)
        mid = bbo_mid
        densities = compose_liquidity_zones(
            bids,
            asks,
            mid,
            band_bps=config.BAND_BPS,
            min_zone_vol=config.MIN_ZONE_VOL,
            top_n=config.TOP_ZONES_PER_SIDE,
        )
        profile = build_volume_profile(
            bids,
            asks,
            bbo_mid,
            range_pct=range_pct,
            steps_each_side=config.PROFILE_STEPS,
            best_bid=best_bid,
            best_ask=best_ask,
        )
        return {
            "connected": self.connected,
            "last": last,
            "mid": mid,
            "best_bid": best_bid,
            "best_ask": best_ask,
            "bars": bars,
            "densities": densities,
            "profile": profile,
            "error": self.error or None,
        }


class MarketState:
    def __init__(self, symbols: list[str]):
        self.symbols = [s.upper() for s in symbols]
        self._states: Dict[str, Dict[str, ExchangeSymbolState]] = {}
        self._latest_snapshot: Dict[str, Any] = {}
        self._lock = asyncio.Lock()
        self.funding_rates: Dict[str, Dict[str, float]] = {}
        for sym in self.symbols:
            self._states[sym] = {
                ex: ExchangeSymbolState(exchange=ex, symbol=sym) for ex in EXCHANGES
            }

    def get(self, symbol: str, exchange: str) -> ExchangeSymbolState:
        sym = symbol.upper()
        return self._states[sym][exchange]

    async def _ensure_history(self, sym: str, tf: str, *, refresh: bool = False) -> None:
        from src.history.klines import fetch_history

        for ex, st in self._states[sym].items():
            if not refresh and tf in st._seeded_tf:
                continue
            bars = await fetch_history(ex, sym, tf, config.SNAPSHOT_BARS)
            if bars:
                st.bars.seed(tf, bars)
            elif refresh:
                st.bars.clear_tf(tf)
            st._seeded_tf.add(tf)

    @staticmethod
    def _cache_key(sym: str, tf: str, range_pct: float) -> str:
        return f"{sym.upper()}:{tf}:{range_pct:g}"

    async def build_snapshot(
        self,
        symbol: str,
        tf: str,
        bars_count: int,
        profile_range_pct: float | None = None,
        refresh_history: bool = False,
    ) -> Dict[str, Any]:
        sym = symbol.upper()
        if sym not in self._states:
            return {}
        range_pct = _normalize_profile_range(profile_range_pct)
        await self._ensure_history(sym, tf, refresh=refresh_history)
        exchanges: Dict[str, Any] = {}
        for ex, st in self._states[sym].items():
            ex_snap = scale_exchange_snapshot(
                ex, sym, st.snapshot_exchange(tf, bars_count, range_pct)
            )
            fr = self.funding_rates.get(ex, {}).get(sym)
            if fr is not None:
                ex_snap["funding_rate"] = fr
            exchanges[ex] = ex_snap
        snap = {
            "ts": int(time.time()),
            "symbol": sym,
            "tf": tf,
            "profile_range_pct": range_pct,
            "exchanges": exchanges,
            "meta": {"publish_interval_sec": config.PUBLISH_INTERVAL_SEC},
        }
        async with self._lock:
            self._latest_snapshot[self._cache_key(sym, tf, range_pct)] = snap
        return snap

    async def get_cached(
        self, symbol: str, tf: str, profile_range_pct: float
    ) -> Optional[Dict[str, Any]]:
        key = self._cache_key(symbol, tf, profile_range_pct)
        async with self._lock:
            return self._latest_snapshot.get(key)


def _normalize_profile_range(value: float | str | None) -> float:
    if value is None:
        return config.PROFILE_RANGE_PCT
    try:
        r = float(value)
    except (TypeError, ValueError):
        return config.PROFILE_RANGE_PCT
    for choice in config.PROFILE_RANGE_CHOICES:
        if abs(r - choice) < 0.01:
            return choice
    return config.PROFILE_RANGE_CHOICES[0]
