"""WebSocket pro real-time aktualizace."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

from backend.db_models import AggregatedResult
from config import DATABASE_PATH, WEBSOCKET_UPDATE_INTERVAL

logger = logging.getLogger(__name__)

router = APIRouter()


engine = create_engine(f"sqlite:///{DATABASE_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)


async def fetch_latest_summary(scope: str, scope_code: str | None) -> Dict[str, object]:
    """Načte poslední shrnutí."""

    with SessionLocal() as session:
        latest_minute = (
            session.query(func.max(AggregatedResult.minute_bucket))
            .filter(AggregatedResult.scope == scope, AggregatedResult.scope_code == scope_code)
            .scalar()
        )
        if not latest_minute:
            return {}
        aggregated = (
            session.query(AggregatedResult)
            .filter(
                AggregatedResult.minute_bucket == latest_minute,
                AggregatedResult.scope == scope,
                AggregatedResult.scope_code == scope_code,
            )
            .one()
        )
        return {
            "minute_bucket": aggregated.minute_bucket.isoformat(),
            "total_votes": aggregated.total_votes,
            "valid_votes": aggregated.valid_votes,
            "turnout": aggregated.turnout,
            "party_votes": aggregated.data,
        }


@router.websocket("/ws/summary")
async def summary_socket(websocket: WebSocket, scope: str = "country", scope_code: str | None = "CZ"):
    """Posílá pravidelné aktualizace dashboardu."""

    await websocket.accept()
    try:
        while True:
            payload = await fetch_latest_summary(scope, scope_code)
            await websocket.send_text(json.dumps(payload))
            await asyncio.sleep(WEBSOCKET_UPDATE_INTERVAL)
    except WebSocketDisconnect:
        logger.info("WebSocket summary odpojen")
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Chyba ve WebSocket: %s", exc)
        await websocket.close()
