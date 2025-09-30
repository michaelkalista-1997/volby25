"""Nástroje pro parsování volebních XML souborů."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

from lxml import etree

logger = logging.getLogger(__name__)


@dataclass
class PartyResult:
    """Reprezentuje výsledek jedné strany."""

    code: str
    name: str
    votes: int
    share: float

    def to_dict(self) -> dict:
        """Převede výsledek na slovník."""

        return {
            "code": self.code,
            "name": self.name,
            "votes": self.votes,
            "share": self.share,
        }


@dataclass
class ElectionSnapshot:
    """Struktura pro popis stavu sčítání."""

    scope_type: str
    scope_code: str
    total_votes: int
    counted_units: Optional[int]
    total_units: Optional[int]
    turnout: Optional[int]
    parties: List[PartyResult]


def parse_snapshot(xml_content: str) -> ElectionSnapshot:
    """Vytvoří snímek z dodaného XML."""

    root = _parse_xml(xml_content)

    scope_type = root.get("uzemi_typ", "nation") or "nation"
    scope_code = root.get("uzemi_kod", "CZ") or "CZ"
    total_votes = _safe_int(root.get("hlasy_celkem"))

    counted_units = _safe_int(root.get("okrsky_zprac"))
    total_units = _safe_int(root.get("okrsky_celkem"))
    turnout = _safe_int(root.get("ucast_procenta"))

    parties = _parse_parties(root)

    return ElectionSnapshot(
        scope_type=scope_type,
        scope_code=scope_code,
        total_votes=total_votes,
        counted_units=counted_units,
        total_units=total_units,
        turnout=turnout,
        parties=parties,
    )


def _parse_xml(xml_content: str) -> etree._Element:
    """Zvaliduje a naparsuje XML obsah."""

    try:
        parser = etree.XMLParser(recover=True)
        root = etree.fromstring(xml_content.encode("utf-8"), parser=parser)
    except etree.XMLSyntaxError as exc:  # type: ignore[assignment]
        logger.error("XML soubor nelze zpracovat: %s", exc)
        raise

    if root.tag.lower() not in {"vysledky", "results", "data"}:
        logger.debug("Neočekávaný kořen XML: %s", root.tag)

    return root


def _parse_parties(root: etree._Element) -> List[PartyResult]:
    """Vyhledá výsledky stran v XML."""

    parties: List[PartyResult] = []
    for party_node in root.findall(".//strana"):
        code = party_node.get("kod", party_node.get("kstrana", "")) or ""
        name = party_node.get("nazev", party_node.get("strana", "Unknown")) or "Unknown"
        votes = _safe_int(party_node.get("hlasy"))
        share = _safe_float(party_node.get("proc_hlasy"))
        parties.append(PartyResult(code=code, name=name, votes=votes, share=share))

    if not parties:
        for party_node in root.findall(".//party"):
            code = party_node.get("code", "")
            name = party_node.get("name", "Unknown")
            votes = _safe_int(party_node.get("votes"))
            share = _safe_float(party_node.get("share"))
            parties.append(PartyResult(code=code, name=name, votes=votes, share=share))

    parties.sort(key=lambda p: p.votes, reverse=True)
    return parties


def _safe_int(value: Optional[str]) -> int:
    """Bezpečně konvertuje text na celé číslo."""

    try:
        return int(float(value)) if value is not None else 0
    except (TypeError, ValueError):
        return 0


def _safe_float(value: Optional[str]) -> float:
    """Bezpečně konvertuje text na desetinné číslo."""

    try:
        return float(value) if value is not None else 0.0
    except (TypeError, ValueError):
        return 0.0
