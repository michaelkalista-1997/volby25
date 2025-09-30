"""Definice databázových modelů a pomocných funkcí."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    event,
)
from sqlalchemy.engine import Engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, relationship, sessionmaker

from config import DATABASE_PATH

# Zajištění zapnutí cizích klíčů pro SQLite
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Aktivuje cizí klíče v SQLite."""

    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


engine = create_engine(f"sqlite:///{DATABASE_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


class RawData(Base):
    """Model pro ukládání surových XML dat."""

    __tablename__ = "raw_data"

    id = Column(Integer, primary_key=True)
    source_url = Column(String, nullable=False)
    fetched_at = Column(DateTime, default=datetime.utcnow, index=True)
    xml_content = Column(Text, nullable=False)

    aggregates = relationship("AggregatedResult", back_populates="raw_source")


class AggregatedResult(Base):
    """Model pro agregované výsledky po minutách."""

    __tablename__ = "aggregated_results"

    id = Column(Integer, primary_key=True)
    raw_id = Column(Integer, ForeignKey("raw_data.id", ondelete="CASCADE"), nullable=False)
    interval_start = Column(DateTime, index=True, nullable=False)
    scope_type = Column(String, index=True, nullable=False)
    scope_code = Column(String, index=True, nullable=False)
    data = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    raw_source = relationship("RawData", back_populates="aggregates")


class Party(Base):
    """Model pro politické strany."""

    __tablename__ = "parties"

    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    color = Column(String, nullable=True)
    extra = Column(JSON, nullable=True)


class Region(Base):
    """Model pro regionální jednotky."""

    __tablename__ = "regions"

    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    level = Column(String, nullable=False)
    parent_code = Column(String, nullable=True)
    extra = Column(JSON, nullable=True)


class VoteProgress(Base):
    """Model pro vývoj sčítání v čase."""

    __tablename__ = "vote_progress"

    id = Column(Integer, primary_key=True)
    interval_start = Column(DateTime, index=True, nullable=False)
    scope_type = Column(String, index=True, nullable=False)
    scope_code = Column(String, index=True, nullable=False)
    counted_units = Column(Integer, nullable=True)
    total_units = Column(Integer, nullable=True)
    total_votes = Column(Integer, nullable=True)
    turnout = Column(Integer, nullable=True)
    speed_per_hour = Column(Integer, nullable=True)
    prediction = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db() -> None:
    """Inicializuje databázi."""

    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)


def save_json(session: Session, obj: Any) -> Dict[str, Any]:
    """Pomocná funkce pro serializaci objektu na JSON."""

    return json.loads(json.dumps(obj, default=str))
