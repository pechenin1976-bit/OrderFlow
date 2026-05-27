"""Котировочный стейбл по бирже (для подписей объёма в профиле стакана)."""
from __future__ import annotations

import config

_DEFAULT = "USDT"


def quote_currency(exchange: str) -> str:
    """USDT на CEX linear/spot; USDC на Hyperliquid perps."""
    return config.EXCHANGE_QUOTE_CURRENCY.get(exchange, _DEFAULT)
