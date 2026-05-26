from __future__ import annotations

from typing import List

from src.collectors.binance import BinanceCollector, BinanceSpotCollector
from src.collectors.bybit import BybitCollector, BybitSpotCollector
from src.collectors.hyperliquid import HyperliquidCollector
from src.collectors.okx import OkxCollector, OkxSpotCollector
from src.state.market_state import MarketState

COLLECTORS = {
    "binance": BinanceCollector,
    "binance_spot": BinanceSpotCollector,
    "bybit": BybitCollector,
    "bybit_spot": BybitSpotCollector,
    "hyperliquid": HyperliquidCollector,
    "okx": OkxCollector,
    "okx_spot": OkxSpotCollector,
}


def start_all(state: MarketState, symbols: List[str], enabled: List[str] | None = None):
    names = enabled or list(COLLECTORS.keys())
    tasks = []
    for name in names:
        cls = COLLECTORS.get(name)
        if cls:
            tasks.append(cls(state, symbols).start())
    return tasks
