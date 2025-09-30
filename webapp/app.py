"""Inicializace FastAPI aplikace."""
from __future__ import annotations

import logging
from functools import lru_cache

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from webapp.api_routes import router as api_router
from webapp.websocket import router as websocket_router

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Vytvoří FastAPI aplikaci."""

    app = FastAPI(title="Czech Elections 2025", version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api")
    app.include_router(websocket_router)

    app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
    templates = Jinja2Templates(directory="frontend/templates")

    @app.get("/")
    async def index(request):  # type: ignore[override]
        """Vrátí hlavní dashboard."""

        return templates.TemplateResponse("index.html", {"request": request})

    return app


app = create_app()
