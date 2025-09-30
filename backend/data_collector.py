"""Proces pro kontinuální stahování XML dat."""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Iterable

import requests
from requests import Response

from backend.aggregator import DataAggregator
from backend.db_models import RawData, SessionLocal, init_db
from config import BATCH_RANGE, FETCH_INTERVAL_SECONDS, REQUEST_TIMEOUT, XML_SOURCES

logger = logging.getLogger(__name__)


class DataCollector:
    """Stahuje data z volby.cz a ukládá je do databáze."""

    def __init__(self) -> None:
        init_db()
        self.aggregator = DataAggregator()

    def run(self) -> None:
        """Spustí nekonečnou smyčku stahování."""

        logger.info("Spouštím datový kolektor")
        while True:
            for url in self._iter_urls():
                try:
                    response = self._fetch(url)
                    self._store_response(url, response)
                except Exception as exc:  # pylint: disable=broad-exception-caught  # Potlačení kvůli robustnosti
                    logger.warning("Chyba při zpracování %s: %s", url, exc)
                time.sleep(FETCH_INTERVAL_SECONDS)

    def _iter_urls(self) -> Iterable[str]:
        """Vygeneruje seznam URL pro aktuální cyklus."""

        for url in XML_SOURCES.values():
            yield url

        for batch in BATCH_RANGE:
            suffix = str(batch).zfill(5)
            yield f"https://volby.cz/appdata/ps2025/odata/okrsky/vysledky_okrsky_{suffix}.xml"
            yield f"https://volby.cz/appdata/ps2025/odata/obce_d/vysledky_obce_{suffix}.xml"
            yield f"https://volby.cz/appdata/ps2025/odata/okresy_d/vysledky_okresy_{suffix}.xml"

    def _fetch(self, url: str) -> Response:
        """Stáhne data a ošetří chyby."""

        logger.debug("Stahuji %s", url)
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response

    def _store_response(self, url: str, response: Response) -> None:
        """Uloží XML do databáze a spustí agregaci."""

        xml_text = response.text
        with SessionLocal() as session:
            raw = RawData(source_url=url, fetched_at=datetime.utcnow(), xml_content=xml_text)
            session.add(raw)
            session.commit()
            session.refresh(raw)

        self.aggregator.process_raw_record(raw)


def main() -> None:
    """Vstupní bod pro samostatné spuštění kolektoru."""

    collector = DataCollector()
    collector.run()


if __name__ == "__main__":
    main()
