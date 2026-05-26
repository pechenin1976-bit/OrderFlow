import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
SETTINGS_DIR = ROOT_DIR / "settings"

API_HOST = os.getenv("ORDERFLOW_API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("ORDERFLOW_API_PORT", "8080"))
PUBLISH_INTERVAL_SEC = float(os.getenv("ORDERFLOW_PUBLISH_INTERVAL_SEC", "2.0"))

API_KEYS = [
    k.strip()
    for k in os.getenv("ORDERFLOW_API_KEYS", "dev-token-change-me").split(",")
    if k.strip()
]

SIGNALS_SOCK = os.getenv("ORDERFLOW_SIGNALS_SOCK", "/tmp/signals.sock")
SEND_SIGNALS = os.getenv("ORDERFLOW_SEND_SIGNALS", "false").lower() in ("1", "true", "yes")

TF_SECONDS = {
    "5m": 300,
    "15m": 900,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
    "1w": 604800,
}

DEFAULT_SYMBOLS = ["BTC", "ETH", "SOL"]
DEFAULT_TF = "15m"
DEFAULT_BARS_COUNT = 120
BOOK_DEPTH_LEVELS = 50

# Композиция зон ликвидности
BAND_BPS = float(os.getenv("ORDERFLOW_BAND_BPS", "5.0"))
MIN_ZONE_VOL = float(os.getenv("ORDERFLOW_MIN_ZONE_VOL", "0.0"))
TOP_ZONES_PER_SIDE = int(os.getenv("ORDERFLOW_TOP_ZONES", "15"))
