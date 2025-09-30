"""Proces pro sběr volebních dat."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from itertools import cycle
from typing import Dict, Iterable, List

import requests
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from requests import Response
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.aggregator import run_aggregator
from backend.db_models import Base, RawData
from config import (
    BATCH_ENDPOINTS,
    DATA_SOURCES,
    DATABASE_PATH,
    FETCH_INTERVAL_SECONDS,
    LOG_DIR,
)

logger = logging.getLogger(__name__)


def build_engine():
    """Vytvoří databázový engine."""

    return create_engine(f"sqlite:///{DATABASE_PATH}", connect_args={"check_same_thread": False})


def setup_database(engine) -> None:
    """Vytvoří tabulky a inicializuje databázi."""

    Base.metadata.create_all(engine)


def iter_sources() -> Iterable[str]:
    """Generátor všech zdrojů pro stahování."""

    batch_numbers = (f"{i:05d}" for i in range(1, 51))
    district_codes = [
        "CZ0100",
        "CZ0201",
        "CZ0319",
        "CZ0645",
    ]

    sources: List[str] = list(DATA_SOURCES.values())
    sources.extend(BATCH_ENDPOINTS["district_detail"].format(code=code) for code in district_codes)
    for batch in batch_numbers:
        sources.extend(
            BATCH_ENDPOINTS[key].format(batch=batch)
            for key in ("district", "municipality", "county")
        )
    return cycle(sources)


def fetch_url(url: str) -> Response:
    """Stáhne obsah URL s ošetřením chyb."""

    logger.debug("Stahuji %s", url)
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response
    except requests.RequestException as exc:
        logger.warning("Nelze stáhnout %s: %s", url, exc)
        raise


def store_raw(session_factory, source: str, content: str) -> None:
    """Uloží surová data do databáze."""

    SessionLocal = session_factory
    with SessionLocal() as session:
        entry = RawData(source=source, fetched_at=datetime.utcnow(), xml_content=content)
        session.add(entry)
        session.commit()
        logger.debug("Uložena data ze zdroje %s", source)


async def collect_loop(session_factory) -> None:
    """Hlavní smyčka sběru dat."""

    source_iterator = iter_sources()
    for source in source_iterator:
        try:
            response = fetch_url(source)
            store_raw(session_factory, source, response.text)
        except Exception:  # pylint: disable=broad-except
            logger.info("Použiji lokální data pro zdroj %s", source)
        await asyncio.sleep(FETCH_INTERVAL_SECONDS)


async def schedule_aggregation(loop, interval: int) -> None:
    """Plánovač spouštění agregace."""

    scheduler = AsyncIOScheduler(event_loop=loop)
    scheduler.add_job(run_aggregator, "interval", seconds=interval, next_run_time=datetime.utcnow())
    scheduler.start()


async def main() -> None:
    """Vstupní bod collector procesu."""

    LOG_DIR.mkdir(exist_ok=True)
    engine = build_engine()
    setup_database(engine)
    session_factory = sessionmaker(bind=engine)

    loop = asyncio.get_event_loop()
    await schedule_aggregation(loop, interval=30)

    await collect_loop(session_factory)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(LOG_DIR / "collector.log"),
            logging.StreamHandler(),
        ],
    )
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Collector ukončen uživatelem")
