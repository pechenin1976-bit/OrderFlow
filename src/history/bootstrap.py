"""Прогрев OHLCV из REST при старте."""
from __future__ import annotations

import asyncio
import logging

import config
from src.history.klines import fetch_history
from src.state.market_state import EXCHANGES, MarketState

logger = logging.getLogger(__name__)


async def seed_exchange_history(
    state: MarketState,
    exchange: str,
    symbols: list[str],
    tf: str,
    limit: int,
) -> None:
    for sym in symbols:
        bars = await fetch_history(exchange, sym, tf, limit)
        if bars:
            state.get(sym, exchange).bars.seed(tf, bars)
            logger.info("[history] %s %s %s: %d bars", exchange, sym, tf, len(bars))


async def seed_all(
    state: MarketState,
    symbols: list[str],
    exchanges: list[str],
    tf: str | None = None,
) -> None:
    tf = tf or config.DEFAULT_TF
    limit = config.SNAPSHOT_BARS
    tasks = [
        seed_exchange_history(state, ex, symbols, tf, limit)
        for ex in exchanges
        if ex in EXCHANGES
    ]
    await asyncio.gather(*tasks)
