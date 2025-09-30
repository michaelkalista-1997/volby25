"""Konfigurace aplikace pro sledování voleb 2025."""
from pathlib import Path

# Cesty
BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "database" / "volby.db"
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# URL zdroje
DATA_SOURCES = {
    "summary": "https://volby.cz/appdata/ps2025/odata/vysledky.xml",
    "regions": "https://volby.cz/appdata/ps2025/odata/vysledky_krajmesta.xml",
    "abroad": "https://volby.cz/appdata/ps2025/odata/vysledky_zahranici.xml",
    "candidates": "https://volby.cz/appdata/ps2025/odata/vysledky_kandid.xml",
}

# Šablony pro dávková data
BATCH_ENDPOINTS = {
    "district": "https://volby.cz/appdata/ps2025/odata/okrsky/vysledky_okrsky_{batch}.xml",
    "municipality": "https://volby.cz/appdata/ps2025/odata/obce_d/vysledky_obce_{batch}.xml",
    "county": "https://volby.cz/appdata/ps2025/odata/okresy_d/vysledky_okresy_{batch}.xml",
    "district_detail": "https://volby.cz/appdata/ps2025/odata/okresy/vysledky_okres_{code}.xml",
}

# Nastavení sběru
FETCH_INTERVAL_SECONDS = 1
AGGREGATION_INTERVAL_SECONDS = 60
API_CACHE_TTL_SECONDS = 8
WEBSOCKET_UPDATE_INTERVAL = 10

# Predikční parametry
PREDICTION_MIN_PROGRESS = 0.1
PREDICTION_DECAY = 0.3
