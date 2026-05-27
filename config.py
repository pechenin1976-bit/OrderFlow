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

# License server (тот же ключ, что выдаёт @quantilan_bot)
LICENSE_SERVER_URL = os.getenv("ORDERFLOW_LICENSE_SERVER_URL", "http://127.0.0.1:8000")
LICENSE_SERVICE_TOKEN = os.getenv("ORDERFLOW_LICENSE_SERVICE_TOKEN", "")
LICENSE_CACHE_SEC = int(os.getenv("ORDERFLOW_LICENSE_CACHE_SEC", "60"))
LICENSE_VALIDATE = os.getenv("ORDERFLOW_LICENSE_VALIDATE", "true").lower() in (
    "1",
    "true",
    "yes",
)
CORS_ENABLED = os.getenv("ORDERFLOW_CORS", "true").lower() in ("1", "true", "yes")

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

# Как agent/agent/coins.py::_BUILTIN_COINS (top-30+ дефолт агента)
DEFAULT_SYMBOLS = [
    "BTC", "ETH", "BNB", "SOL", "XRP", "DOGE", "ADA", "AVAX", "TRX", "DOT",
    "LINK", "POL", "LTC", "BCH", "NEAR", "APT", "UNI", "ICP", "ARB", "OP",
    "INJ", "SUI", "ATOM", "HBAR", "AAVE", "TON", "ETC", "LDO", "ENA", "PEPE",
    "TIA", "TAO", "ONDO",
]

# Маппинги coin → биржевое имя (agent/exchanges.json)
_SCALED_1000 = {
    "PEPE": "1000PEPE",
    "BONK": "1000BONK",
    "SHIB": "1000SHIB",
    "FLOKI": "1000FLOKI",
    "LUNC": "1000LUNC",
}
BINANCE_SYMBOL_MAP = dict(_SCALED_1000)
BYBIT_SYMBOL_MAP = dict(_SCALED_1000)
HYPERLIQUID_SYMBOL_MAP = {
    "PEPE": "kPEPE",
    "BONK": "kBONK",
    "SHIB": "kSHIB",
    "FLOKI": "kFLOKI",
    "LUNC": "kLUNC",
}
OKX_SYMBOL_MAP: dict[str, str] = {}

# Spot: нет масштабирования 1000x (PEPE торгуется как PEPEUSDT на споте)
BINANCE_SPOT_SYMBOL_MAP: dict[str, str] = {}
BYBIT_SPOT_SYMBOL_MAP: dict[str, str] = {}
OKX_SPOT_SYMBOL_MAP: dict[str, str] = {}

BYBIT_WS_SUB_BATCH = 10
DEFAULT_TF = "15m"
SNAPSHOT_BARS = int(os.getenv("ORDERFLOW_SNAPSHOT_BARS", "11"))
DEFAULT_BARS_COUNT = SNAPSHOT_BARS
# Профиль ликвидности: ±N% от цены (UI: 0.8 / 2.5 / 4 — ~20% уже 1/3/5)
PROFILE_RANGE_PCT = float(os.getenv("ORDERFLOW_PROFILE_RANGE_PCT", "0.8"))
PROFILE_RANGE_CHOICES = (0.8, 2.5, 4.0)
PROFILE_STEPS = int(os.getenv("ORDERFLOW_PROFILE_STEPS", "10"))
BOOK_DEPTH_LEVELS = 50

# Композиция зон ликвидности
BAND_BPS = float(os.getenv("ORDERFLOW_BAND_BPS", "5.0"))
MIN_ZONE_VOL = float(os.getenv("ORDERFLOW_MIN_ZONE_VOL", "0.0"))
TOP_ZONES_PER_SIDE = int(os.getenv("ORDERFLOW_TOP_ZONES", "15"))
