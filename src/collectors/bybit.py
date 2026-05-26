"""Bybit linear: publicTrade + orderbook.50."""
from __future__ import annotations

import json
import logging
from typing import List

import aiohttp

from src.collectors.base import BaseCollector, symbol_to_usdt

logger = logging.getLogger(__name__)

WSS = "wss://stream.bybit.com/v5/public/linear"


class BybitCollector(BaseCollector):
    exchange_id = "bybit"

    async def run(self) -> None:
        logger.info("[bybit] connect")
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(WSS, heartbeat=30) as ws:
                args = []
                for sym in self.symbols:
                    s = symbol_to_usdt(sym)
                    args.append(f"publicTrade.{s}")
                    args.append(f"orderbook.50.{s}")
                await ws.send_json({"op": "subscribe", "args": args})
                for sym in self.symbols:
                    self._st(sym).connected = True
                    self._st(sym).error = ""
                async for msg in ws:
                    if msg.type != aiohttp.WSMsgType.TEXT:
                        if msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                            break
                        continue
                    data = json.loads(msg.data)
                    topic = data.get("topic", "")
                    if not topic:
                        continue
                    sym = self._sym_from_topic(topic)
                    if not sym:
                        continue
                    st = self._st(sym)
                    if topic.startswith("publicTrade"):
                        for row in data.get("data", []):
                            price = float(row.get("p", row.get("price", 0)))
                            qty = float(row.get("v", row.get("size", 0)))
                            ts_ms = int(row.get("T", row.get("ts", 0)))
                            if price > 0:
                                st.on_trade(price, qty, ts_ms)
                    elif "orderbook" in topic:
                        payload = data.get("data", {})
                        if isinstance(payload, list):
                            payload = payload[0] if payload else {}
                        bids = [(float(p), float(q)) for p, q in payload.get("b", [])]
                        asks = [(float(p), float(q)) for p, q in payload.get("a", [])]
                        typ = data.get("type", "snapshot")
                        if typ == "snapshot" or not st.book.bids:
                            st.book.replace(bids, asks)
                        else:
                            st.book.apply_delta(bids, asks)

    def _sym_from_topic(self, topic: str) -> str:
        part = topic.split(".")[-1].upper().replace("USDT", "")
        return part if part in self.symbols else ""
