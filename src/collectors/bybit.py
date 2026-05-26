"""Bybit linear: publicTrade + orderbook.50."""
from __future__ import annotations

import json
import logging
from typing import List, Tuple

import aiohttp

import config
from src.collectors.base import BaseCollector
from src.collectors.bybit_symbols import instrument_id, symbol_from_instrument
from src.symbols.instruments import from_native, usdt_instrument

logger = logging.getLogger(__name__)

WSS = "wss://stream.bybit.com/v5/public/linear"
WSS_SPOT = "wss://stream.bybit.com/v5/public/spot"
REST_ORDERBOOK = "https://api.bybit.com/v5/market/orderbook"


class BybitCollector(BaseCollector):
    exchange_id = "bybit"

    @staticmethod
    def _chunks(items: List[str], size: int) -> List[List[str]]:
        return [items[i : i + size] for i in range(0, len(items), size)]

    async def _subscribe_all(self, ws: aiohttp.ClientWebSocketResponse) -> None:
        args: List[str] = []
        for sym in self.symbols:
            inst = instrument_id(sym)
            args.append(f"publicTrade.{inst}")
            args.append(f"orderbook.50.{inst}")
        batch = config.BYBIT_WS_SUB_BATCH
        chunks = self._chunks(args, batch)
        for chunk in chunks:
            await ws.send_json({"op": "subscribe", "args": chunk})
        logger.info("[bybit] subscribed %s topics in %s batches", len(args), len(chunks))

    async def _rest_orderbook(self, session: aiohttp.ClientSession, symbol: str) -> Tuple[List, List]:
        inst = instrument_id(symbol)
        params = {"category": "linear", "symbol": inst, "limit": "50"}
        async with session.get(REST_ORDERBOOK, params=params, timeout=aiohttp.ClientTimeout(total=10)) as r:
            data = await r.json()
        result = (data.get("result") or {}) if data.get("retCode") == 0 else {}
        bids = [(float(p), float(q)) for p, q in result.get("b", [])]
        asks = [(float(p), float(q)) for p, q in result.get("a", [])]
        return bids, asks

    def _apply_book(self, st, typ: str, bids: List, asks: List) -> None:
        if typ == "snapshot":
            if bids or asks:
                st.book.replace(bids, asks)
            return
        if not st.book.bids and not st.book.asks:
            return
        if bids or asks:
            st.book.apply_delta(bids, asks)

    async def run(self) -> None:
        logger.info("[bybit] connect")
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(WSS, heartbeat=30) as ws:
                await self._subscribe_all(ws)
                for sym in self.symbols:
                    self._st(sym).connected = True
                    self._st(sym).error = ""
                async for msg in ws:
                    if msg.type != aiohttp.WSMsgType.TEXT:
                        if msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                            break
                        continue
                    data = json.loads(msg.data)
                    if data.get("op") == "subscribe" and not data.get("success"):
                        logger.warning("[bybit] subscribe fail: %s", data.get("ret_msg"))
                        continue
                    topic = data.get("topic", "")
                    if not topic:
                        continue
                    payload = data.get("data", {})
                    if isinstance(payload, list):
                        payload = payload[0] if payload else {}
                    sym = self._sym_from_topic(topic, payload)
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
                        bids = [(float(p), float(q)) for p, q in payload.get("b", [])]
                        asks = [(float(p), float(q)) for p, q in payload.get("a", [])]
                        self._apply_book(st, data.get("type", "snapshot"), bids, asks)
                        if not st.book.bids and not st.book.asks:
                            try:
                                rb, ra = await self._rest_orderbook(session, sym)
                                if rb or ra:
                                    st.book.replace(rb, ra)
                            except Exception as e:
                                logger.debug("[bybit] REST book %s: %s", sym, e)

    def _sym_from_topic(self, topic: str, payload: dict) -> str:
        inst = payload.get("s") or topic.split(".")[-1] or ""
        base = symbol_from_instrument(str(inst))
        return base if base in self.symbols else ""


class BybitSpotCollector(BybitCollector):
    """Bybit spot: publicTrade + orderbook.50 через wss://.../spot."""

    exchange_id = "bybit_spot"

    def _inst(self, sym: str) -> str:
        return usdt_instrument("bybit_spot", sym)

    async def _subscribe_all(self, ws: aiohttp.ClientWebSocketResponse) -> None:
        args: List[str] = []
        for sym in self.symbols:
            inst = self._inst(sym)
            args.append(f"publicTrade.{inst}")
            args.append(f"orderbook.50.{inst}")
        batch = config.BYBIT_WS_SUB_BATCH
        chunks = self._chunks(args, batch)
        for chunk in chunks:
            await ws.send_json({"op": "subscribe", "args": chunk})
        logger.info("[bybit_spot] subscribed %s topics in %s batches", len(args), len(chunks))

    async def _rest_orderbook(self, session: aiohttp.ClientSession, symbol: str) -> Tuple[List, List]:
        inst = self._inst(symbol)
        params = {"category": "spot", "symbol": inst, "limit": "50"}
        async with session.get(REST_ORDERBOOK, params=params, timeout=aiohttp.ClientTimeout(total=10)) as r:
            data = await r.json()
        result = (data.get("result") or {}) if data.get("retCode") == 0 else {}
        bids = [(float(p), float(q)) for p, q in result.get("b", [])]
        asks = [(float(p), float(q)) for p, q in result.get("a", [])]
        return bids, asks

    async def run(self) -> None:
        logger.info("[bybit_spot] connect")
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(WSS_SPOT, heartbeat=30) as ws:
                await self._subscribe_all(ws)
                for sym in self.symbols:
                    self._st(sym).connected = True
                    self._st(sym).error = ""
                async for msg in ws:
                    if msg.type != aiohttp.WSMsgType.TEXT:
                        if msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                            break
                        continue
                    data = json.loads(msg.data)
                    if data.get("op") == "subscribe" and not data.get("success"):
                        logger.warning("[bybit_spot] subscribe fail: %s", data.get("ret_msg"))
                        continue
                    topic = data.get("topic", "")
                    if not topic:
                        continue
                    payload = data.get("data", {})
                    if isinstance(payload, list):
                        payload = payload[0] if payload else {}
                    sym = self._sym_from_topic(topic, payload)
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
                        bids = [(float(p), float(q)) for p, q in payload.get("b", [])]
                        asks = [(float(p), float(q)) for p, q in payload.get("a", [])]
                        self._apply_book(st, data.get("type", "snapshot"), bids, asks)
                        if not st.book.bids and not st.book.asks:
                            try:
                                rb, ra = await self._rest_orderbook(session, sym)
                                if rb or ra:
                                    st.book.replace(rb, ra)
                            except Exception as e:
                                logger.debug("[bybit_spot] REST book %s: %s", sym, e)

    def _sym_from_topic(self, topic: str, payload: dict) -> str:
        inst = payload.get("s") or topic.split(".")[-1] or ""
        base = from_native("bybit_spot", str(inst))
        return base if base in self.symbols else ""

