"""Konfigurační hodnoty pro aplikaci Volby 2025."""

from pathlib import Path

# Cesta k databázi SQLite
DATABASE_PATH = Path(__file__).resolve().parent / "database" / "volby.db"

# Interval stahování v sekundách
FETCH_INTERVAL_SECONDS = 1

# URL zdroje dat
XML_SOURCES = {
    "nation": "https://volby.cz/appdata/ps2025/odata/vysledky.xml",
    "regions": "https://volby.cz/appdata/ps2025/odata/vysledky_krajmesta.xml",
    "abroad": "https://volby.cz/appdata/ps2025/odata/vysledky_zahranici.xml",
    "candidates": "https://volby.cz/appdata/ps2025/odata/vysledky_kandid.xml",
}

# Počet dávek, které se mají stahovat pro detailní výsledky
BATCH_RANGE = range(1, 6)

# Timeout pro HTTP požadavky
REQUEST_TIMEOUT = 10

# Nastavení predikce
PREDICTION_MIN_COMPLETION = 0.25

# Nastavení logování
LOGGING_CONFIG = {
    "version": 1,
    "formatters": {
        "default": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        }
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}
