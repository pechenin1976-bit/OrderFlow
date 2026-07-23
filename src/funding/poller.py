"""Фоновый опрос ставок фандинга каждые 60 сек."""
from __future__ import annotations

import asyncio
import logging

from src.funding.rates import fetch_all_funding
from src.state.market_state import MarketState

logger = logging.getLogger(__name__)

POLL_INTERVAL_SEC = 60


async def funding_loop(state: MarketState) -> None:
    while True:
        try:
            rates = await fetch_all_funding(state.symbols)
            state.funding_rates = rates
            await state.refresh_funding_in_cache()
            totals = {ex: len(v) for ex, v in rates.items()}
            logger.info("[funding] updated %s", totals)
        except Exception as e:
            logger.warning("[funding] loop error: %s", e)
        await asyncio.sleep(POLL_INTERVAL_SEC)
