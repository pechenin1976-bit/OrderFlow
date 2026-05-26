"""Binance USD-M futures + spot: aggTrade + depth20@100ms (combined stream)."""

from __future__ import annotations



import json

import logging

from typing import List, Tuple



import aiohttp



from src.collectors.base import BaseCollector
from src.symbols.instruments import from_native, usdt_instrument



logger = logging.getLogger(__name__)





def _levels(raw_bids, raw_asks) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]]]:

    bids = [(float(p), float(q)) for p, q in (raw_bids or [])]

    asks = [(float(p), float(q)) for p, q in (raw_asks or [])]

    return bids, asks





class BinanceCollector(BaseCollector):

    exchange_id = "binance"



    def __init__(self, state, symbols: List[str]):

        super().__init__(state, symbols)

        streams = []

        for sym in self.symbols:

            s = usdt_instrument("binance", sym).lower()

            streams.append(f"{s}@aggTrade")

            streams.append(f"{s}@depth20@100ms")

        self._url = "wss://fstream.binance.com/stream?streams=" + "/".join(streams)



    async def run(self) -> None:

        logger.info("[binance] connect %s", self._url[:96])

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

                    envelope = json.loads(msg.data)

                    data = envelope.get("data", envelope)

                    stream = envelope.get("stream", "")

                    sym = self._sym_from_stream(stream, data)

                    if not sym:

                        continue

                    st = self._st(sym)

                    ev = data.get("e", "")



                    if ev == "aggTrade":

                        st.on_trade(float(data["p"]), float(data["q"]), int(data["T"]))

                        continue



                    if ev == "depthUpdate" or "depth" in stream:

                        raw_b = data.get("b") or data.get("bids")

                        raw_a = data.get("a") or data.get("asks")

                        bids, asks = _levels(raw_b, raw_a)

                        if bids or asks:

                            if "depth20" in stream or data.get("bids") is not None:

                                st.book.replace(bids, asks, int(data.get("E", 0)))

                            else:

                                st.book.apply_delta(bids, asks, int(data.get("E", 0)))

                            if st.last_price <= 0:

                                st.last_price = st.book.mid_price()

                        continue



                    # Partial book snapshot (bids/asks без поля e) — новый формат WS

                    if "bids" in data or "asks" in data:

                        bids, asks = _levels(data.get("bids"), data.get("asks"))

                        if bids or asks:

                            st.book.replace(bids, asks)

                            if st.last_price <= 0:

                                st.last_price = st.book.mid_price()



    def _sym_from_stream(self, stream: str, data: dict) -> str:

        raw = data.get("s") or stream.split("@")[0]

        base = from_native("binance", str(raw))

        return base if base in self.symbols else ""


class BinanceSpotCollector(BinanceCollector):
    """Binance spot: aggTrade + depth20@100ms через stream.binance.com."""

    exchange_id = "binance_spot"

    def __init__(self, state, symbols: List[str]):
        # Вызываем BaseCollector напрямую, минуя BinanceCollector.__init__,
        # чтобы использовать spot-URL и spot-маппинг (без 1000x).
        from src.collectors.base import BaseCollector
        BaseCollector.__init__(self, state, symbols)
        streams = []
        for sym in self.symbols:
            s = usdt_instrument("binance_spot", sym).lower()
            streams.append(f"{s}@aggTrade")
            streams.append(f"{s}@depth20@100ms")
        self._url = "wss://stream.binance.com:9443/stream?streams=" + "/".join(streams)

    def _sym_from_stream(self, stream: str, data: dict) -> str:
        raw = data.get("s") or stream.split("@")[0]
        base = from_native("binance_spot", str(raw))
        return base if base in self.symbols else ""

