"""Периодическая публикация snapshot в MarketState (только активные ключи)."""
from __future__ import annotations

import asyncio
import logging

import config
from src.state.market_state import MarketState

logger = logging.getLogger(__name__)


async def publish_loop(state: MarketState, tf: str = config.DEFAULT_TF) -> None:
    while True:
        try:
            keys = state.active_interest()
            if not keys:
                # Без клиентов — тёплый дефолт, без прогона всех символов
                if state.symbols:
                    await state.build_snapshot(
                        state.symbols[0], tf, config.DEFAULT_BARS_COUNT
                    )
            else:
                for sym, key_tf, range_pct in keys:
                    await state.build_snapshot(
                        sym, key_tf, config.DEFAULT_BARS_COUNT, range_pct
                    )
        except Exception as e:
            logger.exception("publish_loop: %s", e)
        await asyncio.sleep(config.PUBLISH_INTERVAL_SEC)
