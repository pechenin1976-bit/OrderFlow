"""Имена инструментов на биржах (как agent/exchanges.json symbol_map)."""
from __future__ import annotations

from typing import Dict

import config
from src.collectors.base import symbol_to_usdt

# coin → имя на бирже (без USDT)
_MAPS: Dict[str, Dict[str, str]] = {
    "binance": getattr(config, "BINANCE_SYMBOL_MAP", {}),
    "binance_spot": getattr(config, "BINANCE_SPOT_SYMBOL_MAP", {}),
    "bybit": getattr(config, "BYBIT_SYMBOL_MAP", {}),
    "bybit_spot": getattr(config, "BYBIT_SPOT_SYMBOL_MAP", {}),
    "hyperliquid": getattr(config, "HYPERLIQUID_SYMBOL_MAP", {}),
    "okx": getattr(config, "OKX_SYMBOL_MAP", {}),
    "okx_spot": getattr(config, "OKX_SPOT_SYMBOL_MAP", {}),
}

_REVERSE: Dict[str, Dict[str, str]] = {
    ex: {v.upper(): k.upper() for k, v in m.items()} for ex, m in _MAPS.items()
}


def native_coin(exchange: str, symbol: str) -> str:
    """Имя монеты на бирже: PEPE → 1000PEPE / KPEPE."""
    m = _MAPS.get(exchange, {})
    return m.get(symbol.upper(), symbol.upper())


def usdt_instrument(exchange: str, symbol: str) -> str:
    """Futures-тикер с USDT: PEPE → 1000PEPEUSDT (Binance/Bybit)."""
    return symbol_to_usdt(native_coin(exchange, symbol))


def okx_inst_id(symbol: str) -> str:
    base = native_coin("okx", symbol)
    return f"{base}-USDT-SWAP"


def okx_spot_inst_id(symbol: str) -> str:
    base = native_coin("okx_spot", symbol)
    return f"{base}-USDT"


def from_native(exchange: str, native: str) -> str:
    """Биржевое имя → наш символ (BTC, PEPE, …)."""
    raw = native.upper()
    if exchange in ("binance", "bybit", "okx", "binance_spot", "bybit_spot") and raw.endswith("USDT"):
        raw = raw[:-4]
    if exchange == "okx" and raw.endswith("-SWAP"):
        raw = raw.replace("-USDT-SWAP", "").replace("-SWAP", "")
    if exchange == "okx_spot" and raw.endswith("-USDT"):
        raw = raw[:-5]
    rev = _REVERSE.get(exchange, {})
    return rev.get(raw, raw)
