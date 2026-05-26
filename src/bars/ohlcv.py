"""OHLCV из потока trades (WS)."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, List, Optional


@dataclass
class Bar:
    t: int
    o: float
    h: float
    l: float
    c: float
    v: float

    def to_list(self) -> List[float]:
        return [float(self.t), self.o, self.h, self.l, self.c, self.v]


class OhlcvBuilder:
    def __init__(self, tf_sec: int, max_bars: int = 500):
        self.tf_sec = tf_sec
        self.max_bars = max_bars
        self._bars: Deque[Bar] = deque(maxlen=max_bars)
        self._cur: Optional[Bar] = None

    def on_trade(self, price: float, qty: float, ts_ms: int) -> None:
        if price <= 0:
            return
        bucket = (ts_ms // 1000 // self.tf_sec) * self.tf_sec
        if self._cur is None or self._cur.t != bucket:
            if self._cur is not None:
                self._bars.append(self._cur)
            self._cur = Bar(t=bucket, o=price, h=price, l=price, c=price, v=qty)
        else:
            self._cur.h = max(self._cur.h, price)
            self._cur.l = min(self._cur.l, price)
            self._cur.c = price
            self._cur.v += qty

    def bars(self, count: int) -> List[List[float]]:
        out: List[Bar] = list(self._bars)
        if self._cur is not None:
            out.append(self._cur)
        return [b.to_list() for b in out[-count:]]


class MultiTfBars:
    """По одному билдеру на каждый TF."""

    def __init__(self, tf_seconds: Dict[str, int], max_bars: int = 500):
        self._builders = {tf: OhlcvBuilder(sec, max_bars) for tf, sec in tf_seconds.items()}

    def on_trade(self, price: float, qty: float, ts_ms: int) -> None:
        for b in self._builders.values():
            b.on_trade(price, qty, ts_ms)

    def get(self, tf: str, count: int) -> List[List[float]]:
        b = self._builders.get(tf)
        return b.bars(count) if b else []
