"""Agregace volebních dat do minutových intervalů."""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Tuple

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.db_models import AggregatedResult, Base, Party, RawData, VoteProgress
from backend.xml_parser import parse_vote_data
from config import DATABASE_PATH, PREDICTION_DECAY, PREDICTION_MIN_PROGRESS

logger = logging.getLogger(__name__)


def get_engine():
    """Vrátí SQLAlchemy engine."""

    return create_engine(f"sqlite:///{DATABASE_PATH}", connect_args={"check_same_thread": False})


def ensure_tables(engine) -> None:
    """Vytvoří tabulky, pokud neexistují."""

    Base.metadata.create_all(engine)


def bucket_minute(timestamp: datetime | None) -> datetime:
    """Zaokrouhlí čas na začátek minuty."""

    if timestamp is None:
        timestamp = datetime.utcnow()
    return timestamp.replace(second=0, microsecond=0)


def accumulate_party_info(
    party_votes: Dict[str, int], party_names: Dict[str, str], session: Session
) -> Dict[str, Party]:
    """Zajistí existenci záznamů stran."""

    party_objects: Dict[str, Party] = {}
    for code, votes in party_votes.items():
        party = session.query(Party).filter_by(code=code).one_or_none()
        if not party:
            party = Party(code=code, name=party_names.get(code, f"Party {code}"))
            session.add(party)
            session.flush()
        elif party_names.get(code) and party.name != party_names[code]:
            party.name = party_names[code]
        party_objects[code] = party
    return party_objects


def compute_prediction(progress_share: float, current_share: float) -> float:
    """Jednoduchá predikce výsledku."""

    if progress_share < PREDICTION_MIN_PROGRESS:
        return current_share
    return current_share + (1 - progress_share) * current_share * (1 - PREDICTION_DECAY)


def aggregate_single(raw: RawData, session: Session) -> Tuple[datetime, Dict[str, int], Dict[str, str], int, int, float]:
    """Agreguje jednu dávku surových dat."""

    parsed = parse_vote_data(raw.xml_content)
    minute = bucket_minute(parsed.get("timestamp") or raw.fetched_at)
    return (
        minute,
        parsed.get("party_votes", {}),
        parsed.get("party_names", {}),
        parsed.get("counted_precincts", 0),
        parsed.get("total_precincts", 0),
        parsed.get("turnout", 0.0),
    )


def merge_party_votes(buckets: Dict[datetime, Dict[str, int]], minute: datetime, votes: Dict[str, int]) -> None:
    """Sloučí hlasy do agregovaného slovníku."""

    minute_bucket = buckets.setdefault(minute, defaultdict(int))
    for code, value in votes.items():
        minute_bucket[code] += value


def aggregate_data(session: Session) -> None:
    """Agreguje nová surová data do tabulek."""

    raw_entries: List[RawData] = session.query(RawData).order_by(RawData.fetched_at.asc()).all()
    if not raw_entries:
        return

    party_totals: Dict[datetime, Dict[str, int]] = {}
    party_names: Dict[str, str] = {}
    progress_info: Dict[datetime, Tuple[int, int, float]] = {}

    for raw in raw_entries:
        minute, votes, names, counted, total, turnout = aggregate_single(raw, session)
        merge_party_votes(party_totals, minute, votes)
        party_names.update(names)
        progress_info[minute] = (
            max(progress_info.get(minute, (0, 0, 0.0))[0], counted),
            max(progress_info.get(minute, (0, 0, 0.0))[1], total),
            max(progress_info.get(minute, (0, 0, 0.0))[2], turnout),
        )

    for minute, votes in party_totals.items():
        total_votes = sum(votes.values())
        counted, total, turnout = progress_info.get(minute, (0, 0, 0.0))

        aggregated = session.query(AggregatedResult).filter_by(minute_bucket=minute, scope="country").one_or_none()
        if not aggregated:
            aggregated = AggregatedResult(
                minute_bucket=minute,
                scope="country",
                scope_code="CZ",
                total_votes=total_votes,
                valid_votes=total_votes,
                turnout=turnout,
                data={},
            )
            session.add(aggregated)
        else:
            aggregated.total_votes = total_votes
            aggregated.valid_votes = total_votes
            aggregated.turnout = turnout
        aggregated.data = {code: votes[code] for code in votes}

        parties = accumulate_party_info(votes, party_names, session)
        for code, party in parties.items():
            vote_count = votes[code]
            share = (vote_count / total_votes * 100) if total_votes else 0.0
            progress = session.query(VoteProgress).filter_by(
                minute_bucket=minute,
                scope="country",
                scope_code="CZ",
                party_id=party.id,
            ).one_or_none()
            if not progress:
                progress = VoteProgress(
                    minute_bucket=minute,
                    scope="country",
                    scope_code="CZ",
                    party_id=party.id,
                )
                session.add(progress)
            progress.votes = vote_count
            progress.vote_share = share
            progress.turnout = turnout
            progress.counted_precincts = counted
            progress.total_precincts = total

    session.commit()


def run_aggregator() -> None:
    """Spustí agregaci a loguje průběh."""

    engine = get_engine()
    ensure_tables(engine)
    SessionLocal = sessionmaker(bind=engine)

    with SessionLocal() as session:
        try:
            aggregate_data(session)
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Chyba při agregaci dat: %s", exc)
            session.rollback()
        finally:
            # Mazání starých raw dat po zpracování
            session.query(RawData).delete()
            session.commit()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_aggregator()
