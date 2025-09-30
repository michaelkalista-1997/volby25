"""REST API endpointy pro volební výsledky."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_, create_engine, func
from sqlalchemy.orm import Session, sessionmaker

from backend.db_models import AggregatedResult, Party, VoteProgress, serialize_aggregated
from config import API_CACHE_TTL_SECONDS, DATABASE_PATH

logger = logging.getLogger(__name__)

router = APIRouter()


class AggregatedResponse(BaseModel):
    minute_bucket: datetime
    scope: str
    scope_code: Optional[str]
    total_votes: int
    valid_votes: int
    turnout: float
    data: Dict[str, int]


class PartyProgressResponse(BaseModel):
    party_code: str
    party_name: str
    color: Optional[str]
    votes: int
    vote_share: float
    turnout: float
    counted_precincts: int
    total_precincts: int
    prediction: float


class TimelineResponse(BaseModel):
    minute_bucket: datetime
    parties: List[PartyProgressResponse]


def get_engine():
    """Vrátí databázový engine."""

    return create_engine(f"sqlite:///{DATABASE_PATH}", connect_args={"check_same_thread": False})


@lru_cache(maxsize=1)
def get_sessionmaker():
    """Vytvoří sessionmaker s cachováním."""

    engine = get_engine()
    return sessionmaker(bind=engine)


def cached_response(key: str, data_func):
    """Jednoduchá cache pro API odpovědi."""

    cache_storage: Dict[str, tuple] = getattr(cached_response, "_storage", {})
    if not cache_storage:
        cached_response._storage = cache_storage
    now = datetime.utcnow()
    if key in cache_storage:
        timestamp, value = cache_storage[key]
        if now - timestamp < timedelta(seconds=API_CACHE_TTL_SECONDS):
            return value
    value = data_func()
    cache_storage[key] = (now, value)
    return value


@router.get("/aggregated", response_model=List[AggregatedResponse])
def get_aggregated(scope: str = Query("country"), scope_code: Optional[str] = Query("CZ")):
    """Vrátí agregovaná data."""

    def data_func():
        SessionLocal = get_sessionmaker()
        with SessionLocal() as session:
            query = session.query(AggregatedResult).filter(AggregatedResult.scope == scope)
            if scope_code:
                query = query.filter(AggregatedResult.scope_code == scope_code)
            query = query.order_by(AggregatedResult.minute_bucket.asc())
            return [serialize_aggregated(row) for row in query.all()]

    results = cached_response(f"aggregated:{scope}:{scope_code}", data_func)
    return results


@router.get("/progress", response_model=TimelineResponse)
def get_progress(
    minute: Optional[datetime] = Query(None), scope: str = Query("country"), scope_code: Optional[str] = Query("CZ")
):
    """Vrátí průběh pro vybranou minutu."""

    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        if minute is None:
            minute = (
                session.query(func.max(VoteProgress.minute_bucket))
                .filter(VoteProgress.scope == scope, VoteProgress.scope_code == scope_code)
                .scalar()
            )
            if minute is None:
                raise HTTPException(status_code=404, detail="No data available")

        progress_rows = (
            session.query(VoteProgress, Party)
            .join(Party, Party.id == VoteProgress.party_id)
            .filter(
                VoteProgress.minute_bucket == minute,
                VoteProgress.scope == scope,
                VoteProgress.scope_code == scope_code,
            )
            .all()
        )
        if not progress_rows:
            raise HTTPException(status_code=404, detail="No data for selected minute")

        parties = []
        for progress, party in progress_rows:
            counted_share = (
                progress.counted_precincts / progress.total_precincts if progress.total_precincts else 0.0
            )
            prediction = progress.vote_share + (100 - progress.vote_share) * counted_share * 0.5
            parties.append(
                PartyProgressResponse(
                    party_code=party.code,
                    party_name=party.name,
                    color=party.color,
                    votes=progress.votes,
                    vote_share=progress.vote_share,
                    turnout=progress.turnout,
                    counted_precincts=progress.counted_precincts,
                    total_precincts=progress.total_precincts,
                    prediction=prediction,
                )
            )

        return TimelineResponse(minute_bucket=minute, parties=parties)


@router.get("/summary")
def get_summary(scope: str = Query("country"), scope_code: Optional[str] = Query("CZ")):
    """Základní přehled pro dashboard."""

    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        latest_minute = (
            session.query(func.max(AggregatedResult.minute_bucket))
            .filter(AggregatedResult.scope == scope, AggregatedResult.scope_code == scope_code)
            .scalar()
        )
        if not latest_minute:
            raise HTTPException(status_code=404, detail="No aggregated data")

        aggregated = (
            session.query(AggregatedResult)
            .filter(
                AggregatedResult.minute_bucket == latest_minute,
                AggregatedResult.scope == scope,
                AggregatedResult.scope_code == scope_code,
            )
            .one()
        )
        counted = 0
        total = 0
        progress = (
            session.query(func.max(VoteProgress.counted_precincts), func.max(VoteProgress.total_precincts))
            .filter(
                VoteProgress.minute_bucket == latest_minute,
                VoteProgress.scope == scope,
                VoteProgress.scope_code == scope_code,
            )
            .one()
        )
        if progress:
            counted, total = progress

        return {
            "minute_bucket": latest_minute,
            "total_votes": aggregated.total_votes,
            "valid_votes": aggregated.valid_votes,
            "turnout": aggregated.turnout,
            "counted_precincts": counted or 0,
            "total_precincts": total or 0,
            "party_votes": aggregated.data,
        }


@router.get("/export")
def export_data(format: str = Query("json")):
    """Exportuje agregovaná data."""

    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        data = (
            session.query(AggregatedResult.minute_bucket, AggregatedResult.scope, AggregatedResult.scope_code, AggregatedResult.data)
            .order_by(AggregatedResult.minute_bucket.asc())
            .all()
        )
        if format == "json":
            return [
                {
                    "minute_bucket": row[0],
                    "scope": row[1],
                    "scope_code": row[2],
                    "data": row[3],
                }
                for row in data
            ]
        if format == "csv":
            import csv
            from io import StringIO

            buffer = StringIO()
            writer = csv.writer(buffer)
            writer.writerow(["minute_bucket", "scope", "scope_code", "party_code", "votes"])
            for row in data:
                minute_bucket, scope_value, scope_code_value, data_dict = row
                for party_code, votes in (data_dict or {}).items():
                    writer.writerow([minute_bucket, scope_value, scope_code_value, party_code, votes])
            buffer.seek(0)
            return buffer.getvalue()

        raise HTTPException(status_code=400, detail="Unsupported format")
