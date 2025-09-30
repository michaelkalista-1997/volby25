"""SQLAlchemy modely pro databázi voleb 2025."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class RawData(Base):
    """Tabulka pro ukládání surových XML dat."""

    __tablename__ = "raw_data"

    id = Column(Integer, primary_key=True)
    source = Column(String(128), nullable=False)
    fetched_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    xml_content = Column(Text, nullable=False)


class AggregatedResult(Base):
    """Výsledky agregované do minutových intervalů."""

    __tablename__ = "aggregated_results"
    __table_args__ = (UniqueConstraint("minute_bucket", "scope", name="uq_minute_scope"),)

    id = Column(Integer, primary_key=True)
    minute_bucket = Column(DateTime, index=True, nullable=False)
    scope = Column(String(64), nullable=False)
    scope_code = Column(String(64), nullable=True)
    total_votes = Column(Integer, default=0)
    valid_votes = Column(Integer, default=0)
    turnout = Column(Float, default=0.0)
    data = Column(JSON, nullable=False, default=dict)


class Party(Base):
    """Seznam politických stran."""

    __tablename__ = "parties"

    id = Column(Integer, primary_key=True)
    code = Column(String(32), unique=True, nullable=False)
    name = Column(String(128), nullable=False)
    color = Column(String(16), nullable=True)

    results = relationship("VoteProgress", back_populates="party")


class Region(Base):
    """Regionální jednotky pro filtrování."""

    __tablename__ = "regions"
    __table_args__ = (UniqueConstraint("code", "level", name="uq_region_code_level"),)

    id = Column(Integer, primary_key=True)
    code = Column(String(32), nullable=False)
    name = Column(String(128), nullable=False)
    level = Column(String(32), nullable=False)  # country, region, district, municipality, abroad
    parent_code = Column(String(32), nullable=True)


class VoteProgress(Base):
    """Vývoj sčítání pro jednotlivé strany."""

    __tablename__ = "vote_progress"
    __table_args__ = (UniqueConstraint("minute_bucket", "scope", "scope_code", "party_id", name="uq_progress"),)

    id = Column(Integer, primary_key=True)
    minute_bucket = Column(DateTime, index=True, nullable=False)
    scope = Column(String(64), nullable=False)
    scope_code = Column(String(64), nullable=True)
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=False)
    votes = Column(Integer, default=0)
    vote_share = Column(Float, default=0.0)
    turnout = Column(Float, default=0.0)
    counted_precincts = Column(Integer, default=0)
    total_precincts = Column(Integer, default=0)

    party = relationship("Party", back_populates="results")


def serialize_aggregated(result: AggregatedResult) -> Dict[str, Any]:
    """Převede agregovaný záznam na slovník pro API."""

    return {
        "minute_bucket": result.minute_bucket.isoformat(),
        "scope": result.scope,
        "scope_code": result.scope_code,
        "total_votes": result.total_votes,
        "valid_votes": result.valid_votes,
        "turnout": result.turnout,
        "data": result.data or {},
    }
