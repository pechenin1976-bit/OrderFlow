"""Проверка license key через Quantilan License Server."""
from __future__ import annotations

import logging
import time
from typing import Optional

import aiohttp

import config

logger = logging.getLogger(__name__)

_cache: dict[str, tuple[float, bool, int]] = {}  # key -> (mono_expires, valid, expires_at)


async def validate_license_key(key: str) -> bool:
    if not key:
        return False
    if key in config.API_KEYS:
        return True
    if not config.LICENSE_VALIDATE:
        return False

    now = time.monotonic()
    hit = _cache.get(key)
    if hit and hit[0] > now:
        return hit[1]

    ok, expires_at = await _fetch(key)
    _cache[key] = (now + config.LICENSE_CACHE_SEC, ok, expires_at)
    return ok


async def _fetch(key: str) -> tuple[bool, int]:
    url = f"{config.LICENSE_SERVER_URL.rstrip('/')}/v1/orderflow/validate"
    headers: dict[str, str] = {}
    if config.LICENSE_SERVICE_TOKEN:
        headers["X-Service-Token"] = config.LICENSE_SERVICE_TOKEN

    try:
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, params={"key": key}, headers=headers) as resp:
                if resp.status == 403:
                    logger.error(
                        "[License] 403 — задай ORDERFLOW_LICENSE_SERVICE_TOKEN "
                        "(тот же SERVICE_TOKEN, что в server/.env)"
                    )
                    return False, 0
                if resp.status != 200:
                    body = await resp.text()
                    logger.warning("[License] validate HTTP %s: %s", resp.status, body[:200])
                    return False, 0
                data = await resp.json()
    except Exception as e:
        logger.warning("[License] validate failed: %s", e)
        return False, 0

    return bool(data.get("valid")), int(data.get("expires_at") or 0)
