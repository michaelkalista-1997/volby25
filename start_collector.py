"""Spouštěcí skript pro datový kolektor."""

import logging.config

from backend.data_collector import main as collector_main
from config import LOGGING_CONFIG

logging.config.dictConfig(LOGGING_CONFIG)  # type: ignore[attr-defined]

if __name__ == "__main__":
    collector_main()
