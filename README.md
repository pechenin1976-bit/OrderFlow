# OrderFlow

Multi-exchange order flow and liquidity density for [Quantilan](https://quantilan.com).

- **Ingest:** public WebSocket only (trades + order book) — Binance, Bybit, Hyperliquid, OKX
- **Compose:** local L2 → liquidity zones + OHLCV from trades
- **Out:** REST snapshot every ~2s for the website (license key from `@quantilan_bot`, plan `pro_orderflow`)

## Quick start

```bash
cd OrderFlow
uv sync
cp .env.example .env
# ORDERFLOW_LICENSE_SERVICE_TOKEN = same as license server SERVICE_TOKEN
# ORDERFLOW_API_KEYS = dev bypass (optional)
uv run orderflow_core.py
```

API:

```bash
# dev token OR license key ABC1-DEF2-...
curl -H "Authorization: Bearer dev-token-change-me" \
  "http://127.0.0.1:8080/api/v1/snapshot?symbol=BTC&tf=15m"
```

### License server

1. Deploy plan `pro_orderflow` (already in `server/resources/product.py`).
2. Set `SERVICE_TOKEN` in license server `.env` and `ORDERFLOW_LICENSE_SERVICE_TOKEN` in OrderFlow `.env`.
3. User: `/subscribe` in bot → **Pro — OrderFlow** → paste key on [orderflow.html](https://quantilan.com/orderflow.html).

## Deploy

### First deploy

```bash
git clone git@github.com:pechenin1976-bit/OrderFlow.git /tmp/OrderFlow
cd /tmp/OrderFlow && bash deploy/setup_vps.sh
```

The script syncs code to `/opt/orderflow`, runs `uv sync`, installs and enables the systemd unit, and restarts the service. On first run it will prompt to create `.env` if it doesn't exist.

```bash
# Minimum .env
ORDERFLOW_LICENSE_SERVICE_TOKEN=<same as SERVICE_TOKEN in license server>
ORDERFLOW_LICENSE_SERVER_URL=http://127.0.0.1:8000
ORDERFLOW_API_KEYS=dev-token-change-me
```

### Update

```bash
cd /tmp/OrderFlow && git pull && bash deploy/setup_vps.sh
```

`.env` and `settings/` are never overwritten by the script.

### nginx

See `deploy/nginx-orderflow.conf.example` — proxies `/api/orderflow/` → `127.0.0.1:8080`.

### Logs

```bash
sudo journalctl -u orderflow -f
sudo systemctl status orderflow
```

- Site: `quantilan/www/orderflow.html` polls `/api/orderflow/snapshot` via reverse proxy

## Signals (optional)

`ORDERFLOW_SEND_SIGNALS=true` → Unix socket `/tmp/signals.sock` (same as CrCraft / SignalsHub).
