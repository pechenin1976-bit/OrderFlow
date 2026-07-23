# OrderFlow API — Security

## Threat model

Liquidity dashboard backend. License keys in `Authorization: Bearer` header.

## Hardening

- Binds `127.0.0.1:8080` by default — nginx reverse proxy only.
- No `dev-token-change-me` in production (`ORDERFLOW_ALLOW_INSECURE_DEV` for local dev only).
- `ORDERFLOW_LICENSE_SERVICE_TOKEN` required when license validation enabled.
- CORS whitelist: `ORDERFLOW_CORS_ORIGINS` (default quantilan.com).
- `refresh=1` rate-limited per token.
- License keys **not** accepted in URL query (`?token=` removed).

## Reporting

security@quantilan.com
