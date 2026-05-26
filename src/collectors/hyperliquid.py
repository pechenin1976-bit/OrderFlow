"""Hyperliquid: trades + l2Book."""

from __future__ import annotations



import json

import logging



import aiohttp



from src.collectors.base import BaseCollector
from src.symbols.instruments import from_native, native_coin



logger = logging.getLogger(__name__)



WSS = "wss://api.hyperliquid.xyz/ws"





class HyperliquidCollector(BaseCollector):

    exchange_id = "hyperliquid"



    def _resolve_coin(self, data: dict) -> str:

        inner = data.get("data")

        if isinstance(inner, dict):

            base = from_native("hyperliquid", str(inner.get("coin", "")))

            return base if base in self.symbols else ""

        if isinstance(inner, list) and inner:

            base = from_native("hyperliquid", str(inner[0].get("coin", "")))

            return base if base in self.symbols else ""

        return ""



    async def run(self) -> None:

        logger.info("[hyperliquid] connect")

        async with aiohttp.ClientSession() as session:

            async with session.ws_connect(WSS, heartbeat=30) as ws:

                for sym in self.symbols:

                    coin = native_coin("hyperliquid", sym)

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

                    if channel == "subscriptionResponse":

                        continue



                    if channel == "trades":

                        sym = self._resolve_coin(data)

                        if not sym:

                            continue

                        st = self._st(sym)

                        for row in data.get("data", []):

                            price = float(row.get("px", 0))

                            qty = float(row.get("sz", 0))

                            ts_ms = int(row.get("time", 0))

                            if price > 0:

                                st.on_trade(price, qty, ts_ms)

                    elif channel == "l2Book":

                        sym = self._resolve_coin(data)

                        if not sym:

                            continue

                        book = data.get("data", {})

                        if not isinstance(book, dict):

                            continue

                        levels = book.get("levels", [[], []])

                        if len(levels) >= 2:

                            bids = [

                                (float(l["px"]), float(l["sz"]))

                                for l in levels[0]

                                if float(l.get("sz", 0)) > 0

                            ]

                            asks = [

                                (float(l["px"]), float(l["sz"]))

                                for l in levels[1]

                                if float(l.get("sz", 0)) > 0

                            ]

                            st = self._st(sym)

                            st.book.replace(bids, asks, int(book.get("time", 0)))

                            if st.last_price <= 0:

                                mid = st.book.mid_price()

                                if mid > 0:

                                    st.last_price = mid

