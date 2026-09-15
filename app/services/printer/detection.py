"""
Heurística de detección de tipo de impresora por DriverName + PaperNames.
"""

from __future__ import annotations

import re

# tipos detectados: ticket_58, ticket_80, etiqueta_60x40, a4, desconocida

_RE_ETIQUETA = re.compile(r"zebra|tsc|label|gx\d|zd\d|gk\d|argox|bixolon.*label", re.I)
_RE_TICKET_80 = re.compile(r"80\s*mm|80mm", re.I)
_RE_TICKET_58 = re.compile(r"58\s*mm|58mm", re.I)
_RE_TERMAL = re.compile(r"pos|thermal|receipt|tm-t20|tm-m30|tm-u|generic.*text|epson.*pos|bixolon.*pos|3nstar|star.*tsp", re.I)
_RE_A4 = re.compile(r"microsoft.*pdf|microsoft.*xps|a4|laserjet|deskjet", re.I)


def detectar_tipo(driver_name: str | None, paper_names: list[str] | None) -> str:
    driver = (driver_name or "").strip()
    papers = [p.lower() for p in (paper_names or [])]

    # Etiqueta tiene prioridad
    if driver and _RE_ETIQUETA.search(driver):
        return "etiqueta_60x40"

    # 80mm explícito en driver o papers
    if (driver and _RE_TICKET_80.search(driver)) or any("80" in p for p in papers):
        return "ticket_80"

    # 58mm explícito
    if (driver and _RE_TICKET_58.search(driver)) or any("58" in p for p in papers):
        return "ticket_58"

    # Genérico térmico sin tamaño -> asumir 58mm
    if driver and _RE_TERMAL.search(driver):
        # si no hay papers que indiquen 80, asumimos 58
        return "ticket_58"

    # A4 / PDF virtual
    if driver and _RE_A4.search(driver):
        return "a4"

    return "desconocida"


def paper_size_para_tipo(tipo_detectado: str) -> dict:
    """Devuelve ancho/alto en mm y pt para reportlab."""
    if tipo_detectado == "ticket_80":
        return {"ancho_mm": 80, "alto_mm": None, "ancho_pt": 80 * 2.83465, "papel": "80mm"}
    if tipo_detectado == "etiqueta_60x40":
        return {"ancho_mm": 60, "alto_mm": 40, "ancho_pt": 60 * 2.83465, "alto_pt": 40 * 2.83465, "papel": "60x40"}
    if tipo_detectado == "a4":
        return {"ancho_mm": 210, "alto_mm": 297, "ancho_pt": 595.28, "alto_pt": 841.89, "papel": "A4"}
    # ticket_58 y desconocida -> 58mm
    return {"ancho_mm": 58, "alto_mm": None, "ancho_pt": 58 * 2.83465, "papel": "58mm"}
