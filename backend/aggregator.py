"""Logika pro agregaci dat do minutových intervalů."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, Iterable, Tuple

from sqlalchemy.orm import Session

from backend import xml_parser
from backend.db_models import (
    AggregatedResult,
    RawData,
    SessionLocal,
    VoteProgress,
    save_json,
)
from config import PREDICTION_MIN_COMPLETION

logger = logging.getLogger(__name__)


def truncate_to_minute(ts: datetime) -> datetime:
    """Zaokrouhlí čas na začátek minuty."""

    return ts.replace(second=0, microsecond=0)


class DataAggregator:
    """Agregátor zodpovědný za výpočet metrik."""

    def __init__(self) -> None:
        self._last_speed_checkpoint: Dict[Tuple[str, str], Tuple[datetime, int]] = {}

    def process_raw_record(self, raw: RawData) -> None:
        """Zpracuje surový záznam a uloží agregovaná data."""

        with SessionLocal() as session:
            try:
                snapshot = xml_parser.parse_snapshot(raw.xml_content)
            except Exception as exc:  # pylint: disable=broad-exception-caught  # Potlačení kvůli robustnosti
                logger.exception("Nepodařilo se zpracovat XML: %s", exc)
                return

            minute = truncate_to_minute(raw.fetched_at)
            self._store_aggregated(session, raw, minute, snapshot)
            session.commit()

    def _store_aggregated(
        self,
        session: Session,
        raw: RawData,
        minute: datetime,
        snapshot: xml_parser.ElectionSnapshot,
    ) -> None:
        """Uloží agregovaná data a statistiky."""

        aggregated_payload = {
            "parties": [party.to_dict() for party in snapshot.parties],
            "total_votes": snapshot.total_votes,
            "scope_type": snapshot.scope_type,
            "scope_code": snapshot.scope_code,
            "updated_at": raw.fetched_at.isoformat(),
        }

        aggregated = AggregatedResult(
            raw_id=raw.id,
            interval_start=minute,
            scope_type=snapshot.scope_type,
            scope_code=snapshot.scope_code,
            data=save_json(session, aggregated_payload),
        )
        session.add(aggregated)

        progress_payload = self._compute_progress(minute, snapshot)
        progress = VoteProgress(
            interval_start=minute,
            scope_type=snapshot.scope_type,
            scope_code=snapshot.scope_code,
            counted_units=snapshot.counted_units,
            total_units=snapshot.total_units,
            total_votes=snapshot.total_votes,
            turnout=snapshot.turnout,
            speed_per_hour=progress_payload["speed_per_hour"],
            prediction=save_json(session, progress_payload["prediction"]),
        )
        session.add(progress)

    def _compute_progress(self, minute: datetime, snapshot: xml_parser.ElectionSnapshot) -> Dict[str, object]:
        """Spočítá pomocné statistiky pro vývoj sčítání."""

        key = (snapshot.scope_type, snapshot.scope_code)
        counted = snapshot.counted_units or 0

        speed_per_hour = None
        last_checkpoint = self._last_speed_checkpoint.get(key)
        if last_checkpoint:
            last_time, last_counted = last_checkpoint
            delta_minutes = max((minute - last_time).total_seconds() / 60.0, 1)
            speed_per_hour = int(((counted - last_counted) / delta_minutes) * 60) if counted >= last_counted else None

        self._last_speed_checkpoint[key] = (minute, counted)

        prediction = self._compute_prediction(snapshot)
        return {
            "speed_per_hour": speed_per_hour,
            "prediction": prediction,
        }

    def _compute_prediction(self, snapshot: xml_parser.ElectionSnapshot) -> Dict[str, object]:
        """Vytvoří jednoduchou predikci na základě podílu sečtených okrsků."""

        if not snapshot.total_units or not snapshot.counted_units:
            return {"status": "insufficient"}

        completion = snapshot.counted_units / snapshot.total_units
        if completion < PREDICTION_MIN_COMPLETION:
            return {"status": "insufficient"}

        scale = 1 / completion
        predicted_parties = {
            party.code: round(party.votes * scale)
            for party in snapshot.parties
        }
        return {
            "status": "projected",
            "completion": round(completion, 3),
            "predicted_votes": predicted_parties,
        }


def aggregate_missing() -> None:
    """Zpracuje všechna surová data, pro která ještě neexistují agregace."""

    aggregator = DataAggregator()
    with SessionLocal() as session:
        raw_items: Iterable[RawData] = (
            session.query(RawData)
            .outerjoin(AggregatedResult)
            .filter(AggregatedResult.id.is_(None))
            .all()
        )

    for raw in raw_items:
        aggregator.process_raw_record(raw)
