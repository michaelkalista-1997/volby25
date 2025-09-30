"""Spouštěcí skript pro webovou aplikaci."""

import logging.config

from config import LOGGING_CONFIG
from webapp.app import main as webapp_main

logging.config.dictConfig(LOGGING_CONFIG)  # type: ignore[attr-defined]

if __name__ == "__main__":
    webapp_main()
