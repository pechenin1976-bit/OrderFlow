"""Периодическая публикация snapshot в MarketState."""
from __future__ import annotations

import asyncio
import logging

import config
from src.state.market_state import MarketState

logger = logging.getLogger(__name__)


async def publish_loop(state: MarketState, tf: str = config.DEFAULT_TF) -> None:
    while True:
        try:
            for sym in state.symbols:
                await state.build_snapshot(sym, tf, config.DEFAULT_BARS_COUNT)
        except Exception as e:
            logger.exception("publish_loop: %s", e)
        await asyncio.sleep(config.PUBLISH_INTERVAL_SEC)
