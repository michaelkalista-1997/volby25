"""Implementace WebSocket komunikace pro dashboard."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Dict, List, Set

from fastapi import WebSocket

from backend.aggregator import aggregate_missing

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Správa otevřených WebSocket spojení."""

    def __init__(self) -> None:
        self.connections: Set[WebSocket] = set()
        self.lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        """Připojí klienta a přijme spojení."""

        await websocket.accept()
        async with self.lock:
            self.connections.add(websocket)
        logger.info("WebSocket připojen (%s klientů)", len(self.connections))

    async def disconnect(self, websocket: WebSocket) -> None:
        """Odstraní klienta z aktivních spojení."""

        async with self.lock:
            self.connections.discard(websocket)
        logger.info("WebSocket odpojen (%s klientů)", len(self.connections))

    async def broadcast(self, message: Dict) -> None:
        """Odešle zprávu všem klientům."""

        payload = json.dumps(message)
        async with self.lock:
            to_remove: List[WebSocket] = []
            for connection in self.connections:
                try:
                    await connection.send_text(payload)
                except Exception:  # pylint: disable=broad-exception-caught  # Potlačení kvůli robustnosti
                    to_remove.append(connection)
            for connection in to_remove:
                self.connections.discard(connection)

    async def pump(self) -> None:
        """Pravidelně odesílá aktualizace."""

        while True:
            await asyncio.sleep(10)
            aggregate_missing()
            await self.broadcast({"type": "refresh"})


manager = WebSocketManager()
