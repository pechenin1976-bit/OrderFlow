"""Hyperliquid: trades + l2Book."""
from __future__ import annotations

import json
import logging

import aiohttp

from src.collectors.base import BaseCollector

logger = logging.getLogger(__name__)

WSS = "wss://api.hyperliquid.xyz/ws"


class HyperliquidCollector(BaseCollector):
    exchange_id = "hyperliquid"

    async def run(self) -> None:
        logger.info("[hyperliquid] connect")
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(WSS, heartbeat=30) as ws:
                for sym in self.symbols:
                    coin = sym.upper()
                    await ws.send_json({
                        "method": "subscribe",
                        "subscription": {"type": "trades", "coin": coin},
                    })
                    await ws.send_json({
                        "method": "subscribe",
                        "subscription": {"type": "l2Book", "coin": coin},
                    })
                    self._st(sym).connected = True
                    self._st(sym).error = ""
                async for msg in ws:
                    if msg.type != aiohttp.WSMsgType.TEXT:
                        if msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                            break
                        continue
                    data = json.loads(msg.data)
                    channel = data.get("channel", "")
                    if channel == "trades":
                        sym = self._coin(data)
                        if not sym:
                            continue
                        for row in data.get("data", []):
                            price = float(row.get("px", 0))
                            qty = float(row.get("sz", 0))
                            ts_ms = int(row.get("time", 0))
                            if price > 0:
                                self._st(sym).on_trade(price, qty, ts_ms)
                    elif channel == "l2Book":
                        sym = self._coin(data)
                        if not sym:
                            continue
                        book = data.get("data", {}).get("levels", [[], []])
                        if len(book) >= 2:
                            bids = [(float(l["px"]), float(l["sz"])) for l in book[0] if float(l.get("sz", 0)) > 0]
                            asks = [(float(l["px"]), float(l["sz"])) for l in book[1] if float(l.get("sz", 0)) > 0]
                            self._st(sym).book.replace(bids, asks)

    def _coin(self, data: dict) -> str:
        inner = data.get("data")
        if isinstance(inner, dict):
            c = str(inner.get("coin", "")).upper()
            return c if c in self.symbols else ""
        return ""
