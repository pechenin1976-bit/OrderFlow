#!/usr/bin/env python3
"""OrderFlow — multi-exchange order book + liquidity zones → REST snapshots."""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

import config
from src.api.server import start_api
from src.collectors.registry import start_all
from src.funding.poller import funding_loop
from src.history.bootstrap import seed_all
from src.snapshot.publisher import publish_loop
from src.state.market_state import MarketState

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("orderflow")


def load_settings(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


async def main_async(settings: dict) -> None:
    symbols = settings.get("symbols", config.DEFAULT_SYMBOLS)
    exchanges = settings.get("exchanges", ["binance", "bybit", "hyperliquid", "okx"])
    default_tf = settings.get("default_tf", config.DEFAULT_TF)

    state = MarketState(symbols)
    from src.symbols.volume_rank import get_volumes

    await get_volumes(symbols)
    await seed_all(state, symbols, exchanges, default_tf)
    collector_tasks = start_all(state, symbols, enabled=exchanges)
    publisher_task = asyncio.create_task(publish_loop(state, default_tf))
    funding_task = asyncio.create_task(funding_loop(state))
    api_runner = await start_api(state)

    logger.info("OrderFlow running | symbols=%s exchanges=%s", symbols, exchanges)
    try:
        await asyncio.gather(*collector_tasks, publisher_task, funding_task)
    finally:
        for t in collector_tasks:
            t.cancel()
        publisher_task.cancel()
        funding_task.cancel()
        await api_runner.cleanup()


def main() -> None:
    parser = argparse.ArgumentParser(description="OrderFlow service")
    parser.add_argument(
        "--settings",
        default=str(config.SETTINGS_DIR / "settings_orderflow.json"),
        help="Path to settings JSON",
    )
    args = parser.parse_args()
    settings = load_settings(Path(args.settings))
    try:
        asyncio.run(main_async(settings))
    except KeyboardInterrupt:
        logger.info("shutdown")


if __name__ == "__main__":
    main()
