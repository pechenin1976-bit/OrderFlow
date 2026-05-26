from __future__ import annotations

from typing import List

from src.collectors.binance import BinanceCollector
from src.collectors.bybit import BybitCollector
from src.collectors.hyperliquid import HyperliquidCollector
from src.collectors.okx import OkxCollector
from src.state.market_state import MarketState

COLLECTORS = {
    "binance": BinanceCollector,
    "bybit": BybitCollector,
    "hyperliquid": HyperliquidCollector,
    "okx": OkxCollector,
}


def start_all(state: MarketState, symbols: List[str], enabled: List[str] | None = None):
    names = enabled or list(COLLECTORS.keys())
    tasks = []
    for name in names:
        cls = COLLECTORS.get(name)
        if cls:
            tasks.append(cls(state, symbols).start())
    return tasks
