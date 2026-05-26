"""Базовый WS-коллектор."""
from __future__ import annotations

import abc
import asyncio
import json
import logging
from typing import List

import aiohttp

from src.state.market_state import ExchangeSymbolState, MarketState

logger = logging.getLogger(__name__)


def symbol_to_usdt(symbol: str) -> str:
    return f"{symbol.upper()}USDT"


class BaseCollector(abc.ABC):
    exchange_id: str = ""

    def __init__(self, state: MarketState, symbols: List[str]):
        self.state = state
        self.symbols = [s.upper() for s in symbols]
        self._task: asyncio.Task | None = None

    def _st(self, symbol: str) -> ExchangeSymbolState:
        return self.state.get(symbol, self.exchange_id)

    @abc.abstractmethod
    async def run(self) -> None:
        ...

    def start(self) -> asyncio.Task:
        self._task = asyncio.create_task(self._run_wrapper())
        return self._task

    async def _run_wrapper(self) -> None:
        backoff = 1.0
        while True:
            try:
                await self.run()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning("[%s] disconnected: %s", self.exchange_id, e)
                for sym in self.symbols:
                    st = self._st(sym)
                    st.connected = False
                    st.error = str(e)[:120]
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30.0)

    async def _ws_loop(self, url: str, on_message) -> None:
        timeout = aiohttp.ClientTimeout(total=None, sock_read=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.ws_connect(url, heartbeat=30) as ws:
                await on_message(ws, None)
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        await on_message(ws, json.loads(msg.data))
                    elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                        break
