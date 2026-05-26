"""Bybit: re-export из общего маппинга."""
from __future__ import annotations

from src.symbols.instruments import from_native, usdt_instrument

instrument_id = lambda symbol: usdt_instrument("bybit", symbol)
symbol_from_instrument = lambda inst: from_native("bybit", inst)
