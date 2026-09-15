"""
Generación PDF térmico 58/80mm y etiqueta 60x40 con reportlab.
"""

from __future__ import annotations

import base64
import textwrap
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

# 58mm = 164.4pt, 80mm = 226.77pt
_ANCHO_PT = {58: 58 * mm, 80: 80 * mm, 60: 60 * mm}
_ALTO_ETIQUETA_PT = 40 * mm


def formatear_lineas_ticket(
    encabezado: str | None = None,
    lineas_items: list[dict] | None = None,
    total: str | None = None,
    pie: str | None = None,
    ancho_chars: int | None = None,
    raw_lines: list[str] | None = None,
) -> list[str]:
    """Si se pasan raw_lines, se usan tal cual. Si no, construye desde estructura."""
    if raw_lines is not None:
        return raw_lines
    out: list[str] = []
    if encabezado:
        for ln in encabezado.split("\n"):
            out.extend(textwrap.wrap(ln, width=ancho_chars or 32) or [""])
    if lineas_items:
        for it in lineas_items:
            nombre = str(it.get("nombre", ""))[:20]
            cant = str(it.get("cantidad", ""))
            precio = str(it.get("precio", ""))
            # 32 chars: "Nombre           1 x $10.00"
            filler = max(1, (ancho_chars or 32) - len(nombre) - len(cant) - len(precio) - 4)
            out.append(f"{nombre}{' ' * filler}{cant} x {precio}")
    if total:
        out.append("-" * (ancho_chars or 32))
        out.append(total.rjust(ancho_chars or 32))
    if pie:
        out.append("")
        for ln in pie.split("\n"):
            out.extend(textwrap.wrap(ln, width=ancho_chars or 32) or [""])
    return out


def generar_pdf_ticket(
    lineas: list[str],
    ancho_mm: int = 58,
    alto_mm: int | None = None,
    font_name: str = "Courier",
    font_size: float = 7.5,
    titulo: str | None = None,
) -> bytes:
    ancho_pt = _ANCHO_PT.get(ancho_mm, 58 * mm)
    # alto dinámico: 10mm por línea + márgenes
    line_h = font_size * 1.35
    alto_pt = alto_mm * mm if alto_mm else (max(40, len(lineas) * line_h + 30))
    # Para ticket sin alto fijo, usamos alto dinámico; para etiqueta 60x40, fijo
    if ancho_mm == 60 and (alto_mm == 40 or alto_mm is None):
        alto_pt = _ALTO_ETIQUETA_PT
        ancho_pt = 60 * mm

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(ancho_pt, alto_pt))
    c.setFont(font_name, font_size)

    x = 4 * mm if ancho_mm != 60 else 3 * mm
    y = alto_pt - 6 * mm
    if titulo:
        c.setFont(f"{font_name}-Bold", font_size + 1)
        c.drawCentredString(ancho_pt / 2, y, titulo[:32])
        y -= line_h + 2
        c.setFont(font_name, font_size)

    for ln in lineas:
        # truncar a ancho chars aproximado
        c.drawString(x, y, ln[:64])
        y -= line_h
        if y < 4 * mm:
            break

    c.showPage()
    c.save()
    return buf.getvalue()


def generar_pdf_base64(lineas: list[str], ancho_mm: int = 58, **kw) -> str:
    pdf = generar_pdf_ticket(lineas, ancho_mm=ancho_mm, **kw)
    return base64.b64encode(pdf).decode("ascii")
