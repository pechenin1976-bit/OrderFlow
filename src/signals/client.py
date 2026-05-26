"""Отправка сигналов в SignalsHub (как CrCraft)."""
from __future__ import annotations

import logging
from typing import Optional

import aiohttp

import config

logger = logging.getLogger(__name__)


async def send_signal(
    action: str,
    symbol: str,
    strategy: str = "orderflow",
    stop_price: float = 0.0,
    take_price: float = 0.0,
    risk_multiplier: float = 1.0,
    trade_uuid: str = "",
    take_levels: Optional[list] = None,
    take_proportions: Optional[list] = None,
    entry_type: str = "market",
) -> dict:
    if not config.SEND_SIGNALS:
        return {"skipped": True}
    payload = {
        "action": action,
        "symbol": symbol,
        "strategy": strategy,
        "stop_price": stop_price,
        "take_price": take_price,
        "risk": risk_multiplier,
        "trade_uuid": trade_uuid,
        "entry_type": entry_type,
    }
    if take_levels:
        payload["take_levels"] = take_levels
    if take_proportions:
        payload["take_proportions"] = take_proportions

    connector = aiohttp.UnixConnector(path=config.SIGNALS_SOCK)
    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.post(
            "http://localhost/signal",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=3.0),
        ) as resp:
            return await resp.json()
