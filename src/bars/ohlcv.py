"""OHLCV из потока trades (WS)."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Deque, Dict, List, Optional


def _week_monday_utc(ts_sec: int) -> int:
    dt = datetime.fromtimestamp(ts_sec, tz=timezone.utc)
    monday = (dt - timedelta(days=dt.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return int(monday.timestamp())


def trade_bucket(ts_ms: int, tf: str, tf_sec: int, exchange: str) -> int:
    """Время открытия свечи — как у REST klines биржи."""
    ts = ts_ms // 1000
    if tf == "1d":
        return ts - (ts % 86400)
    if tf == "1w":
        if exchange == "okx":
            off = 8 * 3600
            return (ts + off) // 604800 * 604800 - off
        if exchange == "hyperliquid":
            return (ts // 604800) * 604800
        return _week_monday_utc(ts)
    return (ts // tf_sec) * tf_sec


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
    def __init__(self, tf: str, tf_sec: int, exchange: str = "", max_bars: int = 500):
        self.tf = tf
        self.tf_sec = tf_sec
        self.exchange = exchange
        self.max_bars = max_bars
        self._bars: Deque[Bar] = deque(maxlen=max_bars)
        self._cur: Optional[Bar] = None

    def _bucket(self, ts_ms: int) -> int:
        bucket = trade_bucket(ts_ms, self.tf, self.tf_sec, self.exchange)
        if self._cur is not None and bucket < self._cur.t:
            bucket = self._cur.t
        return bucket

    def on_trade(self, price: float, qty: float, ts_ms: int) -> None:
        if price <= 0:
            return
        bucket = self._bucket(ts_ms)
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
        out.sort(key=lambda b: b.t)
        return [b.to_list() for b in out[-count:]]

    def seed(self, rows: List[List[float]]) -> None:
        """Загрузить историю: последняя строка — текущая (forming) свеча."""
        self._bars.clear()
        self._cur = None
        if not rows:
            return
        for row in rows[:-1]:
            self._bars.append(
                Bar(
                    t=int(row[0]),
                    o=float(row[1]),
                    h=float(row[2]),
                    l=float(row[3]),
                    c=float(row[4]),
                    v=float(row[5]),
                )
            )
        r = rows[-1]
        self._cur = Bar(
            t=int(r[0]),
            o=float(r[1]),
            h=float(r[2]),
            l=float(r[3]),
            c=float(r[4]),
            v=float(r[5]),
        )


class MultiTfBars:
    """По одному билдеру на каждый TF."""

    def __init__(self, tf_seconds: Dict[str, int], exchange: str = "", max_bars: int = 500):
        self._builders = {
            tf: OhlcvBuilder(tf, sec, exchange, max_bars) for tf, sec in tf_seconds.items()
        }

    def on_trade(self, price: float, qty: float, ts_ms: int) -> None:
        for b in self._builders.values():
            b.on_trade(price, qty, ts_ms)

    def get(self, tf: str, count: int) -> List[List[float]]:
        b = self._builders.get(tf)
        return b.bars(count) if b else []

    def seed(self, tf: str, rows: List[List[float]]) -> None:
        b = self._builders.get(tf)
        if b:
            b.seed(rows)

    def clear_tf(self, tf: str) -> None:
        b = self._builders.get(tf)
        if b:
            b._bars.clear()
            b._cur = None
