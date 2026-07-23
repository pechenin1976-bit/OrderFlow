"""Startup validation — no dev bypass in production."""
from __future__ import annotations

import logging
import os
import sys

import config

logger = logging.getLogger(__name__)

_DEV_TOKEN = "dev-token-change-me"


def allow_insecure_dev() -> bool:
    return os.getenv("ORDERFLOW_ALLOW_INSECURE_DEV", "false").lower() in ("1", "true", "yes")


def validate_startup_config() -> None:
    if allow_insecure_dev():
        logger.warning("[Security] ORDERFLOW_ALLOW_INSECURE_DEV=true — relaxed checks")
        return

    errors: list[str] = []
    if _DEV_TOKEN in config.API_KEYS:
        errors.append("Remove dev-token-change-me from ORDERFLOW_API_KEYS in production")
    if config.LICENSE_VALIDATE and not config.LICENSE_SERVICE_TOKEN:
        errors.append("ORDERFLOW_LICENSE_SERVICE_TOKEN is required when license validation is enabled")

    if errors:
        for msg in errors:
            logger.critical("[Security] %s", msg)
        sys.exit(
            "Refusing to start OrderFlow: insecure configuration. "
            "Set ORDERFLOW_ALLOW_INSECURE_DEV=true for local dev only."
        )
