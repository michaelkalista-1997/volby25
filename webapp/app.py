"""Vstupní bod FastAPI aplikace."""

from __future__ import annotations

import asyncio
import logging
import logging.config
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from backend.db_models import init_db
from config import LOGGING_CONFIG
from webapp import api_routes
from webapp.websocket import manager

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)

app = FastAPI(title="Elections 2025 Dashboard")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

base_path = Path(__file__).resolve().parent.parent
static_path = base_path / "frontend" / "static"
templates_path = base_path / "frontend" / "templates"

app.mount("/static", StaticFiles(directory=static_path), name="static")
templates = Jinja2Templates(directory=str(templates_path))

app.include_router(api_routes.router)


@app.on_event("startup")
async def startup_event() -> None:
    """Inicializační rutina při startu serveru."""

    init_db()
    asyncio.create_task(manager.pump())


@app.get("/")
async def index(request: Request):
    """Vrací hlavní šablonu."""

    return templates.TemplateResponse("index.html", {"request": request})


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Obsluha WebSocket spojení."""

    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception:  # pylint: disable=broad-exception-caught  # Potlačení kvůli robustnosti
        pass
    finally:
        await manager.disconnect(websocket)


def main() -> None:
    """Spustí server pomocí Uvicorn."""

    uvicorn.run("webapp.app:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
