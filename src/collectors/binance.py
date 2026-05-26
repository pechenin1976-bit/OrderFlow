"""Binance USD-M: aggTrade + depth20@100ms (combined stream)."""
from __future__ import annotations

import logging
from typing import List

import aiohttp

from src.collectors.base import BaseCollector, symbol_to_usdt

logger = logging.getLogger(__name__)


class BinanceCollector(BaseCollector):
    exchange_id = "binance"

    def __init__(self, state, symbols: List[str]):
        super().__init__(state, symbols)
        streams = []
        for sym in self.symbols:
            s = symbol_to_usdt(sym).lower()
            streams.append(f"{s}@aggTrade")
            streams.append(f"{s}@depth20@100ms")
        self._url = "wss://fstream.binance.com/stream?streams=" + "/".join(streams)

    async def run(self) -> None:
        logger.info("[binance] connect %s", self._url[:80])
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(self._url, heartbeat=30) as ws:
                for sym in self.symbols:
                    self._st(sym).connected = True
                    self._st(sym).error = ""
                async for msg in ws:
                    if msg.type != aiohttp.WSMsgType.TEXT:
                        if msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                            break
                        continue
                    import json
                    envelope = json.loads(msg.data)
                    data = envelope.get("data", envelope)
                    stream = envelope.get("stream", "")
                    sym = self._sym_from_stream(stream, data)
                    if not sym:
                        continue
                    st = self._st(sym)
                    ev = data.get("e", "")
                    if ev == "aggTrade":
                        price = float(data["p"])
                        qty = float(data["q"])
                        ts_ms = int(data["T"])
                        st.on_trade(price, qty, ts_ms)
                    elif ev == "depthUpdate" or "depth" in stream:
                        bids = [(float(p), float(q)) for p, q in data.get("b", [])]
                        asks = [(float(p), float(q)) for p, q in data.get("a", [])]
                        if bids or asks:
                            st.book.replace(bids, asks, int(data.get("E", 0)))
                            if st.last_price <= 0:
                                st.last_price = st.book.mid_price()

    def _sym_from_stream(self, stream: str, data: dict) -> str:
        raw = data.get("s") or stream.split("@")[0]
        raw = raw.upper().replace("USDT", "")
        return raw if raw in self.symbols else ""
