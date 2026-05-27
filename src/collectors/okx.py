"""OKX swap + spot: trades + books5."""
from __future__ import annotations

import json
import logging

import aiohttp

from src.collectors.base import BaseCollector
from src.symbols.spot_filter import okx_spot_listed

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


class OkxSpotCollector(OkxCollector):
    """OKX spot: trades + books5, instId = {BASE}-USDT (без SWAP)."""

    exchange_id = "okx_spot"
    _active: frozenset[str] = frozenset()
    _SUB_CHUNK = 20

    def _inst_id(self, sym: str) -> str:
        return f"{sym.upper()}-USDT"

    @staticmethod
    def _chunks(items: list, size: int) -> list:
        return [items[i : i + size] for i in range(0, len(items), size)]

    async def run(self) -> None:
        self._active = await okx_spot_listed(self.symbols)
        for sym in self.symbols:
            st = self._st(sym)
            if sym in self._active:
                st.error = ""
            else:
                st.connected = True
                st.error = "not_listed"
        logger.info("[okx_spot] connect (%s symbols)", len(self._active))
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(WSS, heartbeat=25) as ws:
                args = []
                for sym in sorted(self._active):
                    inst = self._inst_id(sym)
                    args.append({"channel": "trades", "instId": inst})
                    args.append({"channel": "books5", "instId": inst})
                for chunk in self._chunks(args, self._SUB_CHUNK):
                    await ws.send_json({"op": "subscribe", "args": chunk})
                for sym in self._active:
                    self._st(sym).connected = True
                    self._st(sym).error = ""
                async for msg in ws:
                    if msg.type != aiohttp.WSMsgType.TEXT:
                        if msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                            break
                        continue
                    data = json.loads(msg.data)
                    if data.get("event") == "error":
                        logger.warning("[okx_spot] %s", data.get("msg", data))
                        continue
                    arg = data.get("arg", {})
                    channel = arg.get("channel", "")
                    inst = arg.get("instId", "")
                    sym = inst.split("-")[0] if inst else ""
                    if sym not in self._active:
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
