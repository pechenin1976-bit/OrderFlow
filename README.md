# OrderFlow

Multi-exchange order flow and liquidity density for [Quantilan](https://quantilan.com).

- **Ingest:** public WebSocket only (trades + order book) — Binance, Bybit, Hyperliquid, OKX
- **Compose:** local L2 → liquidity zones + OHLCV from trades
- **Out:** REST snapshot every ~2s for the website (Bearer token)

## Quick start

```bash
cd OrderFlow
uv sync
cp .env.example .env
# edit ORDERFLOW_API_KEYS
uv run orderflow_core.py
```

API:

```bash
curl -H "Authorization: Bearer dev-token-change-me" \
  "http://127.0.0.1:8080/api/v1/snapshot?symbol=BTC&tf=15m"
```

## Deploy

- VPS: `deploy/orderflow.service`, `deploy/nginx-orderflow.conf.example`
- Site: `quantilan/www/orderflow.html` polls `/api/orderflow/snapshot` via reverse proxy

## Signals (optional)

`ORDERFLOW_SEND_SIGNALS=true` → Unix socket `/tmp/signals.sock` (same as CrCraft / SignalsHub).
