"""REST API endpointy pro aplikaci."""

from __future__ import annotations

import csv
import io
import logging
from time import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import and_

from backend.db_models import AggregatedResult, SessionLocal, VoteProgress

logger = logging.getLogger(__name__)


class SimpleCache:
    """Jednoduchá cache pro snížení zátěže databáze."""

    def __init__(self, default_ttl: int = 5) -> None:
        self.default_ttl = default_ttl
        self._store: Dict[str, Dict[str, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        """Vrátí hodnotu z cache pokud je platná."""

        record = self._store.get(key)
        if not record:
            return None
        if record["expires"] < time():
            self._store.pop(key, None)
            return None
        return record["value"]

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Uloží hodnotu do cache."""

        self._store[key] = {
            "value": value,
            "expires": time() + (ttl or self.default_ttl),
        }


cache = SimpleCache()
router = APIRouter(prefix="/api")


@router.get("/dashboard")
def get_dashboard(
    scope_type: str = Query("nation"),
    scope_code: str = Query("CZ"),
    limit: int = Query(240, ge=1, le=1440),
) -> Dict[str, Any]:
    """Vrací agregovaná data pro hlavní dashboard."""

    cache_key = f"dashboard:{scope_type}:{scope_code}:{limit}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    with SessionLocal() as session:
        query = (
            session.query(AggregatedResult)
            .filter(
                and_(
                    AggregatedResult.scope_type == scope_type,
                    AggregatedResult.scope_code == scope_code,
                )
            )
            .order_by(AggregatedResult.interval_start.desc())
            .limit(limit)
        )
        results: List[AggregatedResult] = list(reversed(query.all()))

    if not results:
        raise HTTPException(status_code=404, detail="No data available")

    timeline = [
        {
            "interval_start": item.interval_start.isoformat(),
            "data": item.data,
        }
        for item in results
    ]
    payload = {"timeline": timeline}
    cache.set(cache_key, payload)
    return payload


@router.get("/progress")
def get_progress(
    scope_type: str = Query("nation"),
    scope_code: str = Query("CZ"),
    limit: int = Query(240, ge=1, le=1440),
) -> Dict[str, Any]:
    """Vrací vývoj sčítání pro zvolený region."""

    cache_key = f"progress:{scope_type}:{scope_code}:{limit}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    with SessionLocal() as session:
        query = (
            session.query(VoteProgress)
            .filter(
                and_(
                    VoteProgress.scope_type == scope_type,
                    VoteProgress.scope_code == scope_code,
                )
            )
            .order_by(VoteProgress.interval_start.desc())
            .limit(limit)
        )
        results: List[VoteProgress] = list(reversed(query.all()))

    if not results:
        raise HTTPException(status_code=404, detail="No progress data available")

    data = [
        {
            "interval_start": item.interval_start.isoformat(),
            "counted_units": item.counted_units,
            "total_units": item.total_units,
            "total_votes": item.total_votes,
            "turnout": item.turnout,
            "speed_per_hour": item.speed_per_hour,
            "prediction": item.prediction,
        }
        for item in results
    ]
    payload = {"progress": data}
    cache.set(cache_key, payload)
    return payload


@router.get("/export")
def export_data(
    scope_type: str = Query("nation"),
    scope_code: str = Query("CZ"),
    format: str = Query("json"),
) -> StreamingResponse | JSONResponse:
    """Exportuje data do JSON nebo CSV."""

    with SessionLocal() as session:
        query = (
            session.query(AggregatedResult)
            .filter(
                and_(
                    AggregatedResult.scope_type == scope_type,
                    AggregatedResult.scope_code == scope_code,
                )
            )
            .order_by(AggregatedResult.interval_start.asc())
        )
        results: List[AggregatedResult] = query.all()

    if format == "json":
        payload = [
            {
                "interval_start": item.interval_start.isoformat(),
                "data": item.data,
            }
            for item in results
        ]
        return JSONResponse(content=payload)

    if format == "csv":
        stream = io.StringIO()
        writer = csv.writer(stream)
        writer.writerow(["interval_start", "scope_type", "scope_code", "total_votes"])
        for item in results:
            writer.writerow(
                [
                    item.interval_start.isoformat(),
                    item.scope_type,
                    item.scope_code,
                    item.data.get("total_votes", 0) if isinstance(item.data, dict) else 0,
                ]
            )
        stream.seek(0)
        headers = {"Content-Disposition": "attachment; filename=export.csv"}
        return StreamingResponse(iter([stream.getvalue()]), media_type="text/csv", headers=headers)

    raise HTTPException(status_code=400, detail="Unsupported format")
