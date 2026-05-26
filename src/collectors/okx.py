"""OKX swap: trades + books5."""
from __future__ import annotations

import json
import logging

import aiohttp

from src.collectors.base import BaseCollector

logger = logging.getLogger(__name__)

WSS = "wss://ws.okx.com:8443/ws/v5/public"


class OkxCollector(BaseCollector):
    exchange_id = "okx"

    def _inst_id(self, sym: str) -> str:
        return f"{sym.upper()}-USDT-SWAP"

    async def run(self) -> None:
        logger.info("[okx] connect")
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(WSS, heartbeat=25) as ws:
                args = []
                for sym in self.symbols:
                    inst = self._inst_id(sym)
                    args.append({"channel": "trades", "instId": inst})
                    args.append({"channel": "books5", "instId": inst})
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
                    arg = data.get("arg", {})
                    channel = arg.get("channel", "")
                    inst = arg.get("instId", "")
                    sym = inst.split("-")[0] if inst else ""
                    if sym not in self.symbols:
                        continue
                    st = self._st(sym)
                    if channel == "trades":
                        for row in data.get("data", []):
                            price = float(row.get("px", 0))
                            qty = float(row.get("sz", 0))
                            ts_ms = int(row.get("ts", 0))
                            if price > 0:
                                st.on_trade(price, qty, ts_ms)
                    elif channel == "books5":
                        for row in data.get("data", []):
                            bids = [(float(p), float(q)) for p, q, *_ in row.get("bids", [])]
                            asks = [(float(p), float(q)) for p, q, *_ in row.get("asks", [])]
                            st.book.replace(bids, asks, int(row.get("ts", 0)))
