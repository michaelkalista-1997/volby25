"""Pomocné funkce pro parsování volebních XML."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Tuple

from lxml import etree


class XmlParsingError(Exception):
    """Výjimka pro chyby během parsování."""


def parse_xml_content(xml_content: str) -> etree._Element:
    """Bezpečně načte XML do stromu."""

    try:
        parser = etree.XMLParser(resolve_entities=False, no_network=True, recover=True)
        return etree.fromstring(xml_content.encode("utf-8"), parser=parser)
    except etree.XMLSyntaxError as exc:
        raise XmlParsingError("Chyba při parsování XML") from exc


def extract_timestamp(root: etree._Element) -> datetime | None:
    """Najde časovou značku v XML, pokud existuje."""

    for attr in ("DATUM_UPDATE", "DATUM", "TIMESTAMP", "UPDATED"):
        value = root.get(attr)
        if value:
            try:
                return datetime.fromisoformat(value.replace(" ", "T"))
            except ValueError:
                continue
    for elem in root.xpath("//*[@DATUM_UPDATE]"):
        value = elem.get("DATUM_UPDATE")
        if value:
            try:
                return datetime.fromisoformat(value.replace(" ", "T"))
            except ValueError:
                continue
    return None


def aggregate_party_votes(root: etree._Element) -> Tuple[Dict[str, int], Dict[str, str]]:
    """Vrátí slovník hlasů pro strany a jejich názvy."""

    party_votes: Dict[str, int] = defaultdict(int)
    party_names: Dict[str, str] = {}

    for elem in root.xpath("//*[@HLASY or @HLASY_STRANA or @PL_HLASY or @PLATNE_HLASY]"):
        code = elem.get("KSTRANA") or elem.get("NUM_STRANA") or elem.get("CISLO") or elem.get("STRANA")
        if not code:
            continue
        name = elem.get("NAZ_STR") or elem.get("NAZEV_STRANY") or elem.get("NAZEV") or elem.get("JMENO")
        if name:
            party_names[code] = name
        vote_value = None
        for attr in ("HLASY", "HLASY_STRANA", "PL_HLASY", "PLATNE_HLASY", "HLASY_OBDRZENE"):
            value = elem.get(attr)
            if value and value.isdigit():
                vote_value = int(value)
                break
        if vote_value is not None:
            party_votes[code] += vote_value

    return dict(party_votes), party_names


def extract_precinct_progress(root: etree._Element) -> Tuple[int, int]:
    """Získá počet sečtených a celkových okrsků."""

    counted = 0
    total = 0
    for elem in root.xpath("//*[@OKRSKY_ZPRAC or @POC_OKRSC or @OKRSKY_CELKEM]"):
        counted_attr = elem.get("OKRSKY_ZPRAC") or elem.get("POC_OKRSC_ZPRAC")
        total_attr = elem.get("POC_OKRSC") or elem.get("OKRSKY_CELKEM") or elem.get("POCET_OKRSKU")
        if counted_attr and counted_attr.isdigit():
            counted = max(counted, int(counted_attr))
        if total_attr and total_attr.isdigit():
            total = max(total, int(total_attr))
    return counted, total


def extract_turnout(root: etree._Element) -> float:
    """Získá hodnotu volební účasti."""

    for attr in ("UCAST", "PERCENTO_UCASTI", "UCAST_PROC"):
        value = root.get(attr)
        if value:
            try:
                return float(value.replace(",", "."))
            except ValueError:
                continue
    for elem in root.xpath("//*[@UCAST or @UCAST_PROC]"):
        for attr in ("UCAST", "UCAST_PROC", "UCAST_PROCENT" ):
            value = elem.get(attr)
            if value:
                try:
                    return float(value.replace(",", "."))
                except ValueError:
                    continue
    return 0.0


def validate_xml(root: etree._Element) -> None:
    """Základní validace XML struktury."""

    if root is None or not isinstance(root.tag, str):
        raise XmlParsingError("Neočekávaná struktura XML")


def parse_vote_data(xml_content: str) -> Dict[str, object]:
    """Vrátí shrnutí volebních dat pro agregaci."""

    root = parse_xml_content(xml_content)
    validate_xml(root)
    timestamp = extract_timestamp(root)
    party_votes, party_names = aggregate_party_votes(root)
    counted, total = extract_precinct_progress(root)
    turnout = extract_turnout(root)

    return {
        "timestamp": timestamp,
        "party_votes": party_votes,
        "party_names": party_names,
        "counted_precincts": counted,
        "total_precincts": total,
        "turnout": turnout,
    }
